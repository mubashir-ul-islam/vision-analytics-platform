import { useState, useRef } from "react";
import { Upload, Camera, X, Check, Loader } from "lucide-react";
import { api } from "../lib/api";

export default function EnrollModal({ employee, onClose, onSuccess }) {
  const [mode, setMode] = useState("upload"); // "upload" | "capture"
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef();

  function handleFile(f) {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError(null);
  }

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      if (mode === "upload") {
        if (!file) { setError("Please select an image"); setLoading(false); return; }
        await api.enrollUpload(employee.id, file);
      } else {
        await api.enrollCapture(employee.id);
      }
      onSuccess();
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Enroll Face</h2>
            <p className="text-sm text-slate-400 mt-0.5">{employee.name}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Mode tabs */}
          <div className="flex gap-1 p-1 bg-slate-800 rounded-xl">
            {["upload", "capture"].map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setFile(null); setPreview(null); setError(null); }}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${
                  mode === m
                    ? "bg-brand-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {m === "upload" ? <Upload size={15} /> : <Camera size={15} />}
                {m === "upload" ? "Upload Photo" : "Live Capture"}
              </button>
            ))}
          </div>

          {mode === "upload" ? (
            <div>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
              />
              {preview ? (
                <div className="relative">
                  <img src={preview} alt="preview" className="w-full h-48 object-cover rounded-xl" />
                  <button
                    onClick={() => { setFile(null); setPreview(null); }}
                    className="absolute top-2 right-2 bg-black/60 rounded-full p-1 text-white hover:bg-black/80"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => fileRef.current.click()}
                  className="w-full h-40 border-2 border-dashed border-slate-700 rounded-xl flex flex-col items-center justify-center gap-3 text-slate-500 hover:border-brand-500 hover:text-brand-400 transition-colors"
                >
                  <Upload size={28} />
                  <span className="text-sm">Click to select image</span>
                </button>
              )}
            </div>
          ) : (
            <div className="bg-slate-800 rounded-xl overflow-hidden">
              <img
                src="/camera/entry/stream"
                alt="Live camera"
                className="w-full h-48 object-cover"
              />
              <p className="text-xs text-slate-400 text-center py-2">Entrance camera preview</p>
            </div>
          )}

          {error && (
            <p className="text-sm text-rose-400 bg-rose-500/10 rounded-lg px-3 py-2">{error}</p>
          )}
        </div>

        <div className="flex gap-3 p-6 pt-0">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-800 transition-colors text-sm font-medium"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={loading}
            className="flex-1 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-60"
          >
            {loading ? <Loader size={15} className="animate-spin" /> : <Check size={15} />}
            {mode === "upload" ? "Enroll" : "Capture & Enroll"}
          </button>
        </div>
      </div>
    </div>
  );
}
