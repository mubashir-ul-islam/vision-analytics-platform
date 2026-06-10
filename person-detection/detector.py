import threading

import cv2
from ultralytics import YOLO

model = YOLO('yolo26n.pt')
_model_lock = threading.Lock()

# BGR colors
_MAIN_CLR        = (255, 140, 0)
_ZONE_CLR        = (0, 220, 255)
_ZONE_ACTIVE_CLR = (0, 80, 255)
_PERSON_CLR      = (0, 180, 0)    # green — person detected


def switch_model(name: str):
    global model
    with _model_lock:
        model = YOLO(name)


def _to_px(rect, w, h):
    return int(rect[0] * w), int(rect[1] * h), int(rect[2] * w), int(rect[3] * h)


def _in_rect(cx, cy, px_rect):
    x1, y1, x2, y2 = px_rect
    return x1 <= cx <= x2 and y1 <= cy <= y2


def detect(frame, main_region, zones, person_conf=0.5):
    """Detect persons and record zone hits based on person center position."""
    h, w = frame.shape[:2]
    with _model_lock:
        results = model(frame, classes=[0], conf=person_conf, verbose=False)[0]

    main_px   = _to_px(main_region, w, h) if main_region else None
    zone_hits = {z['id']: False for z in zones}

    # ── Pass 1: collect all valid person detections ───────────────────────────
    person_boxes = []   # [(x1, y1, x2, y2, conf), ...]

    for box in results.boxes:
        conf = float(box.conf[0])
        if conf < person_conf:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if main_px and not _in_rect(cx, cy, main_px):
            continue

        person_boxes.append((x1, y1, x2, y2, conf))

    # ── Pass 2: zone hits — use person center ─────────────────────────────────
    for (rx1, ry1, rx2, ry2, _) in person_boxes:
        pcx, pcy = (rx1 + rx2) // 2, (ry1 + ry2) // 2
        for zone in zones:
            zpx = _to_px(zone['rect'], w, h)
            if _in_rect(pcx, pcy, zpx):
                zone_hits[zone['id']] = True

    # ── Draw persons ──────────────────────────────────────────────────────────
    for (rx1, ry1, rx2, ry2, rconf) in person_boxes:
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), _PERSON_CLR, 2)
        cv2.putText(frame, f'Person {rconf:.0%}', (rx1, ry1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, _PERSON_CLR, 2)

    # ── Draw main region and zones ────────────────────────────────────────────
    if main_px:
        cv2.rectangle(frame, main_px[:2], main_px[2:], _MAIN_CLR, 2)
        cv2.putText(frame, 'Detection Area',
                    (main_px[0] + 4, main_px[1] + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, _MAIN_CLR, 2)

    for zone in zones:
        zpx    = _to_px(zone['rect'], w, h)
        active = zone_hits[zone['id']]
        color  = _ZONE_ACTIVE_CLR if active else _ZONE_CLR
        cv2.rectangle(frame, zpx[:2], zpx[2:], color, 2)
        cv2.putText(frame, zone['name'],
                    (zpx[0] + 4, zpx[1] + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    return frame, zone_hits
