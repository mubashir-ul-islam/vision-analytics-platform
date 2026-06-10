import math
import threading
import time

import cv2
from ultralytics import YOLO

model = YOLO('yolo26n.pt')
_model_lock = threading.Lock()

# BGR colors
_LINE_CLR        = (0, 220, 220)   # cyan — counting line
_LINE_ACTIVE_CLR = (0, 80, 255)    # orange-red — flash on crossing
_PERSON_CLR      = (0, 180, 0)     # green
_IN_CLR          = (0, 255, 80)    # bright green — IN arrow
_OUT_CLR         = (0, 80, 255)    # orange — OUT arrow
_ARROW_LEN       = 40              # pixels for direction arrow


def switch_model(name: str):
    global model
    with _model_lock:
        model = YOLO(name)


def _to_px(norm_pt, w, h):
    return int(norm_pt[0] * w), int(norm_pt[1] * h)


def _side(p1, p2, pt):
    """Signed cross product. +1 = left of line, -1 = right of line, 0 = on line."""
    cross = (p2[0] - p1[0]) * (pt[1] - p1[1]) - (p2[1] - p1[1]) * (pt[0] - p1[0])
    if cross > 0:
        return 1
    if cross < 0:
        return -1
    return 0


def _match_centroids(prev, curr, threshold=80):
    """Greedy nearest-neighbour matching. Returns list of (prev_idx, curr_idx) pairs."""
    pairs = []
    used_prev = set()
    used_curr = set()
    # Build all distances, sort ascending
    distances = []
    for pi, (px, py) in enumerate(prev):
        for ci, (cx, cy) in enumerate(curr):
            d = math.hypot(cx - px, cy - py)
            if d <= threshold:
                distances.append((d, pi, ci))
    distances.sort()
    for d, pi, ci in distances:
        if pi not in used_prev and ci not in used_curr:
            pairs.append((pi, ci))
            used_prev.add(pi)
            used_curr.add(ci)
    return pairs


def _prune_cooldowns(cooldowns, now, window=1.5):
    """Remove expired cooldown entries."""
    return [(pt, t) for pt, t in cooldowns if now - t < window]


def _in_cooldown(cooldowns, pt, now, radius=40, window=1.5):
    for (cx, cy), t in cooldowns:
        if now - t < window and math.hypot(pt[0] - cx, pt[1] - cy) < radius:
            return True
    return False


def detect(frame, line, prev_centroids, flip, cooldowns, conf=0.35):
    """
    Detect persons and count line crossings.

    Args:
        frame:          BGR image
        line:           [[x1,y1],[x2,y2]] normalized 0–1, or None
        prev_centroids: list of (px, py) pixel coords from the previous frame
        flip:           bool — swap IN/OUT direction
        cooldowns:      list of ((cx,cy), timestamp) — recently counted crossings
        conf:           detection confidence threshold

    Returns:
        annotated_frame, new_centroids, in_delta, out_delta, updated_cooldowns
    """
    h, w = frame.shape[:2]
    with _model_lock:
        results = model(frame, classes=[0], conf=conf, verbose=False)[0]

    # ── Collect detections ────────────────────────────────────────────────────
    curr_centroids = []   # pixel (bottom-center x, cy)
    boxes = []
    for box in results.boxes:
        if float(box.conf[0]) < conf:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        # Use bottom-center as the crossing point (feet on ground)
        cx = (x1 + x2) // 2
        cy = y2
        curr_centroids.append((cx, cy))
        boxes.append((x1, y1, x2, y2))

    # ── Draw person boxes ─────────────────────────────────────────────────────
    for (x1, y1, x2, y2) in boxes:
        cv2.rectangle(frame, (x1, y1), (x2, y2), _PERSON_CLR, 2)

    in_delta = 0
    out_delta = 0

    if line is not None:
        p1 = _to_px(line[0], w, h)
        p2 = _to_px(line[1], w, h)

        # ── Check crossings ───────────────────────────────────────────────────
        now = time.time()
        cooldowns = _prune_cooldowns(cooldowns, now)

        pairs = _match_centroids(prev_centroids, curr_centroids)
        for pi, ci in pairs:
            prev_pt = prev_centroids[pi]
            curr_pt = curr_centroids[ci]
            s_prev = _side(p1, p2, prev_pt)
            s_curr = _side(p1, p2, curr_pt)
            if s_prev != 0 and s_curr != 0 and s_prev != s_curr:
                # Crossed the line — check cooldown at midpoint
                mid = ((prev_pt[0] + curr_pt[0]) // 2, (prev_pt[1] + curr_pt[1]) // 2)
                if not _in_cooldown(cooldowns, mid, now):
                    # s_prev=+1 → s_curr=-1 means crossed rightward
                    # Without flip: rightward = IN; leftward = OUT
                    crossed_right = (s_prev == 1 and s_curr == -1)
                    is_in = crossed_right if not flip else not crossed_right
                    if is_in:
                        in_delta += 1
                    else:
                        out_delta += 1
                    cooldowns.append((mid, now))

        # ── Draw line ─────────────────────────────────────────────────────────
        line_color = _LINE_CLR
        cv2.line(frame, p1, p2, line_color, 3)

        # Draw IN/OUT arrow perpendicular to the line at its midpoint
        mx = (p1[0] + p2[0]) // 2
        my = (p1[1] + p2[1]) // 2
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy) or 1
        # Perpendicular (rotate 90° left = IN side when flip=False)
        perp_x = -dy / length
        perp_y =  dx / length
        if flip:
            perp_x, perp_y = -perp_x, -perp_y
        ax = int(mx + perp_x * _ARROW_LEN)
        ay = int(my + perp_y * _ARROW_LEN)
        cv2.arrowedLine(frame, (mx, my), (ax, ay), _IN_CLR, 2, tipLength=0.4)
        cv2.putText(frame, 'IN', (ax + 4, ay + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, _IN_CLR, 2)

    return frame, curr_centroids, in_delta, out_delta, cooldowns
