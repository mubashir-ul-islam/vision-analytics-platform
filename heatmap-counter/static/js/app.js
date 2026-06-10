'use strict';

// ── Utilities ────────────────────────────────────────────────────────────────

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

let _toastTimer;
function showToast(msg, duration = 2500) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('visible');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove('visible'), duration);
}

function formatTime(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
}

async function apiFetch(url, opts = {}) {
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });
    return res.json();
  } catch (e) {
    console.error(url, e);
    return null;
  }
}

// ── Element refs ─────────────────────────────────────────────────────────────

const $ = id => document.getElementById(id);

const cameraSelect     = $('camera-select');
const resolutionSelect = $('resolution-select');
const applyCameraBtn   = $('apply-camera-btn');
const cameraUrlInput   = $('camera-url-input');
const connectUrlBtn    = $('connect-url-btn');
const modelSelect      = $('model-select');
const deviceSelect     = $('device-select');

const confRange  = $('conf-range');
const confVal    = $('conf-val');
const iouRange   = $('iou-range');
const iouVal     = $('iou-val');
const trackerSel = $('tracker-select');
const bufRange   = $('track-buffer-range');
const bufVal     = $('track-buffer-val');
const minFramesRange = $('min-track-frames-range');
const minFramesVal   = $('min-track-frames-val');
const strideRange = $('vid-stride-range');
const strideVal  = $('vid-stride-val');

const colormapSel = $('colormap-select');
const alphaRange  = $('alpha-range');
const alphaVal    = $('alpha-val');

const resetHeatmapBtn = $('reset-heatmap-btn');
const resetCountsBtn  = $('reset-counts-btn');

const fpsBadge       = $('fps-badge');
const statOccupancy  = $('stat-occupancy');
const statVisitors   = $('stat-visitors');
const statSession    = $('stat-session');

// ── Camera loading ───────────────────────────────────────────────────────────

async function loadCameras() {
  const cameras = await apiFetch('/api/cameras');
  if (!cameras) return;
  cameraSelect.innerHTML = '';
  if (cameras.length === 0) {
    cameraSelect.innerHTML = '<option value="0">Default (0)</option>';
    return;
  }
  cameras.forEach(idx => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = `Camera ${idx}`;
    cameraSelect.appendChild(opt);
  });
  cameraSelect.value = INITIAL_STATE.camera_index;
  resolutionSelect.value = `${INITIAL_STATE.width}x${INITIAL_STATE.height}`;

  // Pre-fill URL input if a network camera was last used
  if (INITIAL_STATE.camera_url) {
    cameraUrlInput.value = INITIAL_STATE.camera_url;
  }
}

applyCameraBtn.addEventListener('click', async () => {
  const idx = parseInt(cameraSelect.value, 10);
  const [w, h] = resolutionSelect.value.split('x').map(Number);
  applyCameraBtn.disabled = true;
  applyCameraBtn.textContent = 'Switching…';
  const data = await apiFetch('/api/camera', {
    method: 'POST',
    body: JSON.stringify({ index: idx, width: w, height: h }),
  });
  applyCameraBtn.disabled = false;
  applyCameraBtn.textContent = 'Apply Camera';
  if (data && data.ok) {
    showToast(`Camera ${idx} active (${data.actual_width}×${data.actual_height})`);
    _reloadStreams();
  } else {
    showToast(data ? data.error : 'Failed to switch camera');
  }
});

// ── IP / network camera connect ───────────────────────────────────────────────

function _reloadStreams() {
  ['det-img', 'heat-img'].forEach(id => {
    const img = $(id);
    const src = img.src;
    img.src = '';
    setTimeout(() => { img.src = src; }, 250);
  });
}

connectUrlBtn.addEventListener('click', async () => {
  const url = cameraUrlInput.value.trim();
  if (!url) { showToast('Please enter an RTSP or HTTP URL'); return; }
  connectUrlBtn.disabled = true;
  connectUrlBtn.textContent = 'Connecting…';
  const data = await apiFetch('/api/camera', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
  connectUrlBtn.disabled = false;
  connectUrlBtn.textContent = 'Connect';
  if (data && data.ok) {
    showToast(`IP camera connected (${data.actual_width}×${data.actual_height})`);
    _reloadStreams();
  } else {
    showToast(data ? data.error : 'Failed to connect to IP camera', 4000);
  }
});

// ── Parameter controls ───────────────────────────────────────────────────────

function populateParams(params) {
  if (params.model)         modelSelect.value    = params.model;
  if (params.device != null) deviceSelect.value  = params.device;
  if (params.conf != null)  { confRange.value    = params.conf;   confVal.textContent  = parseFloat(params.conf).toFixed(2); }
  if (params.iou != null)   { iouRange.value     = params.iou;    iouVal.textContent   = parseFloat(params.iou).toFixed(2); }
  if (params.tracker)       trackerSel.value     = params.tracker;
  if (params.track_buffer != null)     { bufRange.value = params.track_buffer; bufVal.textContent = params.track_buffer; }
  if (params.min_track_frames != null) { minFramesRange.value = params.min_track_frames; minFramesVal.textContent = params.min_track_frames; }
  if (params.vid_stride != null)   { strideRange.value = params.vid_stride; strideVal.textContent = params.vid_stride; }
  if (params.colormap != null)     colormapSel.value = params.colormap;
  if (params.heatmap_alpha != null) { alphaRange.value = params.heatmap_alpha; alphaVal.textContent = parseFloat(params.heatmap_alpha).toFixed(2); }
}

const REINIT_PARAMS = new Set(['model', 'tracker', 'device', 'conf', 'iou', 'track_buffer']);

const sendParams = debounce(async (params) => {
  const needsReinit = Object.keys(params).some(k => REINIT_PARAMS.has(k));
  if (needsReinit) showToast('Applying… (heatmap will reset)', 3000);
  await apiFetch('/api/params', { method: 'POST', body: JSON.stringify(params) });
}, 400);

// Slider helpers
function bindSlider(range, display, key, fmt = v => parseFloat(v).toFixed(2)) {
  range.addEventListener('input', () => {
    display.textContent = fmt(range.value);
    sendParams({ [key]: parseFloat(range.value) });
  });
}

function bindSelect(el, key) {
  el.addEventListener('change', () => {
    const val = isNaN(el.value) ? el.value : (el.value.includes('.') ? parseFloat(el.value) : parseInt(el.value, 10));
    sendParams({ [key]: val });
  });
}

bindSlider(confRange,   confVal,   'conf');
bindSlider(iouRange,    iouVal,    'iou');
bindSlider(bufRange,       bufVal,       'track_buffer',    v => String(parseInt(v, 10)));
bindSlider(minFramesRange, minFramesVal, 'min_track_frames', v => String(parseInt(v, 10)));
bindSlider(strideRange,    strideVal,   'vid_stride',       v => String(parseInt(v, 10)));
bindSlider(alphaRange,  alphaVal,  'heatmap_alpha');

bindSelect(modelSelect,   'model');
bindSelect(deviceSelect,  'device');
bindSelect(trackerSel,    'tracker');
bindSelect(colormapSel,   'colormap');

// ── Stats polling ────────────────────────────────────────────────────────────

async function pollStats() {
  const data = await apiFetch('/api/stats');
  if (!data) return;
  statOccupancy.textContent = data.occupancy ?? '—';
  statVisitors.textContent  = data.total_visitors ?? '—';
  statSession.textContent   = formatTime(data.session_seconds ?? 0);
  fpsBadge.textContent      = `${data.fps ?? '--'} fps`;
}

// ── Action buttons ───────────────────────────────────────────────────────────

resetHeatmapBtn.addEventListener('click', async () => {
  await apiFetch('/api/heatmap/reset', { method: 'POST' });
  showToast('Heatmap reset');
});

resetCountsBtn.addEventListener('click', async () => {
  await apiFetch('/api/stats/reset', { method: 'POST' });
  statOccupancy.textContent = '0';
  statVisitors.textContent  = '0';
  statSession.textContent   = '00:00:00';
  showToast('Counts reset');
});

// ── Init ─────────────────────────────────────────────────────────────────────

async function init() {
  await loadCameras();
  const params = await apiFetch('/api/params');
  if (params) populateParams(params);
  else populateParams(INITIAL_STATE);
  pollStats();
  setInterval(pollStats, 1000);
}

init();
