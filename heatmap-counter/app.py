import logging
import threading
import time

import cv2
from flask import Flask, Response, jsonify, render_template, request

# Suppress Ultralytics "No tracks found" and other verbose tracker messages
logging.getLogger('ultralytics').setLevel(logging.ERROR)

from camera import Camera, camera
from processor import processor
from state import app_state

app = Flask(__name__)


# ── MJPEG stream helpers ──────────────────────────────────────────────────────

def _encode_frame(frame):
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
            + buf.tobytes() + b'\r\n')


def _placeholder_frame(text='Waiting for camera…'):
    import numpy as np
    img = np.zeros((480, 640, 3), dtype='uint8')
    cv2.putText(img, text, (80, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 2, cv2.LINE_AA)
    return img


def _generate_detection_stream():
    while True:
        det_frame, _ = processor.get_frames()
        frame = det_frame if det_frame is not None else _placeholder_frame()
        yield _encode_frame(frame)
        time.sleep(0.033)


def _generate_heatmap_stream():
    while True:
        _, heat_frame = processor.get_frames()
        frame = heat_frame if heat_frame is not None else _placeholder_frame('Heatmap building…')
        yield _encode_frame(frame)
        time.sleep(0.033)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    s = app_state.get()
    return render_template('index.html', initial_state=s)


@app.route('/stream/detection')
def stream_detection():
    return Response(_generate_detection_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/stream/heatmap')
def stream_heatmap():
    return Response(_generate_heatmap_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/cameras')
def api_cameras():
    return jsonify(Camera.list_cameras())


@app.route('/api/camera', methods=['POST'])
def api_camera():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get('url') or '').strip()

    if url:
        # Network / RTSP / HTTP camera
        result = camera.start(url)
        if result is None:
            return jsonify({'ok': False, 'error': f'Could not connect to {url}'}), 400
        actual_w, actual_h = result
        app_state.set_params({'camera_url': url})
        return jsonify({'ok': True, 'source': 'url', 'actual_width': actual_w, 'actual_height': actual_h})
    else:
        # Local device index
        idx = int(data.get('index', 0))
        w   = int(data.get('width', 1280))
        h   = int(data.get('height', 720))
        result = camera.start(idx, w, h)
        if result is None:
            return jsonify({'ok': False, 'error': f'Camera {idx} could not be opened'}), 400
        actual_w, actual_h = result
        app_state.set_camera(idx, actual_w, actual_h)
        app_state.set_params({'camera_url': ''})   # clear any saved URL
        return jsonify({'ok': True, 'source': 'local', 'actual_width': actual_w, 'actual_height': actual_h})


@app.route('/api/params', methods=['GET'])
def api_get_params():
    return jsonify(processor.get_params())


@app.route('/api/params', methods=['POST'])
def api_set_params():
    data = request.get_json(force=True, silent=True) or {}
    app_state.set_params(data)
    processor.update_params(data)
    return jsonify({'ok': True})


@app.route('/api/stats')
def api_stats():
    return jsonify(processor.get_stats())


@app.route('/api/heatmap/reset', methods=['POST'])
def api_reset_heatmap():
    processor.reset_heatmap()
    return jsonify({'ok': True})


@app.route('/api/stats/reset', methods=['POST'])
def api_reset_stats():
    processor.reset_counts()
    return jsonify({'ok': True})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    s = app_state.get()
    processor.set_camera(camera)
    if s.get('camera_url'):
        camera.start(s['camera_url'])
    else:
        camera.start(s['camera_index'], s['width'], s['height'])
    processor.start(s)
    app.run(host='0.0.0.0', port=8000, threaded=True)
