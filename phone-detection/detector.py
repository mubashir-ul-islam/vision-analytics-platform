import threading

import cv2
from ultralytics import YOLO

model = YOLO('yolo26n.pt')
_model_lock = threading.Lock()

# BGR colors
_MAIN_CLR         = (255, 140, 0)
_ZONE_CLR         = (0, 220, 255)
_ZONE_ACTIVE_CLR  = (0, 80, 255)
_PHONE_ACTIVE_CLR = (0, 0, 220)    # red   — phone being held/used by a person
_PHONE_IDLE_CLR   = (0, 165, 255)  # orange — phone detected but no person nearby
_PERSON_CLR       = (0, 180, 0)    # green — person, no phone
_PERSON_PHONE_CLR = (0, 255, 140)  # bright green — person actively using a phone


def switch_model(name: str):
    global model
    with _model_lock:
        model = YOLO(name)


def _to_px(rect, w, h):
    return int(rect[0] * w), int(rect[1] * h), int(rect[2] * w), int(rect[3] * h)


def _in_rect(cx, cy, px_rect):
    x1, y1, x2, y2 = px_rect
    return x1 <= cx <= x2 and y1 <= cy <= y2


def _phone_person_overlap(phone_box, person_box):
    """Returns intersection area / phone area (0.0–1.0).

    Measures how much of the phone bounding box is inside the person bounding
    box. Standard IoU is not used because phones are much smaller than people —
    a phone fully inside someone's torso would score ~0.05 IoU but 1.0 here.
    """
    px1, py1, px2, py2 = phone_box
    rx1, ry1, rx2, ry2 = person_box
    ix1, iy1 = max(px1, rx1), max(py1, ry1)
    ix2, iy2 = min(px2, rx2), min(py2, ry2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    intersection = (ix2 - ix1) * (iy2 - iy1)
    phone_area = (px2 - px1) * (py2 - py1)
    return intersection / phone_area if phone_area > 0 else 0.0


def detect(frame, main_region, zones, phone_conf=0.5, person_conf=0.5,
           person_phone_overlap=0.3):
    """Detect phones and persons; return separate zone hits for person presence
    and phone-in-use so both can be tracked independently."""
    h, w = frame.shape[:2]
    with _model_lock:
        results = model(frame, classes=[0, 67],
                        conf=min(phone_conf, person_conf), verbose=False)[0]

    main_px          = _to_px(main_region, w, h) if main_region else None
    person_zone_hits = {z['id']: False for z in zones}
    phone_zone_hits  = {z['id']: False for z in zones}

    # ── Pass 1: collect all valid detections ─────────────────────────────────
    person_boxes = []   # [(x1, y1, x2, y2, conf), ...]
    phone_boxes  = []   # [(x1, y1, x2, y2, conf), ...]

    for box in results.boxes:
        cls  = int(box.cls[0])
        conf = float(box.conf[0])
        if cls == 67 and conf < phone_conf:
            continue
        if cls == 0 and conf < person_conf:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if main_px and not _in_rect(cx, cy, main_px):
            continue

        if cls == 0:
            person_boxes.append((x1, y1, x2, y2, conf))
        else:
            phone_boxes.append((x1, y1, x2, y2, conf))

    # ── Pass 2: pair each phone with the best overlapping person ─────────────
    active_phones  = []   # [(phone_tuple, person_tuple)] — phone overlaps a person
    idle_phones    = []   # [phone_tuple]                 — no person overlap
    active_persons = set()  # indices into person_boxes with at least one phone

    for phone in phone_boxes:
        px1, py1, px2, py2, _ = phone
        best_overlap = 0.0
        best_idx     = -1
        for i, person in enumerate(person_boxes):
            overlap = _phone_person_overlap((px1, py1, px2, py2), person[:4])
            if overlap > best_overlap:
                best_overlap = overlap
                best_idx     = i

        if best_overlap >= person_phone_overlap and best_idx >= 0:
            active_phones.append((phone, person_boxes[best_idx]))
            active_persons.add(best_idx)
        else:
            idle_phones.append(phone)

    # ── Pass 3: zone hits ─────────────────────────────────────────────────────
    # Person zone hits: any person (regardless of phone use) in a zone
    for (rx1, ry1, rx2, ry2, _) in person_boxes:
        pcx, pcy = (rx1 + rx2) // 2, (ry1 + ry2) // 2
        for zone in zones:
            zpx = _to_px(zone['rect'], w, h)
            if _in_rect(pcx, pcy, zpx):
                person_zone_hits[zone['id']] = True

    # Phone zone hits: only persons actively using a phone in a zone
    for _, person in active_phones:
        rx1, ry1, rx2, ry2 = person[:4]
        pcx, pcy = (rx1 + rx2) // 2, (ry1 + ry2) // 2
        for zone in zones:
            zpx = _to_px(zone['rect'], w, h)
            if _in_rect(pcx, pcy, zpx):
                phone_zone_hits[zone['id']] = True

    # ── Draw persons ──────────────────────────────────────────────────────────
    for i, (rx1, ry1, rx2, ry2, rconf) in enumerate(person_boxes):
        using_phone = i in active_persons
        color = _PERSON_PHONE_CLR if using_phone else _PERSON_CLR
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), color, 2)
        label = f'Person {rconf:.0%}' + (' [using phone]' if using_phone else '')
        cv2.putText(frame, label, (rx1, ry1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    # ── Draw phones ───────────────────────────────────────────────────────────
    for (px1, py1, px2, py2, pconf), _ in active_phones:
        cv2.rectangle(frame, (px1, py1), (px2, py2), _PHONE_ACTIVE_CLR, 2)
        cv2.putText(frame, f'Phone {pconf:.0%} (in use)',
                    (px1, py1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, _PHONE_ACTIVE_CLR, 2)

    for (px1, py1, px2, py2, pconf) in idle_phones:
        cv2.rectangle(frame, (px1, py1), (px2, py2), _PHONE_IDLE_CLR, 2)
        cv2.putText(frame, f'Phone {pconf:.0%} (unattended)',
                    (px1, py1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, _PHONE_IDLE_CLR, 2)

    # ── Draw main region and zones ────────────────────────────────────────────
    if main_px:
        cv2.rectangle(frame, main_px[:2], main_px[2:], _MAIN_CLR, 2)
        cv2.putText(frame, 'Detection Area',
                    (main_px[0] + 4, main_px[1] + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, _MAIN_CLR, 2)

    for zone in zones:
        zpx    = _to_px(zone['rect'], w, h)
        active = person_zone_hits[zone['id']]
        color  = _ZONE_ACTIVE_CLR if active else _ZONE_CLR
        cv2.rectangle(frame, zpx[:2], zpx[2:], color, 2)
        cv2.putText(frame, zone['name'],
                    (zpx[0] + 4, zpx[1] + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    return frame, person_zone_hits, phone_zone_hits
