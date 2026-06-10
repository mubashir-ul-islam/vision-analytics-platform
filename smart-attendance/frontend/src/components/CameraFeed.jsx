import { useState } from "react";
import { Camera, WifiOff } from "lucide-react";
import clsx from "clsx";

export default function CameraFeed({ type, label, active }) {
  const [error, setError] = useState(false);
  const src = `/camera/${type}/stream`;

  return (
    <div className="rounded-2xl overflow-hidden bg-slate-900 border border-slate-800 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Camera size={16} className="text-slate-400" />
          <span className="text-sm font-medium text-slate-200">{label}</span>
        </div>
        <span
          className={clsx(
            "flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full",
            active && !error
              ? "bg-emerald-500/15 text-emerald-400"
              : "bg-slate-700 text-slate-400"
          )}
        >
          <span
            className={clsx(
              "w-1.5 h-1.5 rounded-full",
              active && !error ? "bg-emerald-400 animate-pulse" : "bg-slate-500"
            )}
          />
          {active && !error ? "Live" : "Offline"}
        </span>
      </div>

      <div className="relative aspect-video bg-slate-950 flex items-center justify-center">
        {error ? (
          <div className="flex flex-col items-center gap-3 text-slate-500">
            <WifiOff size={40} />
            <p className="text-sm">Camera unavailable</p>
          </div>
        ) : (
          <img
            src={src}
            alt={label}
            className="w-full h-full object-cover"
            onError={() => setError(true)}
          />
        )}
      </div>
    </div>
  );
}
