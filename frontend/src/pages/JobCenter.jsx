import { useState, useEffect, useRef } from "react";
import {
  fetchJobs, fetchJobStats, submitBackgroundJob,
  retryJob, cancelJob, formatApiError
} from "../lib/api.js";

export default function JobCenter() {
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & Pagination
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  // Selected Job for Logs Modal
  const [selectedJob, setSelectedJob] = useState(null);
  const [showLaunchModal, setShowLaunchModal] = useState(false);
  const [newJobType, setNewJobType] = useState("pdf_export");
  const [newEntityId, setNewEntityId] = useState("");
  const [launching, setLaunching] = useState(false);

  const currentUser = JSON.parse(localStorage.getItem("ci_user") || "{}");

  // Auto-polling ref
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    loadJobs();
  }, [page, searchQuery, statusFilter, typeFilter]);

  // Set up 2s auto-refresh for active jobs
  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === "RUNNING" || j.status === "QUEUED" || j.status === "RETRYING");
    if (hasActive) {
      pollIntervalRef.current = setInterval(() => {
        loadJobs(false);
        loadStats();
      }, 2000);
    } else {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    }
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [jobs]);

  async function loadStats() {
    try {
      const data = await fetchJobStats();
      setStats(data);
    } catch (err) {
      console.warn("Failed to load job stats:", err);
    }
  }

  async function loadJobs(showLoading = true) {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        page_size: 15,
      };
      if (searchQuery.trim()) params.q = searchQuery.trim();
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.job_type = typeFilter;

      const data = await fetchJobs(params);
      setJobs(data.results || []);
      setTotalPages(data.total_pages || 1);
      setTotalItems(data.total || 0);

      // Keep selected job updated if drawer open
      if (selectedJob) {
        const updated = (data.results || []).find((j) => j.id === selectedJob.id);
        if (updated) setSelectedJob(updated);
      }
    } catch (err) {
      setError(formatApiError(err).message);
    } finally {
      if (showLoading) setLoading(false);
    }
  }

  async function handleLaunchJob(e) {
    e.preventDefault();
    setLaunching(true);
    try {
      await submitBackgroundJob({
        job_type: newJobType,
        entity_id: newEntityId.trim() || undefined,
        input_payload: {
          submitted_at: new Date().toISOString(),
          requested_by: currentUser.name,
        },
      });
      setShowLaunchModal(false);
      setNewEntityId("");
      loadJobs();
      loadStats();
    } catch (err) {
      alert(formatApiError(err).message);
    } finally {
      setLaunching(false);
    }
  }

  async function handleRetry(jobId) {
    try {
      await retryJob(jobId);
      loadJobs();
      loadStats();
    } catch (err) {
      alert(formatApiError(err).message);
    }
  }

  async function handleCancel(jobId) {
    try {
      await cancelJob(jobId);
      loadJobs();
      loadStats();
    } catch (err) {
      alert(formatApiError(err).message);
    }
  }

  function getStatusBadge(statusStr) {
    switch (statusStr) {
      case "COMPLETED":
        return <span className="bg-teal/10 text-teal border border-teal/30 px-2.5 py-0.5 rounded font-mono text-[10px] uppercase font-bold">✓ COMPLETED</span>;
      case "RUNNING":
        return (
          <span className="bg-amber/10 text-amber border border-amber/30 px-2.5 py-0.5 rounded font-mono text-[10px] uppercase font-bold flex items-center gap-1">
            <span className="animate-spin">⚙️</span> RUNNING
          </span>
        );
      case "QUEUED":
        return <span className="bg-panel2 text-muted border border-line px-2.5 py-0.5 rounded font-mono text-[10px] uppercase font-bold">⏳ QUEUED</span>;
      case "RETRYING":
        return <span className="bg-amber/20 text-amber border border-amber/40 px-2.5 py-0.5 rounded font-mono text-[10px] uppercase font-bold animate-pulse">↻ RETRYING</span>;
      case "FAILED":
        return <span className="bg-crit/10 text-crit border border-crit/30 px-2.5 py-0.5 rounded font-mono text-[10px] uppercase font-bold">✕ FAILED</span>;
      case "CANCELLED":
        return <span className="bg-line/40 text-muted border border-line px-2.5 py-0.5 rounded font-mono text-[10px] uppercase font-bold">∅ CANCELLED</span>;
      default:
        return <span className="bg-panel2 text-muted px-2 py-0.5 rounded font-mono text-[10px]">{statusStr}</span>;
    }
  }

  function getJobIcon(type) {
    switch (type) {
      case "pdf_export": return "📄";
      case "csv_import": return "📥";
      case "citizen_report_analysis": return "📢";
      case "ai_content_generation": return "🤖";
      case "business_analysis": return "📊";
      default: return "⚡";
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 font-body">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">⚙️</span>
            <h1 className="font-display text-2xl text-ink tracking-wide">Background Job Center</h1>
            <span className="font-mono text-xs bg-amber/10 text-amber border border-amber/20 px-2 py-0.5 rounded">
              {totalItems} Jobs Tracked
            </span>
          </div>
          <p className="text-xs text-muted mt-1">
            Asynchronous background task runner with automatic retries, progress tracking, and detailed execution logs.
          </p>
        </div>

        <button
          onClick={() => setShowLaunchModal(true)}
          className="bg-amber hover:bg-amber-hover text-base font-bold font-mono text-xs px-4 py-2.5 rounded shadow transition flex items-center gap-2"
        >
          <span>🚀 Launch Async Job</span>
        </button>
      </div>

      {/* Control Bar */}
      <div className="bg-panel border border-line rounded-lg p-4 space-y-3 shadow-md">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-2 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
              placeholder="Search jobs by ID, type, user, or logs..."
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal pl-8"
            />
            <span className="absolute left-2.5 top-2.5 text-muted text-xs">🔍</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
          >
            <option value="">All Statuses</option>
            <option value="RUNNING">Running</option>
            <option value="QUEUED">Queued</option>
            <option value="COMPLETED">Completed</option>
            <option value="FAILED">Failed</option>
            <option value="RETRYING">Retrying</option>
            <option value="CANCELLED">Cancelled</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className="bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
          >
            <option value="">All Job Types</option>
            <option value="pdf_export">PDF Dossier Export</option>
            <option value="csv_import">CSV Case Import</option>
            <option value="citizen_report_analysis">Citizen Report AI</option>
            <option value="ai_content_generation">AI Content Gen</option>
            <option value="business_analysis">Business Analysis</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="bg-crit/10 border border-crit/30 p-4 rounded text-crit font-mono text-xs">
          ⚠️ {error}
        </div>
      )}

      {/* Main Job List */}
      {loading ? (
        <div className="p-12 text-center text-muted font-mono text-xs">
          <span className="animate-spin inline-block mr-2">⚙️</span> Polling background job status...
        </div>
      ) : jobs.length === 0 ? (
        <div className="p-12 text-center bg-panel border border-line rounded-lg space-y-2">
          <p className="text-muted font-mono text-sm">No background jobs found matching search filters.</p>
          <button
            onClick={() => { setSearchQuery(""); setStatusFilter(""); setTypeFilter(""); setPage(1); }}
            className="text-xs font-mono text-teal hover:underline"
          >
            Clear Filters
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((item) => (
            <div
              key={item.id}
              className="bg-panel border border-line rounded-lg p-4 hover:border-teal/50 transition shadow-sm space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line/60 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{getJobIcon(item.job_type)}</span>
                  <div>
                    <div className="font-mono text-xs font-bold text-ink flex items-center gap-2">
                      <span>{item.job_type}</span>
                      <span className="text-[10px] text-muted font-normal">({item.id.slice(0, 8)})</span>
                    </div>
                    <div className="text-[11px] text-muted font-mono">
                      User: {item.user_name || "System"} • Created: {new Date(item.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {getStatusBadge(item.status)}
                  {item.execution_duration_ms && (
                    <span className="font-mono text-[11px] text-teal">{item.execution_duration_ms}ms</span>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              {(item.status === "RUNNING" || item.status === "RETRYING" || item.status === "QUEUED") && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between font-mono text-[10px] text-muted">
                    <span>Progress: {item.progress_pct}%</span>
                    {item.retry_count > 0 && (
                      <span className="text-amber">Retry attempt {item.retry_count}/{item.max_retries}</span>
                    )}
                  </div>
                  <div className="w-full bg-panel2 h-2 rounded overflow-hidden border border-line">
                    <div
                      className="bg-teal h-full transition-all duration-300"
                      style={{ width: `${Math.max(5, item.progress_pct)}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Output Result / Error preview */}
              {item.status === "COMPLETED" && item.output_result && (
                <div className="bg-teal/5 border border-teal/20 p-2.5 rounded font-mono text-[11px] text-ink flex items-center justify-between">
                  <div className="truncate max-w-xl">
                    <span className="text-teal font-bold mr-2">Result:</span>
                    {JSON.stringify(item.output_result)}
                  </div>
                  {item.output_result.download_url && (
                    <a
                      href={item.output_result.download_url}
                      className="text-teal font-bold hover:underline shrink-0 ml-2"
                    >
                      📥 Download Output
                    </a>
                  )}
                </div>
              )}

              {item.status === "FAILED" && item.error_details && (
                <div className="bg-crit/10 border border-crit/30 p-2.5 rounded font-mono text-[11px] text-crit">
                  <span className="font-bold">Failure Cause:</span> {item.error_details.message || JSON.stringify(item.error_details)}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between font-mono text-xs pt-1">
                <button
                  onClick={() => setSelectedJob(item)}
                  className="text-teal hover:underline font-bold"
                >
                  📜 View Logs ({item.logs?.length || 0})
                </button>

                <div className="flex items-center gap-2">
                  {(item.status === "FAILED" || item.status === "CANCELLED" || item.status === "TIMEOUT") && (
                    <button
                      onClick={() => handleRetry(item.id)}
                      className="bg-amber/10 hover:bg-amber/20 text-amber border border-amber/30 px-3 py-1 rounded font-bold transition"
                    >
                      ↻ Retry Job
                    </button>
                  )}

                  {(item.status === "RUNNING" || item.status === "QUEUED") && (
                    <button
                      onClick={() => handleCancel(item.id)}
                      className="bg-crit/10 hover:bg-crit/20 text-crit border border-crit/30 px-3 py-1 rounded transition"
                    >
                      ✕ Cancel Job
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-line pt-4 font-mono text-xs">
          <span className="text-muted">
            Page {page} of {totalPages} ({totalItems} jobs)
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

      {/* Logs Drawer Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 bg-base/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-panel border border-line rounded-xl max-w-3xl w-full p-6 space-y-4 shadow-2xl relative max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">{getJobIcon(selectedJob.job_type)}</span>
                <h2 className="font-display text-xl text-ink">Job Execution Logs</h2>
                <span className="font-mono text-xs text-muted">({selectedJob.id})</span>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-muted hover:text-ink font-mono text-sm px-2 py-1 bg-panel2 rounded"
              >
                ✕ Close
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs bg-panel2 p-3 rounded border border-line">
              <div>
                <span className="text-muted block text-[10px]">JOB TYPE</span>
                <span className="text-ink font-bold">{selectedJob.job_type}</span>
              </div>
              <div>
                <span className="text-muted block text-[10px]">STATUS</span>
                {getStatusBadge(selectedJob.status)}
              </div>
              <div>
                <span className="text-muted block text-[10px]">RETRY COUNT</span>
                <span className="text-amber font-bold">{selectedJob.retry_count}/{selectedJob.max_retries}</span>
              </div>
              <div>
                <span className="text-muted block text-[10px]">DURATION</span>
                <span className="text-teal font-bold">{selectedJob.execution_duration_ms ? `${selectedJob.execution_duration_ms}ms` : "-"}</span>
              </div>
            </div>

            {/* Execution Log Output */}
            <div>
              <h3 className="font-mono text-xs text-muted mb-1 uppercase">Step-by-Step Execution Log</h3>
              <div className="bg-base border border-line p-3 rounded text-[11px] font-mono text-teal space-y-1 max-h-60 overflow-y-auto">
                {selectedJob.logs && selectedJob.logs.length > 0 ? (
                  selectedJob.logs.map((logMsg, i) => <div key={i}>{logMsg}</div>)
                ) : (
                  <div className="text-muted">// No execution logs recorded yet</div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-line pt-3 font-mono text-xs">
              {(selectedJob.status === "FAILED" || selectedJob.status === "CANCELLED") && (
                <button
                  onClick={() => { handleRetry(selectedJob.id); setSelectedJob(null); }}
                  className="bg-amber hover:bg-amber-hover text-base font-bold px-3 py-1.5 rounded"
                >
                  ↻ Retry Job Now
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Launch New Job Modal */}
      {showLaunchModal && (
        <div className="fixed inset-0 z-50 bg-base/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleLaunchJob}
            className="bg-panel border border-line rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl relative"
          >
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h2 className="font-display text-xl text-ink">Launch Asynchronous Background Job</h2>
              <button
                type="button"
                onClick={() => setShowLaunchModal(false)}
                className="text-muted hover:text-ink font-mono text-sm px-2 py-1 bg-panel2 rounded"
              >
                ✕ Close
              </button>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div>
                <label className="text-muted block mb-1">JOB TYPE</label>
                <select
                  value={newJobType}
                  onChange={(e) => setNewJobType(e.target.value)}
                  className="w-full bg-panel2 border border-line rounded p-2 text-ink focus:outline-none focus:ring-1 focus:ring-teal"
                >
                  <option value="pdf_export">📄 PDF Dossier Export</option>
                  <option value="csv_import">📥 CSV Case Ingestion</option>
                  <option value="citizen_report_analysis">📢 Citizen Report AI Analysis</option>
                  <option value="ai_content_generation">🤖 AI Content Generation</option>
                  <option value="business_analysis">📊 Business Trend Computation</option>
                </select>
              </div>

              <div>
                <label className="text-muted block mb-1">ENTITY ID (OPTIONAL)</label>
                <input
                  type="text"
                  value={newEntityId}
                  onChange={(e) => setNewEntityId(e.target.value)}
                  placeholder="e.g. CASE-1002 or REPORT-99"
                  className="w-full bg-panel2 border border-line rounded p-2 text-ink focus:outline-none focus:ring-1 focus:ring-teal"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-line pt-3 font-mono text-xs">
              <button
                type="button"
                onClick={() => setShowLaunchModal(false)}
                className="bg-panel2 hover:bg-line border border-line px-3 py-2 rounded text-ink"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={launching}
                className="bg-amber hover:bg-amber-hover text-base font-bold px-4 py-2 rounded disabled:opacity-50"
              >
                {launching ? "Launching..." : "Launch Background Job"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
