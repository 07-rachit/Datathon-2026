import { useEffect, useState } from "react";
import { fetchAuditLogs, getCurrentUser } from "../lib/api.js";

const ACTION_COLOR = {
  chat_query: "#3FD6C1",
  create_case: "#F0A202",
  export_case_report: "#E8833A",
  export_chat_report: "#E8833A",
};

export default function AuditTrail() {
  const [data, setData] = useState({ total: 0, results: [] });
  const [error, setError] = useState("");
  const user = getCurrentUser();

  useEffect(() => {
    if (user?.role !== "admin") return;
    fetchAuditLogs()
      .then(setData)
      .catch(() => setError("Could not load audit logs. Is the API running?"));
  }, [user]);

  if (user?.role !== "admin") {
    return (
      <div className="p-8">
        <p className="text-muted text-sm">
          Audit trail access is restricted to admin accounts.
        </p>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">EXPLAINABLE AI · ACCOUNTABILITY</p>
        <h2 className="font-display text-3xl text-ink">Audit Trail</h2>
        <p className="text-muted text-sm mt-1">
          Every AI query, case creation, and report export is logged here for full traceability.
        </p>
      </div>

      {error && (
        <p className="text-crit text-sm font-mono border border-crit/40 bg-crit/10 rounded px-4 py-3 mb-4">
          {error}
        </p>
      )}

      <div className="bg-panel border border-line rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-muted text-xs font-mono uppercase">
              <th className="text-left px-4 py-3">Timestamp</th>
              <th className="text-left px-4 py-3">User</th>
              <th className="text-left px-4 py-3">Action</th>
              <th className="text-left px-4 py-3">Detail</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((log) => (
              <tr key={log.id} className="border-b border-line/50 hover:bg-panel2 transition">
                <td className="px-4 py-3 text-muted font-mono text-xs whitespace-nowrap">
                  {new Date(log.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-ink text-xs">
                  {log.user_name || "System"}
                  {log.user_email && <span className="text-muted"> · {log.user_email}</span>}
                </td>
                <td className="px-4 py-3">
                  <span
                    className="text-xs font-mono uppercase px-2 py-1 rounded"
                    style={{
                      color: ACTION_COLOR[log.action] || "#7C8AA3",
                      border: `1px solid ${ACTION_COLOR[log.action] || "#7C8AA3"}55`,
                    }}
                  >
                    {log.action.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted text-xs max-w-md truncate" title={log.detail || ""}>
                  {log.detail || "-"}
                </td>
              </tr>
            ))}
            {data.results.length === 0 && !error && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-muted">
                  No audit entries yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-muted text-xs font-mono mt-3">{data.total} logged event(s)</p>
    </div>
  );
}
