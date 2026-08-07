import { useState, useEffect } from "react";
import { fetchActivityHistory, fetchActivityStats, deleteActivityRecord, formatApiError } from "../lib/api.js";

export default function ActivityHistory() {
  const [activities, setActivities] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter & Search states
  const [searchQuery, setSearchQuery] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("timestamp_desc");
  const [viewMode, setViewMode] = useState("timeline"); // "timeline" | "table"
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  // Selected Activity Detail Modal
  const [selectedActivity, setSelectedActivity] = useState(null);

  // Get current user role
  const currentUser = JSON.parse(localStorage.getItem("ci_user") || "{}");
  const isAdmin = currentUser.role === "admin";

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    loadActivities();
  }, [page, searchQuery, moduleFilter, statusFilter, sortBy]);

  async function loadStats() {
    try {
      const data = await fetchActivityStats();
      setStats(data);
    } catch (err) {
      console.warn("Failed to load activity stats:", err);
    }
  }

  async function loadActivities() {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        page_size: 15,
        sort_by: sortBy,
      };
      if (searchQuery.trim()) params.q = searchQuery.trim();
      if (moduleFilter) params.module = moduleFilter;
      if (statusFilter) params.status = statusFilter;

      const data = await fetchActivityHistory(params);
      setActivities(data.results || []);
      setTotalPages(data.total_pages || 1);
      setTotalItems(data.total || 0);
    } catch (err) {
      setError(formatApiError(err).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Are you sure you want to delete this activity log record?")) return;
    try {
      await deleteActivityRecord(id);
      loadActivities();
      loadStats();
      if (selectedActivity?.id === id) setSelectedActivity(null);
    } catch (err) {
      alert(formatApiError(err).message);
    }
  }

  function getModuleIcon(mod) {
    switch (mod) {
      case "cases": return "📁";
      case "ai_assistant": return "🤖";
      case "citizen_reports": return "📢";
      case "collaboration": return "🤝";
      case "admin": return "⚙️";
      case "finance": return "💳";
      case "export": return "📄";
      case "import": return "📥";
      default: return "⚡";
    }
  }

  function getStatusBadgeClass(statusStr) {
    switch (statusStr) {
      case "success": return "bg-teal/10 text-teal border-teal/30";
      case "failed": return "bg-crit/10 text-crit border-crit/30";
      case "warning": return "bg-amber/10 text-amber border-amber/30";
      default: return "bg-panel2 text-muted border-line";
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 font-body">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">📜</span>
            <h1 className="font-display text-2xl text-ink tracking-wide">Persistent Activity History</h1>
            <span className="font-mono text-xs bg-teal/10 text-teal border border-teal/20 px-2 py-0.5 rounded">
              {totalItems} Recorded Actions
            </span>
          </div>
          <p className="text-xs text-muted mt-1">
            Searchable event trail tracking AI outputs, case edits, citizen reports, automation runs, and workflow decisions.
          </p>
        </div>

        {/* Stats Mini Badges */}
        {stats && (
          <div className="flex items-center gap-3 font-mono text-xs">
            <div className="bg-panel border border-line p-2.5 rounded text-center">
              <span className="text-muted block text-[10px]">TOTAL EVENTS</span>
              <span className="text-amber font-bold text-sm">{stats.total_activities}</span>
            </div>
            <div className="bg-panel border border-line p-2.5 rounded text-center">
              <span className="text-muted block text-[10px]">MODULES</span>
              <span className="text-teal font-bold text-sm">{stats.by_module?.length || 0}</span>
            </div>
          </div>
        )}
      </div>

      {/* Control Bar: Filters, Search & View Mode */}
      <div className="bg-panel border border-line rounded-lg p-4 space-y-3 shadow-md">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Search */}
          <div className="md:col-span-2 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
              placeholder="Search history by title, description, module, user, or metadata..."
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal pl-8"
            />
            <span className="absolute left-2.5 top-2.5 text-muted text-xs">🔍</span>
          </div>

          {/* Module Filter */}
          <select
            value={moduleFilter}
            onChange={(e) => { setModuleFilter(e.target.value); setPage(1); }}
            className="bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
          >
            <option value="">All Modules</option>
            <option value="cases">Cases & FIRs</option>
            <option value="ai_assistant">AI Case Assistant</option>
            <option value="citizen_reports">Citizen Reports</option>
            <option value="collaboration">Collaboration & Tasks</option>
            <option value="admin">User Admin</option>
            <option value="finance">Financial Crime</option>
            <option value="import">CSV Import</option>
            <option value="export">Report Export</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
          >
            <option value="">All Statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="warning">Warning</option>
            <option value="pending">Pending</option>
          </select>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 border-t border-line/60">
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-muted">SORT:</span>
            <button
              onClick={() => setSortBy(sortBy === "timestamp_desc" ? "timestamp_asc" : "timestamp_desc")}
              className="bg-panel2 hover:bg-line border border-line px-2.5 py-1 rounded text-ink transition flex items-center gap-1"
            >
              <span>{sortBy === "timestamp_desc" ? "⬇ Newest First" : "⬆ Oldest First"}</span>
            </button>
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-1 bg-panel2 border border-line p-0.5 rounded text-xs font-mono">
            <button
              onClick={() => setViewMode("timeline")}
              className={`px-3 py-1 rounded transition ${viewMode === "timeline" ? "bg-teal text-base font-bold" : "text-muted hover:text-ink"}`}
            >
              ⏳ Timeline
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`px-3 py-1 rounded transition ${viewMode === "table" ? "bg-teal text-base font-bold" : "text-muted hover:text-ink"}`}
            >
              📊 Table View
            </button>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-crit/10 border border-crit/30 p-4 rounded text-crit font-mono text-xs">
          ⚠️ {error}
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="p-12 text-center text-muted font-mono text-xs">
          <span className="animate-spin inline-block mr-2">⚙️</span> Loading persistent activity history...
        </div>
      ) : activities.length === 0 ? (
        <div className="p-12 text-center bg-panel border border-line rounded-lg space-y-2">
          <p className="text-muted font-mono text-sm">No activity records found matching filters.</p>
          <button
            onClick={() => { setSearchQuery(""); setModuleFilter(""); setStatusFilter(""); setPage(1); }}
            className="text-xs font-mono text-teal hover:underline"
          >
            Clear Filters
          </button>
        </div>
      ) : viewMode === "timeline" ? (
        /* TIMELINE VIEW */
        <div className="space-y-3 relative pl-6 border-l-2 border-line/80 ml-3">
          {activities.map((item) => (
            <div key={item.id} className="relative group">
              {/* Timeline dot */}
              <div className="absolute -left-[31px] top-3.5 w-4 h-4 rounded-full bg-panel border-2 border-teal flex items-center justify-center text-[9px]">
                {getModuleIcon(item.module)}
              </div>

              <div className="bg-panel border border-line rounded-lg p-4 hover:border-teal/50 transition shadow-sm space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`font-mono text-[10px] uppercase px-2 py-0.5 rounded border ${getStatusBadgeClass(item.status)}`}>
                      {item.status}
                    </span>
                    <span className="font-mono text-xs font-bold text-ink">{item.title}</span>
                    <span className="font-mono text-[10px] bg-panel2 text-muted px-2 py-0.5 rounded border border-line">
                      {item.module}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 font-mono text-xs text-muted">
                    <span>{new Date(item.timestamp).toLocaleString()}</span>
                    {item.execution_duration_ms && (
                      <span className="text-teal text-[11px]">{item.execution_duration_ms}ms</span>
                    )}
                  </div>
                </div>

                <p className="text-xs text-ink/80 leading-relaxed font-body">{item.description}</p>

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-line/50 font-mono text-[11px]">
                  <div className="flex items-center gap-2 text-muted">
                    <span>👤 {item.user_name || "System"}</span>
                    {item.user_role && (
                      <span className="text-[10px] bg-line/40 px-1.5 py-0.2 rounded uppercase">
                        {item.user_role}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSelectedActivity(item)}
                      className="text-teal hover:underline font-bold"
                    >
                      🔍 Inspect Details &rarr;
                    </button>
                    {isAdmin && (
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="text-crit/70 hover:text-crit hover:underline ml-2"
                      >
                        🗑️ Delete
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* TABLE VIEW */
        <div className="bg-panel border border-line rounded-lg overflow-x-auto shadow-md">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="bg-panel2 border-b border-line text-muted uppercase tracking-wider text-[11px]">
                <th className="p-3">Timestamp</th>
                <th className="p-3">Module</th>
                <th className="p-3">Activity</th>
                <th className="p-3">User</th>
                <th className="p-3">Status</th>
                <th className="p-3">Latency</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/60">
              {activities.map((item) => (
                <tr key={item.id} className="hover:bg-panel2/50 transition">
                  <td className="p-3 text-muted text-[11px] whitespace-nowrap">
                    {new Date(item.timestamp).toLocaleString()}
                  </td>
                  <td className="p-3 font-bold">
                    <span className="flex items-center gap-1.5">
                      <span>{getModuleIcon(item.module)}</span>
                      <span>{item.module}</span>
                    </span>
                  </td>
                  <td className="p-3">
                    <div className="font-bold text-ink">{item.title}</div>
                    <div className="text-[11px] text-muted truncate max-w-xs">{item.description}</div>
                  </td>
                  <td className="p-3 text-muted">
                    {item.user_name || "System"}
                  </td>
                  <td className="p-3">
                    <span className={`text-[10px] uppercase px-2 py-0.5 rounded border ${getStatusBadgeClass(item.status)}`}>
                      {item.status}
                    </span>
                  </td>
                  <td className="p-3 text-teal">
                    {item.execution_duration_ms ? `${item.execution_duration_ms}ms` : "-"}
                  </td>
                  <td className="p-3 text-right whitespace-nowrap space-x-2">
                    <button
                      onClick={() => setSelectedActivity(item)}
                      className="text-teal hover:underline font-bold"
                    >
                      Inspect
                    </button>
                    {isAdmin && (
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="text-crit/70 hover:text-crit hover:underline"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-line pt-4 font-mono text-xs">
          <span className="text-muted">
            Page {page} of {totalPages} ({totalItems} records)
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="bg-panel2 hover:bg-line border border-line px-3 py-1.5 rounded disabled:opacity-40"
            >
              &larr; Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="bg-panel2 hover:bg-line border border-line px-3 py-1.5 rounded disabled:opacity-40"
            >
              Next &rarr;
            </button>
          </div>
        </div>
      )}

      {/* Activity Detail Inspector Modal */}
      {selectedActivity && (
        <div className="fixed inset-0 z-50 bg-base/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-panel border border-line rounded-xl max-w-3xl w-full p-6 space-y-4 shadow-2xl relative max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">{getModuleIcon(selectedActivity.module)}</span>
                <h2 className="font-display text-xl text-ink">{selectedActivity.title}</h2>
              </div>
              <button
                onClick={() => setSelectedActivity(null)}
                className="text-muted hover:text-ink font-mono text-sm px-2 py-1 bg-panel2 rounded"
              >
                ✕ Close
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs bg-panel2 p-3 rounded border border-line">
              <div>
                <span className="text-muted block text-[10px]">ACTIVITY ID</span>
                <span className="text-ink text-[11px] font-bold">{selectedActivity.id.slice(0, 12)}...</span>
              </div>
              <div>
                <span className="text-muted block text-[10px]">MODULE</span>
                <span className="text-teal font-bold">{selectedActivity.module}</span>
              </div>
              <div>
                <span className="text-muted block text-[10px]">USER</span>
                <span className="text-ink">{selectedActivity.user_name || "System"}</span>
              </div>
              <div>
                <span className="text-muted block text-[10px]">STATUS</span>
                <span className={`text-[10px] uppercase font-bold ${selectedActivity.status === "success" ? "text-teal" : "text-crit"}`}>
                  {selectedActivity.status}
                </span>
              </div>
            </div>

            {selectedActivity.description && (
              <div>
                <h3 className="font-mono text-xs text-muted mb-1 uppercase">Description</h3>
                <p className="text-xs text-ink leading-relaxed bg-panel2 p-3 rounded border border-line">
                  {selectedActivity.description}
                </p>
              </div>
            )}

            {/* JSON Metadata Viewer */}
            <div>
              <h3 className="font-mono text-xs text-muted mb-1 uppercase">Structured Payload & Metadata</h3>
              <pre className="bg-panel2 border border-line p-3 rounded text-[11px] font-mono text-teal overflow-x-auto max-h-60">
                {selectedActivity.metadata_json
                  ? JSON.stringify(selectedActivity.metadata_json, null, 2)
                  : "// No additional metadata captured"}
              </pre>
            </div>

            <div className="flex items-center justify-between border-t border-line pt-3 font-mono text-xs">
              <span className="text-muted">Timestamp: {new Date(selectedActivity.timestamp).toUTCString()}</span>
              {isAdmin && (
                <button
                  onClick={() => handleDelete(selectedActivity.id)}
                  className="bg-crit/10 hover:bg-crit/20 text-crit border border-crit/30 px-3 py-1 rounded"
                >
                  Delete Record
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
