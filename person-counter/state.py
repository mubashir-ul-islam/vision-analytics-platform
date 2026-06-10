import json
import os
import threading

STATE_FILE = 'state.json'

MODELS = ['yolo26n.pt', 'yolo26s.pt', 'yolo26m.pt', 'yolo26l.pt', 'yolo26x.pt']


class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self.camera_source = 0
        self.width = 1280
        self.height = 720
        self.model_name = 'yolo26n.pt'
        self.person_conf = 0.35
        self.flip_direction = False
        self.line = None    # [[x1,y1],[x2,y2]] normalized 0–1, or None
        self._load()

    def get(self):
        with self._lock:
            return {
                'camera_source':  self.camera_source,
                'width':          self.width,
                'height':         self.height,
                'model_name':     self.model_name,
                'person_conf':    self.person_conf,
                'flip_direction': self.flip_direction,
                'line':           self.line,
            }

    def set_source(self, source, width=1280, height=720):
        with self._lock:
            self.camera_source = source
            self.width = width
            self.height = height
            self._save()

    def set_confidence(self, person_conf):
        with self._lock:
            self.person_conf = max(0.01, min(1.0, person_conf))
            self._save()

    def set_model(self, name):
        with self._lock:
            self.model_name = name
            self._save()

    def set_line(self, line):
        with self._lock:
            self.line = line
            self._save()

    def clear_line(self):
        with self._lock:
            self.line = None
            self._save()

    def toggle_flip(self):
        with self._lock:
            self.flip_direction = not self.flip_direction
            self._save()
            return self.flip_direction

    def _save(self):
        data = {
            'camera_source':  self.camera_source,
            'width':          self.width,
            'height':         self.height,
            'model_name':     self.model_name,
            'person_conf':    self.person_conf,
            'flip_direction': self.flip_direction,
            'line':           self.line,
        }
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
            src = data.get('camera_source', 0)
            self.camera_source = int(src) if isinstance(src, (int, float)) else src
            self.width          = data.get('width', 1280)
            self.height         = data.get('height', 720)
            self.model_name     = data.get('model_name', 'yolo26n.pt')
            self.person_conf    = data.get('person_conf', 0.35)
            self.flip_direction = bool(data.get('flip_direction', False))
            self.line           = data.get('line')
        except Exception:
            pass


app_state = AppState()
