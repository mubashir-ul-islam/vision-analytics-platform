import { format, parseISO } from "date-fns";
import { LogIn, LogOut, Clock } from "lucide-react";
import clsx from "clsx";

function fmtTime(iso) {
  if (!iso) return "—";
  try {
    return format(parseISO(iso), "HH:mm:ss");
  } catch {
    return "—";
  }
}

function fmtDuration(minutes) {
  if (minutes == null) return "—";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function AttendanceTable({ records, loading }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
        Loading attendance…
      </div>
    );
  }

  if (!records.length) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-slate-500 gap-2">
        <Clock size={32} className="opacity-40" />
        <p className="text-sm">No attendance records yet today</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800">
            <th className="text-left py-3 px-4 text-slate-400 font-medium">Employee</th>
            <th className="text-left py-3 px-4 text-slate-400 font-medium">ID</th>
            <th className="text-left py-3 px-4 text-slate-400 font-medium">Entry</th>
            <th className="text-left py-3 px-4 text-slate-400 font-medium">Exit</th>
            <th className="text-left py-3 px-4 text-slate-400 font-medium">Duration</th>
            <th className="text-left py-3 px-4 text-slate-400 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/50">
          {records.map((r) => (
            <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
              <td className="py-3 px-4 font-medium text-slate-200">{r.employee_name}</td>
              <td className="py-3 px-4 text-slate-400 font-mono text-xs">{r.employee_code}</td>
              <td className="py-3 px-4 text-slate-300">
                <span className="flex items-center gap-1.5">
                  <LogIn size={13} className="text-emerald-400" />
                  {fmtTime(r.entry_time)}
                </span>
              </td>
              <td className="py-3 px-4 text-slate-300">
                <span className="flex items-center gap-1.5">
                  <LogOut size={13} className="text-rose-400" />
                  {fmtTime(r.exit_time)}
                </span>
              </td>
              <td className="py-3 px-4 text-slate-300">{fmtDuration(r.total_minutes)}</td>
              <td className="py-3 px-4">
                <span
                  className={clsx(
                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                    r.status === "completed"
                      ? "bg-slate-700 text-slate-300"
                      : "bg-emerald-500/15 text-emerald-400"
                  )}
                >
                  {r.status === "completed" ? "Completed" : "Present"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
