import { useState, useEffect } from "react";
import { BrowserRouter, NavLink, Routes, Route, Navigate } from "react-router-dom";
import { LayoutDashboard, Camera, Users, History, Wifi, WifiOff, ScanFace } from "lucide-react";
import clsx from "clsx";
import { api } from "./lib/api";
import Dashboard from "./components/Dashboard";
import CamerasPage from "./components/CamerasPage";
import EmployeeList from "./components/EmployeeList";
import HistoryView from "./components/HistoryView";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/cameras", label: "Cameras", icon: Camera },
  { to: "/employees", label: "Employees", icon: Users },
  { to: "/history", label: "History", icon: History },
];

function Sidebar({ status }) {
  return (
    <aside className="w-60 shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="p-5 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-brand-600 rounded-xl flex items-center justify-center">
            <ScanFace size={20} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-slate-100 text-sm leading-tight">Smart</p>
            <p className="font-bold text-brand-400 text-sm leading-tight">Attendance</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-600 text-white"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              )
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Status indicator */}
      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-2 text-xs">
          {status?.compreface_ready ? (
            <>
              <Wifi size={13} className="text-emerald-400" />
              <span className="text-emerald-400">Recognition live</span>
            </>
          ) : (
            <>
              <WifiOff size={13} className="text-amber-400" />
              <span className="text-amber-400">Setup required</span>
            </>
          )}
        </div>
      </div>
    </aside>
  );
}

export default function App() {
  const [systemStatus, setSystemStatus] = useState(null);

  async function refreshStatus() {
    try {
      const s = await api.status();
      setSystemStatus(s);
    } catch (_) {}
  }

  useEffect(() => {
    refreshStatus();
    const id = setInterval(refreshStatus, 30000);
    return () => clearInterval(id);
  }, []);

  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar status={systemStatus} />
        <main className="flex-1 p-8 overflow-auto">
          <div className="max-w-5xl mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard systemStatus={systemStatus} onStatusRefresh={refreshStatus} />} />
              <Route path="/cameras" element={<CamerasPage systemStatus={systemStatus} onStatusRefresh={refreshStatus} />} />
              <Route path="/employees" element={<EmployeeList />} />
              <Route path="/history" element={<HistoryView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}
