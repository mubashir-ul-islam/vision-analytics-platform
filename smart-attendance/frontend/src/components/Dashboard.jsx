import { useState, useEffect, useCallback } from "react";
import { Users, UserCheck, UserX, Clock, AlertTriangle, ChevronRight, Key, Loader, Camera, WifiOff } from "lucide-react";
import { format, parseISO } from "date-fns";
import clsx from "clsx";
import { api } from "../lib/api";
import { socket } from "../lib/websocket";
import AttendanceTable from "./AttendanceTable";

// ─── Inline camera feed ───────────────────────────────────────────────────────
function LiveCamera({ src, label, active }) {
  const [error, setError] = useState(false);
  return (
    <div className="bg-slate-950 rounded-xl overflow-hidden border border-slate-800">
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800">
        <span className="flex items-center gap-1.5 text-xs font-medium text-slate-300">
          <Camera size={13} className="text-slate-500" />
          {label}
        </span>
        <span className={clsx(
          "flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium",
          active && !error ? "bg-emerald-500/15 text-emerald-400" : "bg-slate-800 text-slate-500"
        )}>
          <span className={clsx("w-1.5 h-1.5 rounded-full", active && !error ? "bg-emerald-400 animate-pulse" : "bg-slate-600")} />
          {active && !error ? "Live" : "Offline"}
        </span>
      </div>
      <div className="aspect-video flex items-center justify-center bg-slate-950">
        {error ? (
          <div className="flex flex-col items-center gap-2 text-slate-600">
            <WifiOff size={28} />
            <span className="text-xs">Unavailable</span>
          </div>
        ) : (
          <img src={src} alt={label} className="w-full h-full object-cover" onError={() => setError(true)} />
        )}
      </div>
    </div>
  );
}

// ─── Setup banner ─────────────────────────────────────────────────────────────
function SetupBanner({ onSave }) {
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function save() {
    if (!key.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateConfig(key.trim());
      onSave();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-6">
      <div className="flex items-start gap-4">
        <AlertTriangle size={22} className="text-amber-400 shrink-0 mt-0.5" />
        <div className="flex-1 space-y-4">
          <div>
            <h3 className="font-semibold text-amber-300 text-lg">Face Recognition Setup Required</h3>
            <p className="text-slate-400 text-sm mt-1">Complete these steps to activate face recognition:</p>
          </div>
          <ol className="text-sm text-slate-300 space-y-2">
            {[
              <span>Open <a href="http://localhost:8000" target="_blank" rel="noreferrer" className="text-amber-400 hover:underline">http://localhost:8000</a> — the recognition engine dashboard</span>,
              "Register an account (first run only)",
              "Create an Application → add a Recognition Service",
              "Copy the API key from the service card",
            ].map((step, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 text-xs flex items-center justify-center shrink-0 mt-0.5 font-medium">{i + 1}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
          <div className="flex gap-3">
            <div className="flex-1 flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2">
              <Key size={15} className="text-slate-500 shrink-0" />
              <input
                value={key}
                onChange={(e) => setKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && save()}
                placeholder="Paste API key here"
                className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-500 focus:outline-none"
              />
            </div>
            <button
              onClick={save}
              disabled={saving || !key.trim()}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-sm font-medium flex items-center gap-2 transition-colors disabled:opacity-60"
            >
              {saving ? <Loader size={14} className="animate-spin" /> : <ChevronRight size={14} />}
              Activate
            </button>
          </div>
          {error && <p className="text-sm text-rose-400">{error}</p>}
        </div>
      </div>
    </div>
  );
}

// ─── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={22} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-100">{value}</p>
        <p className="text-sm text-slate-400">{label}</p>
      </div>
    </div>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
export default function Dashboard({ systemStatus, onStatusRefresh }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [liveEvents, setLiveEvents] = useState([]);

  async function loadToday() {
    try {
      const data = await api.todayAttendance();
      setRecords(data);
    } catch (_) {}
    setLoading(false);
  }

  const handleEvent = useCallback((event) => {
    if (event.type !== "attendance") return;
    setLiveEvents((prev) => [event, ...prev].slice(0, 50));
    loadToday();
  }, []);

  useEffect(() => {
    loadToday();
    const unsub = socket.subscribe(handleEvent);
    // Fallback polling every 30s in case WebSocket misses an event
    const poll = setInterval(loadToday, 30_000);
    return () => { unsub(); clearInterval(poll); };
  }, [handleEvent]);

  const cameras = systemStatus?.cameras || {};
  const present = records.filter((r) => r.status === "entered").length;
  const exited = records.filter((r) => r.status === "completed").length;
  const total = records.length;

  return (
    <div className="flex gap-6 items-start">
      {/* ── Main content ── */}
      <div className="flex-1 min-w-0 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">{format(new Date(), "EEEE, MMMM d, yyyy")}</p>
        </div>

        {!systemStatus?.compreface_ready && (
          <SetupBanner onSave={() => { onStatusRefresh(); loadToday(); }} />
        )}

        {/* Live camera feeds */}
        <div className="grid grid-cols-2 gap-4">
          <LiveCamera src="/camera/entry/stream" label="Entrance Camera" active={cameras.entrance} />
          <LiveCamera src="/camera/exit/stream" label="Exit Camera" active={cameras.exit} />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <StatCard icon={Users} label="Total Today" value={total} color="bg-indigo-900/50 text-indigo-400" />
          <StatCard icon={UserCheck} label="Currently In" value={present} color="bg-emerald-900/50 text-emerald-400" />
          <StatCard icon={UserX} label="Exited" value={exited} color="bg-slate-800 text-slate-400" />
        </div>

        {/* Today's table */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-slate-400" />
              <h2 className="font-semibold text-slate-200">Today's Attendance</h2>
            </div>
            <span className="text-xs text-slate-500">Live</span>
          </div>
          <AttendanceTable records={records} loading={loading} />
        </div>
      </div>

      {/* ── Activity sidebar ── */}
      <div className="w-72 shrink-0 sticky top-6 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col" style={{ maxHeight: "calc(100vh - 3rem)" }}>
        <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Recent Activity</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {liveEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-16 text-slate-600">
              <Clock size={24} />
              <span className="text-xs">Waiting for events…</span>
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {liveEvents.map((ev, i) => (
                <div
                  key={i}
                  className={clsx(
                    "px-4 py-3 flex flex-col gap-1",
                    ev.status === "entered" ? "bg-emerald-500/5" : ""
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className={clsx("w-2 h-2 rounded-full shrink-0", ev.status === "entered" ? "bg-emerald-400" : "bg-slate-500")} />
                    <span className="text-sm font-medium text-slate-200 truncate">{ev.employee_name}</span>
                  </div>
                  <div className="pl-4 flex items-center justify-between gap-2">
                    <span className={clsx("text-xs", ev.status === "entered" ? "text-emerald-400" : "text-slate-400")}>
                      {ev.status === "entered" ? "Entered" : "Exited"}
                    </span>
                    <span className="text-xs text-slate-500 tabular-nums">
                      {format(parseISO(ev.timestamp), "HH:mm:ss")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
