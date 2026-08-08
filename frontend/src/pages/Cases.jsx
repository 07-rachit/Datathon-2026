import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchCases, getCurrentUser } from "../lib/api.js";

const STATUS_OPTIONS = ["", "open", "closed", "under_review"];
const SEVERITY_OPTIONS = ["", "low", "medium", "high", "critical"];
const LABEL_OPTIONS = ["", "Suspected", "Verified", "Needs Review", "Unreviewed"];

const ROLE_SCOPES = [
  { id: "all", label: "Admin Overview", icon: "👑", desc: "All security case records" },
  { id: "investigator", label: "Investigator View", icon: "🔍", desc: "Active & assigned investigation cases" },
  { id: "reviewer", label: "Reviewer View", icon: "📋", desc: "Pending review decisions & notes" },
  { id: "authority", label: "Authority HQ", icon: "🏛️", desc: "High-severity & statutory FIR cases" },
  { id: "hospital", label: "Hospital / Medico-Legal", icon: "🏥", desc: "Medico-legal & emergency security incidents" },
  { id: "user", label: "User / Citizen Scope", icon: "👤", desc: "User-assigned & citizen reported cases" },
];

export default function Cases() {
  const navigate = useNavigate();
  const currentUser = getCurrentUser();

  const [roleScope, setRoleScope] = useState("all");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [investigationLabel, setInvestigationLabel] = useState("");

  const [data, setData] = useState({ total: 0, page: 1, page_size: 20, active_role_scope: "all", results: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runSearch(scopeToUse) {
    const scope = scopeToUse !== undefined ? scopeToUse : roleScope;
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (q) params.q = q;
      if (status) params.status = status;
      if (severity) params.severity = severity;
      if (investigationLabel) params.investigation_label = investigationLabel;
      if (scope && scope !== "all") params.role_scope = scope;

      const res = await fetchCases(params);
      setData(res);
    } catch (err) {
      setError("Could not load security cases. Is the backend server running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    runSearch(roleScope);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleScope, status, severity, investigationLabel]);

  function handleSelectRoleScope(scopeId) {
    setRoleScope(scopeId);
    runSearch(scopeId);
  }

  const renderLabelBadge = (label) => {
    const l = label || "Unreviewed";
    if (l === "Suspected") {
      return <span className="bg-amber/20 text-amber border border-amber/40 px-2 py-0.5 rounded text-[11px] font-mono font-semibold">⚠️ Suspected</span>;
    }
    if (l === "Verified") {
      return <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 px-2 py-0.5 rounded text-[11px] font-mono font-semibold">✓ Verified</span>;
    }
    if (l === "Needs Review") {
      return <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-2 py-0.5 rounded text-[11px] font-mono font-semibold">🔍 Needs Review</span>;
    }
    return <span className="bg-slate-700/40 text-slate-400 border border-slate-600 px-2 py-0.5 rounded text-[11px] font-mono">Unreviewed</span>;
  };

  const activeScopeMeta = ROLE_SCOPES.find((r) => r.id === roleScope) || ROLE_SCOPES[0];

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">SECURITY CASE MANAGEMENT</p>
          <h2 className="font-display text-3xl text-ink">Role-Aware Case Search & Scoped Filters</h2>
        </div>
        <div className="bg-panel2 border border-line rounded p-2.5 flex items-center gap-3 self-start md:self-auto text-xs font-mono">
          <span className="text-muted">Current User Role:</span>
          <span className="bg-teal/20 text-teal border border-teal/40 px-2.5 py-0.5 rounded font-bold uppercase">
            {currentUser?.role || "analyst"}
          </span>
        </div>
      </div>

      {/* Role-Aware Security Case Filter Tabs Bar */}
      <div className="bg-panel border border-line rounded-lg p-4 space-y-3 shadow-sm">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <label className="text-xs font-mono text-muted uppercase tracking-wider font-semibold">
            Role-Aware Security Case Scopes
          </label>
          <span className="text-[11px] font-mono text-slate-400">
            Select a role to demonstrate role-scoped list results
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {ROLE_SCOPES.map((role) => {
            const isActive = roleScope === role.id;
            return (
              <button
                key={role.id}
                role="tab"
                aria-selected={isActive}
                aria-label={`Scope cases for ${role.label}`}
                onClick={() => handleSelectRoleScope(role.id)}
                className={`p-3 rounded-lg border text-left flex flex-col justify-between transition cursor-pointer ${
                  isActive
                    ? "bg-amber/20 border-amber text-ink shadow"
                    : "bg-panel2 border-line text-muted hover:border-teal hover:text-ink"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-lg">{role.icon}</span>
                  {isActive && <span className="text-amber font-mono font-bold text-xs">● Active</span>}
                </div>
                <div>
                  <p className="text-xs font-mono font-bold leading-tight">{role.label}</p>
                  <p className="text-[10px] font-body text-muted line-clamp-1 mt-0.5">{role.desc}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Filter Inputs & Visible Scoped Count Badge */}
      <div className="bg-panel border border-line rounded-lg p-4 space-y-4 shadow-sm">
        {/* Scoped Count Banner */}
        <div className="bg-panel2 border border-line/60 rounded p-3 flex items-center justify-between flex-wrap gap-2 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="text-lg">{activeScopeMeta.icon}</span>
            <div>
              <span className="text-muted">Active Scope: </span>
              <span className="text-ink font-bold">{activeScopeMeta.label}</span>
              <span className="text-muted ml-2">({activeScopeMeta.desc})</span>
            </div>
          </div>
          <div className="bg-teal/10 border border-teal/40 text-teal px-3 py-1 rounded font-bold flex items-center gap-1.5">
            <span>📊</span> Visible Count: {data.total} Security Cases Scoped
          </div>
        </div>

        {/* Search Inputs Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          <div className="md:col-span-2">
            <label className="block text-[10px] font-mono text-muted uppercase mb-1">Keyword Search</label>
            <div className="relative">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runSearch()}
                placeholder="Case ID, title, station name..."
                className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
              />
              {q && (
                <button onClick={() => { setQ(""); runSearch(); }} className="absolute right-2.5 top-2 text-muted hover:text-ink text-xs font-mono">
                  ✕
                </button>
              )}
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-muted uppercase mb-1">Investigation Label</label>
            <select
              value={investigationLabel}
              onChange={(e) => setInvestigationLabel(e.target.value)}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
            >
              {LABEL_OPTIONS.map((l) => (
                <option key={l} value={l}>{l || "All Investigation Labels"}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-muted uppercase mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{s ? s.replace("_", " ").toUpperCase() : "All Statuses"}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-muted uppercase mb-1">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
            >
              {SEVERITY_OPTIONS.map((s) => (
                <option key={s} value={s}>{s ? s.toUpperCase() : "All Severities"}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-crit/10 border border-crit/40 text-crit text-xs font-mono p-4 rounded">
          {error}
        </div>
      )}

      {/* Case Scoped Results Table */}
      <div className="bg-panel border border-line rounded-lg overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-line bg-panel2 text-[10px] font-mono text-muted uppercase tracking-wider">
              <th className="py-3 px-4">Case ID</th>
              <th className="py-3 px-4">Title & Details</th>
              <th className="py-3 px-4">Station / District</th>
              <th className="py-3 px-4">Investigation Label</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Severity</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60 font-body text-xs">
            {loading ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-muted font-mono">
                  Loading security case records for {activeScopeMeta.label}...
                </td>
              </tr>
            ) : data.results.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center space-y-3">
                  <div className="text-3xl">📁</div>
                  <p className="text-muted font-mono text-xs">No security case records match this role scope and filter criteria.</p>
                  <button
                    onClick={() => { setRoleScope("all"); setQ(""); setStatus(""); setSeverity(""); setInvestigationLabel(""); }}
                    title="Reset all filters to view full admin list of security cases"
                    className="bg-amber text-base font-mono font-bold text-xs px-4 py-2 rounded shadow hover:bg-amber/90 transition cursor-pointer"
                  >
                    🔄 Clear Filters & Reset to Admin Overview
                  </button>
                </td>
              </tr>
            ) : (
              data.results.map((c) => (
                <tr key={c.id} className="hover:bg-panel2/50 transition">
                  <td className="py-3 px-4 font-mono font-semibold text-teal">{c.case_id}</td>
                  <td className="py-3 px-4">
                    <p className="font-semibold text-ink leading-snug">{c.title}</p>
                    <p className="text-[11px] text-muted font-mono">{c.crime_type}</p>
                  </td>
                  <td className="py-3 px-4 font-mono text-muted">
                    <p className="text-ink">{c.station_name}</p>
                    <p className="text-[10px]">{c.district}</p>
                  </td>
                  <td className="py-3 px-4">{renderLabelBadge(c.investigation_label)}</td>
                  <td className="py-3 px-4 font-mono uppercase text-[11px]">{c.status.replace("_", " ")}</td>
                  <td className="py-3 px-4 font-mono uppercase text-[11px]">
                    <span className={c.severity === "critical" ? "text-crit font-bold" : c.severity === "high" ? "text-amber font-semibold" : "text-muted"}>
                      {c.severity}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => navigate(`/cases/${c.id}`)}
                      className="bg-panel2 border border-line hover:border-teal text-ink font-mono text-[11px] px-3 py-1.5 rounded transition"
                    >
                      View Details →
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
