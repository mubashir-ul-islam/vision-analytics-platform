'use strict';

// ── State ────────────────────────────────────────────────────────────────────
let drawMode   = false;    // true when user is in line-draw mode
let lineStart  = null;     // {x, y} normalized
let lineEnd    = null;     // {x, y} normalized
let flipDir    = INITIAL_STATE.flip_direction;
let drawing    = false;
let drawStartPx = null;
let drawEndPx   = null;

// ── Elements ──────────────────────────────────────────────────────────────────
const streamImg      = document.getElementById('stream-img');
const videoContainer = document.getElementById('video-container');
const canvas         = document.getElementById('draw-canvas');
const ctx            = canvas.getContext('2d');
const modeHint       = document.getElementById('mode-hint');
const fpsBadge       = document.getElementById('fps-badge');
const inCount        = document.getElementById('in-count');
const outCount       = document.getElementById('out-count');
const insideCount    = document.getElementById('inside-count');

// ── Canvas sync ───────────────────────────────────────────────────────────────
function syncCanvas() {
  const w = videoContainer.offsetWidth;
  const h = videoContainer.offsetHeight;
  if (w === 0 || h === 0) return;
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width  = w;
    canvas.height = h;
    redrawCanvas();
  }
}

streamImg.addEventListener('load', syncCanvas);
window.addEventListener('resize', syncCanvas);
if (window.ResizeObserver) new ResizeObserver(syncCanvas).observe(videoContainer);

// ── Canvas drawing ────────────────────────────────────────────────────────────
function getPos(e) {
  const r = canvas.getBoundingClientRect();
  return {
    x: (e.clientX - r.left) * (canvas.width  / r.width),
    y: (e.clientY - r.top)  * (canvas.height / r.height),
  };
}

function normPt(px) {
  return { x: px.x / canvas.width, y: px.y / canvas.height };
}

canvas.addEventListener('mousedown', e => {
  if (!drawMode) return;
  drawing     = true;
  drawStartPx = getPos(e);
  drawEndPx   = { ...drawStartPx };
});

canvas.addEventListener('mousemove', e => {
  if (!drawing) return;
  drawEndPx = getPos(e);
  redrawCanvas();
});

canvas.addEventListener('mouseup', e => {
  if (!drawing) return;
  drawing   = false;
  drawEndPx = getPos(e);
  const dx  = drawEndPx.x - drawStartPx.x;
  const dy  = drawEndPx.y - drawStartPx.y;
  if (Math.hypot(dx, dy) > 10) {
    lineStart = normPt(drawStartPx);
    lineEnd   = normPt(drawEndPx);
    setDrawMode(false);
  }
  redrawCanvas();
});

document.addEventListener('mouseup', () => {
  if (drawing) { drawing = false; redrawCanvas(); }
});

// ── Canvas render ─────────────────────────────────────────────────────────────
function redrawCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Draw committed line
  if (lineStart && lineEnd) {
    const x1 = lineStart.x * canvas.width,  y1 = lineStart.y * canvas.height;
    const x2 = lineEnd.x   * canvas.width,  y2 = lineEnd.y   * canvas.height;
    drawLine(x1, y1, x2, y2, '#00dddd', false);
  }

  // Draw in-progress line
  if (drawing && drawStartPx && drawEndPx) {
    drawLine(drawStartPx.x, drawStartPx.y, drawEndPx.x, drawEndPx.y, '#00dddd', true);
  }
}

function drawLine(x1, y1, x2, y2, color, dashed) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth   = 3;
  ctx.setLineDash(dashed ? [8, 5] : []);
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();

  if (!dashed) {
    // Perpendicular arrow at midpoint (IN direction)
    const mx  = (x1 + x2) / 2;
    const my  = (y1 + y2) / 2;
    const dx  = x2 - x1;
    const dy  = y2 - y1;
    const len = Math.hypot(dx, dy) || 1;
    let px = -dy / len;
    let py =  dx / len;
    if (flipDir) { px = -px; py = -py; }
    const ax = mx + px * 40;
    const ay = my + py * 40;

    // Arrow shaft
    ctx.beginPath();
    ctx.moveTo(mx, my);
    ctx.lineTo(ax, ay);
    ctx.strokeStyle = '#00ff55';
    ctx.lineWidth   = 2;
    ctx.setLineDash([]);
    ctx.stroke();

    // Arrowhead
    const angle = Math.atan2(ay - my, ax - mx);
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(ax - 12 * Math.cos(angle - 0.4), ay - 12 * Math.sin(angle - 0.4));
    ctx.lineTo(ax - 12 * Math.cos(angle + 0.4), ay - 12 * Math.sin(angle + 0.4));
    ctx.closePath();
    ctx.fillStyle = '#00ff55';
    ctx.fill();

    // "IN" label
    ctx.font      = 'bold 13px sans-serif';
    ctx.fillStyle = '#00ff55';
    ctx.fillText('IN', ax + 5, ay + 5);

    // Endpoint dots
    ctx.fillStyle = color;
    [[x1, y1], [x2, y2]].forEach(([ex, ey]) => {
      ctx.beginPath();
      ctx.arc(ex, ey, 5, 0, Math.PI * 2);
      ctx.fill();
    });
  }
  ctx.restore();
}

// ── Mode controls ─────────────────────────────────────────────────────────────
const drawLineBtn  = document.getElementById('draw-line-btn');
const flipBtn      = document.getElementById('flip-btn');
const clearLineBtn = document.getElementById('clear-line-btn');
const applyLineBtn = document.getElementById('apply-line-btn');

function setDrawMode(on) {
  drawMode = on;
  drawLineBtn.classList.toggle('active', on);
  if (on) {
    modeHint.textContent = 'Click and drag to draw the counting line across the doorway';
    modeHint.classList.add('visible');
    canvas.style.cursor = 'crosshair';
  } else {
    modeHint.classList.remove('visible');
    canvas.style.cursor = 'default';
  }
}

drawLineBtn.addEventListener('click', () => setDrawMode(!drawMode));

flipBtn.addEventListener('click', async () => {
  const resp = await fetch('/api/flip', { method: 'POST' });
  const data = await resp.json();
  if (data.ok) {
    flipDir = data.flip_direction;
    redrawCanvas();
    showToast(flipDir ? 'Direction flipped' : 'Direction restored');
  }
});

clearLineBtn.addEventListener('click', async () => {
  if (!confirm('Clear the counting line?')) return;
  lineStart = null;
  lineEnd   = null;
  setDrawMode(false);
  redrawCanvas();
  await fetch('/api/line', { method: 'DELETE' });
  showToast('Line cleared');
});

applyLineBtn.addEventListener('click', async () => {
  if (!lineStart || !lineEnd) {
    showToast('Draw a line first');
    return;
  }
  const payload = {
    line: [
      [lineStart.x, lineStart.y],
      [lineEnd.x,   lineEnd.y],
    ],
  };
  const resp = await fetch('/api/line', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  });
  const data = await resp.json();
  showToast(data.ok ? 'Line applied' : `Error: ${data.error}`);
});

// ── Camera ────────────────────────────────────────────────────────────────────
const cameraSelect     = document.getElementById('camera-select');
const resolutionSelect = document.getElementById('resolution-select');
const applyCameraBtn   = document.getElementById('apply-camera-btn');
const modeWebcamBtn    = document.getElementById('mode-webcam-btn');
const modeUrlBtn       = document.getElementById('mode-url-btn');
const webcamControls   = document.getElementById('webcam-controls');
const urlControls      = document.getElementById('url-controls');
const cameraUrlInput   = document.getElementById('camera-url');
let cameraMode = 'webcam';

function setCameraMode(mode) {
  cameraMode = mode;
  modeWebcamBtn.classList.toggle('active', mode === 'webcam');
  modeUrlBtn.classList.toggle('active',    mode === 'url');
  webcamControls.style.display = mode === 'webcam' ? '' : 'none';
  urlControls.style.display    = mode === 'url'    ? '' : 'none';
}

modeWebcamBtn.addEventListener('click', () => setCameraMode('webcam'));
modeUrlBtn.addEventListener('click',    () => setCameraMode('url'));

(function initCameraUI() {
  const src = INITIAL_STATE.camera_source;
  if (typeof src === 'string' && src !== '') {
    setCameraMode('url');
    cameraUrlInput.value = src;
  } else {
    setCameraMode('webcam');
    const savedOpt = resolutionSelect.querySelector(
      `option[value="${INITIAL_STATE.width}x${INITIAL_STATE.height}"]`);
    if (savedOpt) savedOpt.selected = true;
  }
})();

async function loadCameras() {
  const resp    = await fetch('/api/cameras');
  const cameras = await resp.json();
  cameraSelect.innerHTML = '';
  if (!cameras.length) {
    cameraSelect.innerHTML = '<option value="">No cameras found</option>';
    return;
  }
  cameras.forEach(i => {
    const opt = document.createElement('option');
    opt.value = i; opt.textContent = `Camera ${i}`;
    if (i === INITIAL_STATE.camera_source) opt.selected = true;
    cameraSelect.appendChild(opt);
  });
}

applyCameraBtn.addEventListener('click', async () => {
  let body;
  if (cameraMode === 'url') {
    const url = cameraUrlInput.value.trim();
    if (!url) { showToast('Please enter a stream URL'); return; }
    body = { source: url };
  } else {
    const [w, h] = resolutionSelect.value.split('x').map(Number);
    body = { source: parseInt(cameraSelect.value, 10), width: w, height: h };
  }
  const resp = await fetch('/api/camera', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (data.ok) {
    showToast(cameraMode === 'url'
      ? `IP camera connected — ${data.actual_width}×${data.actual_height}`
      : `Resolution set to ${data.actual_width}×${data.actual_height}`);
  } else {
    showToast(`Error: ${data.error}`);
  }
});

// ── Confidence slider ─────────────────────────────────────────────────────────
const personSlider = document.getElementById('person-conf');
const personVal    = document.getElementById('person-conf-val');
let _confTimer = null;

personSlider.value    = Math.round(INITIAL_STATE.person_conf * 100);
personVal.textContent = `${personSlider.value}%`;

personSlider.addEventListener('input', () => {
  personVal.textContent = `${personSlider.value}%`;
  clearTimeout(_confTimer);
  _confTimer = setTimeout(() => fetch('/api/confidence', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ person_conf: parseFloat(personSlider.value) / 100 }),
  }), 300);
});

// ── Model ─────────────────────────────────────────────────────────────────────
const modelSelect   = document.getElementById('model-select');
const applyModelBtn = document.getElementById('apply-model-btn');

(function initModelUI() {
  const opt = modelSelect.querySelector(`option[value="${INITIAL_STATE.model_name}"]`);
  if (opt) opt.selected = true;
})();

applyModelBtn.addEventListener('click', async () => {
  applyModelBtn.disabled = true; applyModelBtn.textContent = 'Loading…';
  const resp = await fetch('/api/model', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: modelSelect.value }),
  });
  applyModelBtn.disabled = false; applyModelBtn.textContent = 'Apply Model';
  const data = await resp.json();
  showToast(data.ok ? `Model switched to ${data.model}` : `Error: ${data.error}`);
});

// ── Stats ─────────────────────────────────────────────────────────────────────
document.getElementById('reset-stats-btn').addEventListener('click', async () => {
  await fetch('/api/stats/reset', { method: 'POST' });
  showToast('Counters reset');
});

setInterval(async () => {
  try {
    const resp = await fetch('/api/stats');
    const data = await resp.json();
    fpsBadge.textContent   = `${data.fps ?? '--'} fps`;
    inCount.textContent    = data.in_count  ?? 0;
    outCount.textContent   = data.out_count ?? 0;
    insideCount.textContent = data.inside   ?? 0;
  } catch (_) {}
}, 1000);

// ── Load saved line on startup ────────────────────────────────────────────────
async function loadLine() {
  const resp = await fetch('/api/line');
  const data = await resp.json();
  flipDir = data.flip_direction ?? false;
  if (data.line && data.line.length === 2) {
    lineStart = { x: data.line[0][0], y: data.line[0][1] };
    lineEnd   = { x: data.line[1][0], y: data.line[1][1] };
  }
  redrawCanvas();
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let _toastTimer = null;
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('visible');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => toast.classList.remove('visible'), 2200);
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadCameras();
loadLine();
syncCanvas();
