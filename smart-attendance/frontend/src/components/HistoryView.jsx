import { useState, useEffect } from "react";
import { Download, Filter, Loader } from "lucide-react";
import { format, parseISO } from "date-fns";
import { api } from "../lib/api";

function fmtTime(iso) {
  if (!iso) return "—";
  try { return format(parseISO(iso), "HH:mm:ss"); } catch { return "—"; }
}

function fmtDuration(minutes) {
  if (minutes == null) return "—";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function exportCsv(records) {
  const rows = [
    ["Employee", "ID", "Date", "Entry", "Exit", "Duration", "Status"],
    ...records.map((r) => [
      r.employee_name,
      r.employee_code,
      r.date,
      r.entry_time ? fmtTime(r.entry_time) : "",
      r.exit_time ? fmtTime(r.exit_time) : "",
      fmtDuration(r.total_minutes),
      r.status,
    ]),
  ];
  const csv = rows.map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `attendance-history.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function HistoryView() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [date, setDate] = useState(format(new Date(), "yyyy-MM-dd"));

  async function load() {
    setLoading(true);
    try {
      const data = await api.historyAttendance(date || null);
      setRecords(data);
    } catch (_) {}
    setLoading(false);
  }

  useEffect(() => { load(); }, [date]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">History</h1>
          <p className="text-slate-400 text-sm mt-1">{records.length} records</p>
        </div>
        <button
          onClick={() => exportCsv(records)}
          disabled={!records.length}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium transition-colors disabled:opacity-40"
        >
          <Download size={15} />
          Export CSV
        </button>
      </div>

      <div className="flex items-center gap-3 p-4 bg-slate-900 border border-slate-800 rounded-xl">
        <Filter size={15} className="text-slate-500" />
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="bg-transparent text-sm text-slate-200 focus:outline-none"
        />
        <button
          onClick={() => setDate("")}
          className="ml-auto text-xs text-slate-500 hover:text-slate-300"
        >
          Clear filter
        </button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-slate-500">
            <Loader size={24} className="animate-spin" />
          </div>
        ) : records.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
            No records for this period
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Employee</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Date</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Entry</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Exit</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Duration</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {records.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4">
                      <p className="font-medium text-slate-200">{r.employee_name}</p>
                      <p className="text-xs text-slate-500 font-mono">{r.employee_code}</p>
                    </td>
                    <td className="py-3 px-4 text-slate-400">{r.date}</td>
                    <td className="py-3 px-4 text-slate-300">{fmtTime(r.entry_time)}</td>
                    <td className="py-3 px-4 text-slate-300">{fmtTime(r.exit_time)}</td>
                    <td className="py-3 px-4 text-slate-300">{fmtDuration(r.total_minutes)}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        r.status === "completed"
                          ? "bg-slate-700 text-slate-300"
                          : "bg-emerald-500/15 text-emerald-400"
                      }`}>
                        {r.status === "completed" ? "Completed" : "Present"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
