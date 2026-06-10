import { useState, useEffect } from "react";
import { UserPlus, Trash2, ScanFace, CheckCircle, AlertCircle, Loader, Users } from "lucide-react";
import { api } from "../lib/api";
import EnrollModal from "./EnrollModal";

export default function EmployeeList() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enrollTarget, setEnrollTarget] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", employee_id: "" });
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    try {
      const data = await api.listEmployees();
      setEmployees(data);
    } catch (_) {}
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function addEmployee(e) {
    e.preventDefault();
    setAdding(true);
    setError(null);
    try {
      await api.createEmployee(form);
      setForm({ name: "", employee_id: "" });
      setShowAdd(false);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  }

  async function deleteEmployee(emp) {
    if (!confirm(`Delete ${emp.name}? This cannot be undone.`)) return;
    try {
      await api.deleteEmployee(emp.id);
      setEmployees((prev) => prev.filter((e) => e.id !== emp.id));
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Employees</h1>
          <p className="text-slate-400 text-sm mt-1">{employees.length} registered</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-sm font-medium transition-colors"
        >
          <UserPlus size={16} />
          Add Employee
        </button>
      </div>

      {showAdd && (
        <form onSubmit={addEmployee} className="bg-slate-900 border border-slate-700 rounded-2xl p-5 space-y-4">
          <h3 className="font-semibold text-slate-200">New Employee</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1.5 block">Full Name</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Jane Smith"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1.5 block">Employee ID</label>
              <input
                required
                value={form.employee_id}
                onChange={(e) => setForm((f) => ({ ...f, employee_id: e.target.value }))}
                placeholder="EMP001"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => { setShowAdd(false); setError(null); }}
              className="flex-1 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={adding}
              className="flex-1 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-60"
            >
              {adding ? <Loader size={14} className="animate-spin" /> : null}
              Create
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40 text-slate-500">
          <Loader size={24} className="animate-spin" />
        </div>
      ) : employees.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 text-slate-500 gap-2">
          <Users size={32} className="opacity-40" />
          <p className="text-sm">No employees yet. Add one to get started.</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {employees.map((emp) => (
            <div
              key={emp.id}
              className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl px-5 py-4 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-brand-900 flex items-center justify-center text-brand-300 font-semibold text-sm">
                  {emp.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-slate-200">{emp.name}</p>
                  <p className="text-xs text-slate-500 font-mono">{emp.employee_id}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {emp.enrolled ? (
                  <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                    <CheckCircle size={14} /> Enrolled
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-xs text-amber-400">
                    <AlertCircle size={14} /> Not enrolled
                  </span>
                )}
                <button
                  onClick={() => setEnrollTarget(emp)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
                >
                  <ScanFace size={13} />
                  {emp.enrolled ? "Re-enroll" : "Enroll"}
                </button>
                <button
                  onClick={() => deleteEmployee(emp)}
                  className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {enrollTarget && (
        <EnrollModal
          employee={enrollTarget}
          onClose={() => setEnrollTarget(null)}
          onSuccess={load}
        />
      )}
    </div>
  );
}
