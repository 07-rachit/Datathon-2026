import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchCases } from "../lib/api.js";

const STATUS_OPTIONS = ["", "open", "closed", "under_review"];
const SEVERITY_OPTIONS = ["", "low", "medium", "high", "critical"];

export default function Cases() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [data, setData] = useState({ total: 0, results: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runSearch() {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (q) params.q = q;
      if (status) params.status = status;
      if (severity) params.severity = severity;
      const res = await fetchCases(params);
      setData(res);
    } catch (err) {
      setError("Could not load cases. Is the API running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    runSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-8">
      <div className="mb-6">
        <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">RECORDS</p>
        <h2 className="font-display text-3xl text-ink">Case Search</h2>
      </div>

      <div className="bg-panel border border-line rounded-md p-4 mb-6 flex gap-3 items-end flex-wrap">
        <div className="flex-1 min-w-[220px]">
          <label className="block text-xs font-mono text-muted mb-1">SEARCH</label>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runSearch()}
            placeholder="Case ID, title, station..."
            className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
          />
        </div>
        <div>
          <label className="block text-xs font-mono text-muted mb-1">STATUS</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s ? s.replace("_", " ") : "All"}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-mono text-muted mb-1">SEVERITY</label>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
          >
            {SEVERITY_OPTIONS.map((s) => (
              <option key={s} value={s}>{s || "All"}</option>
            ))}
          </select>
        </div>
        <button
          onClick={runSearch}
          className="bg-amber text-base font-semibold rounded px-5 py-2 text-sm hover:brightness-110 transition"
        >
          Search
        </button>
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
              <th className="text-left px-4 py-3">Case ID</th>
              <th className="text-left px-4 py-3">Title</th>
              <th className="text-left px-4 py-3">District</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Severity</th>
              <th className="text-left px-4 py-3">Incident Date</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((c) => (
              <tr
                key={c.id}
                onClick={() => navigate(`/cases/${c.id}`)}
                className="border-b border-line/50 hover:bg-panel2 transition cursor-pointer"
              >
                <td className="px-4 py-3 font-mono text-teal text-xs">{c.case_id}</td>
                <td className="px-4 py-3 text-ink">{c.title}</td>
                <td className="px-4 py-3 text-muted">{c.district}</td>
                <td className="px-4 py-3 text-muted capitalize">{c.status.replace("_", " ")}</td>
                <td className="px-4 py-3 text-muted capitalize">{c.severity}</td>
                <td className="px-4 py-3 text-muted">
                  {new Date(c.incident_date).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {!loading && data.results.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted">
                  No cases match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-muted text-xs font-mono mt-3">{data.total} total case(s)</p>
    </div>
  );
}
