import threading
import time

import cv2
from flask import Flask, Response, jsonify, render_template, request

from camera import Camera, camera
from detector import detect, switch_model
from state import MODELS, app_state

app = Flask(__name__)

# ── Runtime state (not persisted) ────────────────────────────────────────────
_lock           = threading.Lock()
_latest_frame   = None
_fps            = 0.0
_in_count       = 0
_out_count      = 0
_prev_centroids = []    # [(px, py), ...] from the last processed frame
_cooldowns      = []    # [((cx,cy), timestamp), ...] recent crossings


def _inference_loop():
    global _latest_frame, _fps, _in_count, _out_count, _prev_centroids, _cooldowns
    prev_time = time.time()
    while True:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        with _lock:
            s            = app_state.get()
            prev_c       = list(_prev_centroids)
            cooldowns_in = list(_cooldowns)

        annotated, new_c, in_d, out_d, new_cool = detect(
            frame,
            s['line'],
            prev_c,
            s['flip_direction'],
            cooldowns_in,
            s['person_conf'],
        )

        now = time.time()
        fps = round(1.0 / max(now - prev_time, 1e-6), 1)
        prev_time = now

        with _lock:
            _latest_frame   = annotated
            _fps            = fps
            _prev_centroids = new_c
            _cooldowns      = new_cool
            _in_count       += in_d
            _out_count      += out_d


def _generate_stream():
    while True:
        with _lock:
            frame = _latest_frame
        if frame is None:
            time.sleep(0.01)
            continue
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
               + buf.tobytes() + b'\r\n')
        time.sleep(0.033)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    s = app_state.get()
    initial = {
        'camera_source':  s['camera_source'],
        'width':          s['width'],
        'height':         s['height'],
        'model_name':     s['model_name'],
        'person_conf':    s['person_conf'],
        'flip_direction': s['flip_direction'],
    }
    return render_template('index.html', initial_state=initial)


@app.route('/stream')
def stream():
    return Response(_generate_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/cameras')
def api_cameras():
    return jsonify(Camera.list_cameras())


@app.route('/api/camera', methods=['POST'])
def api_camera():
    data   = request.get_json(force=True, silent=True) or {}
    source = data.get('source', 0)
    if isinstance(source, float):
        source = int(source)
    w = int(data.get('width')  or 1280)
    h = int(data.get('height') or 720)
    app_state.set_source(source, w, h)
    result = camera.start(source, w, h)
    if result is None:
        return jsonify({'ok': False, 'error': f'Could not open source: {source}'}), 400
    actual_w, actual_h = result
    return jsonify({'ok': True, 'actual_width': actual_w, 'actual_height': actual_h})


@app.route('/api/models')
def api_models():
    return jsonify({'models': MODELS, 'active': app_state.get()['model_name']})


@app.route('/api/model', methods=['POST'])
def api_model():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get('model', '').strip()
    if name not in MODELS:
        return jsonify({'ok': False, 'error': f'Unknown model: {name}'}), 400
    switch_model(name)
    app_state.set_model(name)
    return jsonify({'ok': True, 'model': name})


@app.route('/api/line', methods=['GET'])
def api_get_line():
    s = app_state.get()
    return jsonify({'line': s['line'], 'flip_direction': s['flip_direction']})


@app.route('/api/line', methods=['POST'])
def api_set_line():
    data = request.get_json(force=True, silent=True) or {}
    line = data.get('line')
    # Validate: must be [[x1,y1],[x2,y2]] with values in [0,1]
    if (line and isinstance(line, list) and len(line) == 2
            and all(isinstance(p, list) and len(p) == 2 for p in line)):
        app_state.set_line(line)
        with _lock:
            pass  # prev_centroids will naturally reset on next frame
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Invalid line format'}), 400


@app.route('/api/line', methods=['DELETE'])
def api_clear_line():
    app_state.clear_line()
    return jsonify({'ok': True})


@app.route('/api/flip', methods=['POST'])
def api_flip():
    new_val = app_state.toggle_flip()
    return jsonify({'ok': True, 'flip_direction': new_val})


@app.route('/api/confidence', methods=['POST'])
def api_confidence():
    data = request.get_json(force=True, silent=True) or {}
    app_state.set_confidence(float(data.get('person_conf', 0.35)))
    return jsonify({'ok': True, 'person_conf': app_state.get()['person_conf']})


@app.route('/api/stats')
def api_stats():
    with _lock:
        i, o, f = _in_count, _out_count, _fps
    return jsonify({
        'in_count':  i,
        'out_count': o,
        'inside':    max(0, i - o),
        'fps':       f,
    })


@app.route('/api/stats/reset', methods=['POST'])
def api_reset_stats():
    global _in_count, _out_count, _prev_centroids, _cooldowns
    with _lock:
        _in_count       = 0
        _out_count      = 0
        _prev_centroids = []
        _cooldowns      = []
    return jsonify({'ok': True})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    s = app_state.get()
    switch_model(s['model_name'])
    camera.start(s['camera_source'], s['width'], s['height'])
    threading.Thread(target=_inference_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=8000, threaded=True)
