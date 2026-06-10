import math
import threading

import cv2
from ultralytics import YOLO

model = YOLO('yolo26n.pt')
_model_lock = threading.Lock()

# BGR colors
_LINE_CLR   = (0, 220, 220)   # cyan — counting line
_PERSON_CLR = (0, 180, 0)     # green
_IN_CLR     = (0, 255, 80)    # bright green — IN arrow
_ARROW_LEN  = 40              # pixels for direction arrow


def switch_model(name: str):
    global model
    with _model_lock:
        model = YOLO(name)


def _to_px(norm_pt, w, h):
    return int(norm_pt[0] * w), int(norm_pt[1] * h)


def _side(p1, p2, pt):
    """Returns +1 (left of line) or -1 (right of line) or 0 (on line)."""
    cross = (p2[0] - p1[0]) * (pt[1] - p1[1]) - (p2[1] - p1[1]) * (pt[0] - p1[0])
    if cross > 0:
        return 1
    if cross < 0:
        return -1
    return 0


def detect(frame, line, track_sides, flip, conf=0.35, tracker='bytetrack.yaml'):
    """
    Detect and track persons; count line crossings using per-ID side memory.

    Args:
        frame:       BGR image
        line:        [[x1,y1],[x2,y2]] normalized 0–1, or None
        track_sides: dict {track_id: last_side} — persisted across frames by caller
        flip:        bool — swap IN/OUT direction
        conf:        detection confidence threshold
        tracker:     tracker config name ('bytetrack.yaml' or 'botsort.yaml')

    Returns:
        annotated_frame, updated_track_sides, in_delta, out_delta
    """
    h, w = frame.shape[:2]
    with _model_lock:
        results = model.track(
            frame,
            classes=[0],
            conf=conf,
            tracker=tracker,
            persist=True,
            verbose=False,
        )[0]

    in_delta  = 0
    out_delta = 0

    # Convert line to pixel coords once
    p1 = p2 = None
    if line is not None:
        p1 = _to_px(line[0], w, h)
        p2 = _to_px(line[1], w, h)

    if results.boxes is not None and len(results.boxes):
        boxes    = results.boxes.xyxy.cpu().numpy()
        raw_ids  = results.boxes.id
        track_ids = (raw_ids.int().cpu().tolist()
                     if raw_ids is not None else [None] * len(boxes))

        for box, tid in zip(boxes, track_ids):
            x1, y1, x2, y2 = map(int, box)

            # Draw bounding box + track ID
            cv2.rectangle(frame, (x1, y1), (x2, y2), _PERSON_CLR, 2)
            if tid is not None:
                cv2.putText(frame, f'#{tid}', (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, _PERSON_CLR, 1)

            if p1 is None or tid is None:
                continue

            # Body center for side computation
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            s  = _side(p1, p2, (cx, cy))
            if s == 0:
                continue

            prev_side = track_sides.get(tid)
            if prev_side is not None and prev_side != 0 and prev_side != s:
                # This track crossed the line this frame
                crossed_right = (prev_side == 1 and s == -1)
                is_in = crossed_right if not flip else not crossed_right
                if is_in:
                    in_delta += 1
                else:
                    out_delta += 1

            track_sides[tid] = s

    # ── Draw counting line and IN arrow ───────────────────────────────────────
    if p1 is not None:
        cv2.line(frame, p1, p2, _LINE_CLR, 3)

        mx  = (p1[0] + p2[0]) // 2
        my  = (p1[1] + p2[1]) // 2
        dx  = p2[0] - p1[0]
        dy  = p2[1] - p1[1]
        length = math.hypot(dx, dy) or 1
        perp_x = -dy / length
        perp_y =  dx / length
        if flip:
            perp_x, perp_y = -perp_x, -perp_y
        ax = int(mx + perp_x * _ARROW_LEN)
        ay = int(my + perp_y * _ARROW_LEN)
        cv2.arrowedLine(frame, (mx, my), (ax, ay), _IN_CLR, 2, tipLength=0.4)
        cv2.putText(frame, 'IN', (ax + 4, ay + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, _IN_CLR, 2)

    return frame, track_sides, in_delta, out_delta
