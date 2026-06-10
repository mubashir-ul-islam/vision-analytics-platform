const BASE = "";

async function req(method, path, body, isForm = false) {
  const opts = { method, headers: {} };
  if (body && !isForm) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  } else if (body && isForm) {
    opts.body = body;
  }
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // System
  status: () => req("GET", "/api/system/status"),
  updateConfig: (key) => req("PUT", "/api/system/config", { compreface_api_key: key }),
  listCameras: () => req("GET", "/api/system/cameras"),
  setCameras: (entrance_source, exit_source) => req("PUT", "/api/system/cameras", { entrance_source, exit_source }),

  // Employees
  listEmployees: () => req("GET", "/api/employees"),
  createEmployee: (data) => req("POST", "/api/employees", data),
  deleteEmployee: (id) => req("DELETE", `/api/employees/${id}`),
  enrollUpload: (id, file) => {
    const fd = new FormData();
    fd.append("file", file);
    return req("POST", `/api/employees/${id}/enroll`, fd, true);
  },
  enrollCapture: (id) => req("POST", `/api/employees/${id}/enroll/capture`),

  // Attendance
  todayAttendance: () => req("GET", "/api/attendance/today"),
  historyAttendance: (date, employeeId) => {
    const params = new URLSearchParams();
    if (date) params.set("date", date);
    if (employeeId) params.set("employee_id", employeeId);
    return req("GET", `/api/attendance/history?${params}`);
  },
};
