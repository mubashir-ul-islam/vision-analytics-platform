import json
import os
import threading

STATE_FILE = 'state.json'

DEFAULTS = {
    'camera_index': 0,
    'camera_url': '',     # non-empty string = use this URL instead of camera_index
    'width': 1280,
    'height': 720,
    'model': 'yolo26n.pt',
    'conf': 0.35,
    'iou': 0.5,
    'tracker': 'bytetrack.yaml',
    'track_buffer': 60,
    'min_track_frames': 10,  # consecutive frames before counting as a visitor
    'colormap': 2,       # cv2.COLORMAP_JET
    'heatmap_alpha': 0.5,
    'vid_stride': 1,
    'device': '',
}


class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        for k, v in DEFAULTS.items():
            setattr(self, k, v)
        self._load()

    def get(self):
        with self._lock:
            return {k: getattr(self, k) for k in DEFAULTS}

    def set_camera(self, index, width, height):
        with self._lock:
            self.camera_index = index
            self.width = width
            self.height = height
            self._save()

    def set_params(self, updates):
        with self._lock:
            for k, v in updates.items():
                if k in DEFAULTS:
                    # Coerce to same type as default
                    default = DEFAULTS[k]
                    if isinstance(default, float):
                        v = float(v)
                    elif isinstance(default, int):
                        v = int(v)
                    setattr(self, k, v)
            self._save()

    def _save(self):
        data = {k: getattr(self, k) for k in DEFAULTS}
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        if not os.path.exists(STATE_FILE):
            return
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            for k, default in DEFAULTS.items():
                val = data.get(k, default)
                if isinstance(default, float):
                    val = float(val)
                elif isinstance(default, int):
                    val = int(val)
                setattr(self, k, val)
        except Exception:
            pass


app_state = AppState()
