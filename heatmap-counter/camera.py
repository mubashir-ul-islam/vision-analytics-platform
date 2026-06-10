import glob
import os
import stat
import threading
import time

import cv2


class Camera:
    def __init__(self):
        self._lock = threading.Lock()
        self._frame = None
        self._cap = None
        self._thread = None
        self._running = False

    def start(self, source, width=1280, height=720):
        """Start capturing from a local device index (int) or network URL (str)."""
        self.stop()
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            return None
        if isinstance(source, int):
            # Local USB/built-in camera: set codec and resolution
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        else:
            # Network stream (RTSP/HTTP): skip codec/resolution, minimize buffer latency
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._cap = cap
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return actual_w, actual_h

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._cap:
            self._cap.release()
            self._cap = None
        with self._lock:
            self._frame = None

    def _loop(self):
        while self._running:
            ret, frame = self._cap.read()
            if ret:
                with self._lock:
                    self._frame = frame
            else:
                time.sleep(0.01)

    def get_frame(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    @staticmethod
    def list_cameras():
        result = []
        for path in sorted(glob.glob('/dev/video*')):
            try:
                st = os.stat(path)
                if stat.S_ISCHR(st.st_mode):
                    result.append(int(path.replace('/dev/video', '')))
            except (ValueError, OSError):
                pass
        return result


camera = Camera()
