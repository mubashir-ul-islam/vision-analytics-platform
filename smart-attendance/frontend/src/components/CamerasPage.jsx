import { useState, useEffect } from "react";
import { RefreshCw, Save, Loader, AlertCircle, Usb, Wifi } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import CameraFeed from "./CameraFeed";

function isUrl(s) {
  return typeof s === "string" && (s.startsWith("rtsp://") || s.startsWith("http://") || s.startsWith("https://"));
}

function CameraSourceInput({ label, source, setSource, available }) {
  const [mode, setMode] = useState(isUrl(source) ? "ip" : "usb");
  const [urlDraft, setUrlDraft] = useState(isUrl(source) ? source : "");

  function switchMode(m) {
    setMode(m);
    if (m === "usb") {
      const first = available[0];
      setSource(first ? String(first.index) : "0");
    } else {
      setSource(urlDraft);
    }
  }

  function handleUrlChange(v) {
    setUrlDraft(v);
    setSource(v);
  }

  function handleUsbChange(v) {
    setSource(v);
  }

  return (
    <div className="space-y-2">
      <label className="text-xs font-medium text-slate-400">{label}</label>

      {/* Mode toggle */}
      <div className="flex rounded-lg border border-slate-700 overflow-hidden w-fit">
        {[
          { key: "usb", icon: Usb, label: "USB Camera" },
          { key: "ip", icon: Wifi, label: "IP Camera" },
        ].map(({ key, icon: Icon, label: ml }) => (
          <button
            key={key}
            onClick={() => switchMode(key)}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors",
              mode === key
                ? "bg-brand-600 text-white"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            )}
          >
            <Icon size={12} />
            {ml}
          </button>
        ))}
      </div>

      {/* Input for selected mode */}
      {mode === "usb" ? (
        <select
          value={source}
          onChange={(e) => handleUsbChange(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-3 py-2 focus:outline-none focus:border-brand-500"
        >
          {available.map((cam) => (
            <option key={cam.index} value={String(cam.index)}>
              {cam.label}
            </option>
          ))}
          {available.length === 0 && (
            <option value={source}>{`Camera ${source}`}</option>
          )}
        </select>
      ) : (
        <input
          type="text"
          value={urlDraft}
          onChange={(e) => handleUrlChange(e.target.value)}
          placeholder="rtsp://user:pass@192.168.1.100:554/stream"
          className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-3 py-2 focus:outline-none focus:border-brand-500 placeholder-slate-600"
        />
      )}
    </div>
  );
}

function CameraPicker({ systemStatus, onSaved }) {
  const [available, setAvailable] = useState([]);
  const [entrance, setEntrance] = useState("0");
  const [exit, setExit] = useState("0");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listCameras();
      setAvailable(data.available);
      setEntrance(String(data.current.entrance));
      setExit(String(data.current.exit));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function save() {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await api.setCameras(entrance, exit);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      onSaved?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-200">Camera Assignment</h2>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Scan USB cameras
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl px-3 py-2">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-slate-500 text-sm py-2">
          <Loader size={14} className="animate-spin" />
          Scanning available cameras…
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-6">
          <CameraSourceInput
            label="Entrance Camera"
            source={entrance}
            setSource={setEntrance}
            available={available}
          />
          <CameraSourceInput
            label="Exit Camera"
            source={exit}
            setSource={setExit}
            available={available}
          />
        </div>
      )}

      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={save}
          disabled={saving || loading}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-xl transition-colors disabled:opacity-50"
        >
          {saving ? <Loader size={14} className="animate-spin" /> : <Save size={14} />}
          Apply & Restart Cameras
        </button>
        {success && <span className="text-xs text-emerald-400">Cameras restarted successfully</span>}
      </div>
    </div>
  );
}

export default function CamerasPage({ systemStatus, onStatusRefresh }) {
  const cameras = systemStatus?.cameras || {};

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Cameras</h1>
        <p className="text-slate-400 text-sm mt-1">Assign USB or IP cameras for entrance and exit</p>
      </div>

      <CameraPicker systemStatus={systemStatus} onSaved={onStatusRefresh} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CameraFeed type="entry" label="Entrance Camera" active={cameras.entrance} />
        <CameraFeed type="exit" label="Exit Camera" active={cameras.exit} />
      </div>
    </div>
  );
}
