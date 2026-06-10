import threading
import time
import traceback

import cv2
import numpy as np

# Only model path and device require a full reinit; tracker/conf/iou are per-call kwargs
_REINIT_KEYS = {'model', 'device'}


class Processor:
    def __init__(self):
        self._lock = threading.Lock()
        self._det_frame = None
        self._heat_frame = None
        self._fps = 0.0
        self._model = None
        # heatmap accumulation lives only in the inference thread — no lock needed
        self._heatmap_acc = None
        self._reset_heatmap_flag = False
        self._running = False
        self._thread = None
        self._occupancy = 0
        self._total_visitors = 0
        self._all_seen_ids = set()
        self._candidate_frames = {}   # tid -> consecutive frame count
        self._session_start = time.time()
        self._needs_reinit = True
        self._params = {}
        self._camera = None

    def set_camera(self, cam):
        self._camera = cam

    def start(self, initial_params):
        with self._lock:
            self._params = dict(initial_params)
            self._session_start = time.time()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def update_params(self, new_params):
        with self._lock:
            needs_reinit = any(
                k in _REINIT_KEYS and new_params.get(k) != self._params.get(k)
                for k in new_params
            )
            self._params.update(new_params)
            if needs_reinit:
                self._needs_reinit = True
                self._reset_heatmap_flag = True

    def reset_heatmap(self):
        with self._lock:
            self._reset_heatmap_flag = True

    def reset_counts(self):
        with self._lock:
            self._occupancy = 0
            self._total_visitors = 0
            self._all_seen_ids = set()
            self._candidate_frames = {}
            self._session_start = time.time()

    def get_frames(self):
        with self._lock:
            return self._det_frame, self._heat_frame

    def get_stats(self):
        with self._lock:
            return {
                'occupancy': self._occupancy,
                'total_visitors': self._total_visitors,
                'fps': round(self._fps, 1),
                'session_seconds': int(time.time() - self._session_start),
            }

    def get_params(self):
        with self._lock:
            return dict(self._params)

    # ── Private — all called only from inference thread ───────────────────────

    def _build_model(self, params):
        from ultralytics import YOLO
        model = YOLO(params['model'])
        if params.get('device'):
            model.to(params['device'])
        return model

    def _accumulate_heatmap(self, frame_shape, boxes):
        h, w = frame_shape[:2]
        if self._heatmap_acc is None or self._heatmap_acc.shape != (h, w):
            self._heatmap_acc = np.zeros((h, w), dtype=np.float32)
        for box in boxes:
            x1, y1, x2, y2 = (max(0, int(box[0])), max(0, int(box[1])),
                               min(w, int(box[2])), min(h, int(box[3])))
            if x2 > x1 and y2 > y1:
                self._heatmap_acc[y1:y2, x1:x2] += 1.0

    def _render_heatmap(self, frame, colormap, alpha):
        if self._heatmap_acc is None:
            return frame.copy()
        h, w = frame.shape[:2]
        acc = self._heatmap_acc
        if acc.shape != (h, w):
            acc = cv2.resize(acc, (w, h))
        acc_max = acc.max()
        if acc_max > 0:
            norm = (acc / acc_max * 255).astype(np.uint8)
        else:
            norm = acc.astype(np.uint8)
        colored = cv2.applyColorMap(norm, int(colormap))
        return cv2.addWeighted(frame, 1.0 - float(alpha), colored, float(alpha), 0)

    def _draw_boxes(self, frame, boxes, track_ids):
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box)
            tid = track_ids[i] if (track_ids and i < len(track_ids)) else '?'
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 210, 80), 2)
            label = f'Person #{tid}'
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            top = max(y1 - th - 4, 0)
            cv2.rectangle(frame, (x1, top), (x1 + tw + 4, top + th + 6), (0, 210, 80), -1)
            cv2.putText(frame, label, (x1 + 2, top + th + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        return frame

    def _loop(self):
        prev_time = time.time()
        frame_counter = 0
        model = None

        while self._running:
            # Read shared state atomically
            with self._lock:
                needs_reinit = self._needs_reinit
                reset_heatmap = self._reset_heatmap_flag
                params = dict(self._params)
                if reset_heatmap:
                    self._reset_heatmap_flag = False

            if reset_heatmap:
                self._heatmap_acc = None

            if needs_reinit or model is None:
                try:
                    model = self._build_model(params)
                    with self._lock:
                        self._model = model
                        self._needs_reinit = False
                    print(f'[processor] ready: model={params["model"]} '
                          f'tracker={params["tracker"]} device={params["device"] or "auto"}')
                except Exception:
                    traceback.print_exc()
                    time.sleep(2)
                    continue

            if self._camera is None:
                time.sleep(0.05)
                continue

            frame = self._camera.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            frame_counter += 1
            if frame_counter % max(1, int(params.get('vid_stride', 1))) != 0:
                time.sleep(0.005)
                continue

            try:
                results = model.track(
                    frame,
                    classes=[0],
                    conf=float(params['conf']),
                    iou=float(params['iou']),
                    tracker=params['tracker'],
                    persist=True,
                    verbose=False,
                )[0]

                # Extract boxes and IDs (safe numpy conversion)
                if results.boxes is not None and len(results.boxes):
                    boxes = results.boxes.xyxy.cpu().numpy()
                    raw_ids = results.boxes.id
                    track_ids = (raw_ids.int().cpu().tolist()
                                 if raw_ids is not None else [None] * len(boxes))
                else:
                    boxes = []
                    track_ids = []

                det_frame = self._draw_boxes(frame.copy(), boxes, track_ids)
                self._accumulate_heatmap(frame.shape, boxes)
                heat_frame = self._render_heatmap(
                    frame.copy(),
                    params.get('colormap', 2),
                    params.get('heatmap_alpha', 0.5),
                )

                current_ids = {int(t) for t in track_ids if t is not None}
                min_frames = max(1, int(params.get('min_track_frames', 10)))
                now = time.time()
                fps = 1.0 / max(now - prev_time, 1e-6)
                prev_time = now

                with self._lock:
                    # Drop counters for IDs no longer visible this frame
                    for tid in list(self._candidate_frames):
                        if tid not in current_ids:
                            del self._candidate_frames[tid]
                    # Increment consecutive-frame counter for each visible ID
                    for tid in current_ids:
                        self._candidate_frames[tid] = self._candidate_frames.get(tid, 0) + 1
                    # Only promote IDs that have been seen for >= min_frames in a row
                    confirmed = {tid for tid, n in self._candidate_frames.items()
                                 if n >= min_frames}
                    new_visitors = confirmed - self._all_seen_ids
                    self._all_seen_ids |= new_visitors
                    self._occupancy = len(current_ids)
                    self._total_visitors = len(self._all_seen_ids)
                    self._fps = fps
                    self._det_frame = det_frame
                    self._heat_frame = heat_frame

            except Exception:
                traceback.print_exc()
                time.sleep(0.1)


processor = Processor()
