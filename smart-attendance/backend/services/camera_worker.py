import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import cv2

from config import settings, _parse_source
from database import SessionLocal
from models import Employee
from services import attendance_service, compreface

logger = logging.getLogger(__name__)

RECONNECT_AFTER = 30  # consecutive failed reads before reconnecting (~3 s)


@dataclass
class CameraState:
    camera_source: str
    camera_type: str  # "entrance" or "exit"
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _latest_frame: Optional[bytes] = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _cooldown: dict = field(default_factory=dict, repr=False)
    _camera_ok: bool = field(default=False, repr=False)

    @property
    def latest_frame(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_frame

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def camera_ok(self) -> bool:
        return self._camera_ok


_entrance_state = CameraState(camera_source=settings.entrance_camera_source, camera_type="entrance")
_exit_state = CameraState(camera_source=settings.exit_camera_source, camera_type="exit")

_event_queue: Optional[asyncio.Queue] = None
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def get_camera_state(camera_type: str) -> CameraState:
    if camera_type == "entrance":
        return _entrance_state
    elif camera_type == "exit":
        return _exit_state
    raise ValueError(f"Unknown camera type: {camera_type}")


def _push_event(payload: dict):
    if _event_queue is not None and _event_loop is not None:
        asyncio.run_coroutine_threadsafe(_event_queue.put(payload), _event_loop)


def _run_recognition(frame, state: CameraState):
    if not settings.compreface_ready:
        return

    if frame is None or frame.size == 0:
        return
    if cv2.mean(frame)[0] < 1.0:
        logger.debug("Skipping blank frame from %s camera", state.camera_type)
        return

    h, w = frame.shape[:2]
    if w > 640:
        frame = cv2.resize(frame, (640, int(h * 640 / w)))

    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    image_bytes = jpeg.tobytes()

    try:
        results = compreface.recognize_sync(image_bytes)
    except Exception as exc:
        logger.warning("Recognition error on %s camera: %s", state.camera_type, exc)
        return

    now_mono = time.monotonic()
    cooldown_threshold = settings.cooldown_minutes * 60

    state._cooldown = {
        k: v for k, v in state._cooldown.items()
        if now_mono - v < cooldown_threshold * 2
    }

    for face in results:
        subjects = face.get("subjects", [])
        if not subjects:
            continue
        best = max(subjects, key=lambda s: s["similarity"])
        if best["similarity"] < settings.recognition_threshold:
            continue

        subject_uuid = best["subject"]

        if now_mono - state._cooldown.get(subject_uuid, 0) < cooldown_threshold:
            continue
        state._cooldown[subject_uuid] = now_mono

        _handle_recognition(subject_uuid, state.camera_type)


def _handle_recognition(subject_uuid: str, camera_type: str):
    db = SessionLocal()
    try:
        employee = db.query(Employee).filter(Employee.compreface_subject == subject_uuid).first()
        if not employee:
            logger.debug("Recognized unknown subject %s — not in DB", subject_uuid)
            return

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if camera_type == "entrance":
            record = attendance_service.record_entry(db, employee)
            status = "entered"
        else:
            record = attendance_service.record_exit(db, employee)
            status = "completed"
            _entrance_state._cooldown.pop(subject_uuid, None)

        _push_event({
            "type": "attendance",
            "camera": camera_type,
            "employee_id": employee.id,
            "employee_name": employee.name,
            "employee_code": employee.employee_id,
            "timestamp": now.isoformat(),
            "status": status,
            "total_minutes": record.total_minutes,
        })
        logger.info("Attendance: %s %s via %s camera", employee.name, status, camera_type)
    except Exception as exc:
        logger.exception("Error handling recognition for subject %s: %s", subject_uuid, exc)
    finally:
        db.close()


def _worker_thread(state: CameraState):
    source = _parse_source(state.camera_source)
    is_url = isinstance(source, str)
    logger.info("Camera worker starting: %s (source: %s)", state.camera_type, state.camera_source)

    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        logger.error("Cannot open camera %s (%s)", state.camera_source, state.camera_type)
        state._camera_ok = False
        return

    if not is_url:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    state._camera_ok = True
    logger.info("Camera %s opened successfully (source: %s)", state.camera_type, state.camera_source)

    last_recognition_at = 0.0
    consecutive_failures = 0

    try:
        while state._running:
            ret, frame = cap.read()
            if not ret:
                consecutive_failures += 1
                if consecutive_failures >= RECONNECT_AFTER:
                    logger.warning("Camera %s lost signal — reconnecting...", state.camera_type)
                    cap.release()
                    cap = cv2.VideoCapture(source)
                    state._camera_ok = cap.isOpened()
                    consecutive_failures = 0
                time.sleep(0.1)
                continue

            consecutive_failures = 0
            _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            with state._lock:
                state._latest_frame = jpeg.tobytes()

            now = time.monotonic()
            if now - last_recognition_at >= settings.recognition_interval_seconds:
                last_recognition_at = now
                _run_recognition(frame, state)
    finally:
        cap.release()
        logger.info("Camera worker stopped: %s", state.camera_type)


def start_workers(event_queue: asyncio.Queue, event_loop: asyncio.AbstractEventLoop):
    global _event_queue, _event_loop
    _event_queue = event_queue
    _event_loop = event_loop

    for state in (_entrance_state, _exit_state):
        state._running = True
        t = threading.Thread(target=_worker_thread, args=(state,), daemon=True, name=f"cam-{state.camera_type}")
        state._thread = t
        t.start()


def stop_workers():
    for state in (_entrance_state, _exit_state):
        state._running = False


def list_available_cameras(max_index: int = 10) -> list[dict]:
    """Return video devices that exist on the filesystem (avoids opening busy cameras)."""
    available = []
    for idx in range(max_index):
        if os.path.exists(f"/dev/video{idx}"):
            available.append({"index": idx, "label": f"Camera {idx}  (/dev/video{idx})"})
    return available


def restart_workers(entrance_source: str, exit_source: str):
    """Stop current camera threads, swap sources, start fresh threads."""
    global _entrance_state, _exit_state

    for state in (_entrance_state, _exit_state):
        state._running = False
    for state in (_entrance_state, _exit_state):
        if state._thread and state._thread.is_alive():
            state._thread.join(timeout=5.0)

    _entrance_state = CameraState(camera_source=entrance_source, camera_type="entrance")
    _exit_state = CameraState(camera_source=exit_source, camera_type="exit")

    settings.entrance_camera_source = entrance_source
    settings.exit_camera_source = exit_source

    start_workers(_event_queue, _event_loop)
