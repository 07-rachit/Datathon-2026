import React, { useState, useEffect, useCallback } from "react";
import {
  fetchAgentRuns,
  fetchAgentRunDetail,
  fetchAgentRunTree,
  fetchObservabilityStats,
  fetchToolStats,
} from "../lib/api";

const ActivityIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

const CheckIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const ClockIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ZapIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
);

const AlertIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const SearchIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const RefreshIcon = ({ spinning }) => (
  <svg className={`w-3.5 h-3.5 ${spinning ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const FilterIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const CpuIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M3 9h2m-2 6h2m14-6h2m-2 6h2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
  </svg>
);

const DownloadIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

const CloseIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export default function Observability() {
  const [runs, setRuns] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [toolStats, setToolStats] = useState([]);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [agentFilter, setAgentFilter] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Selected Run Drawer
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [runDetail, setRunDetail] = useState(null);
  const [runTree, setRunTree] = useState(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview"); // overview, tree, tools, logs

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const params = {
        page,
        page_size: 15,
      };
      if (searchQuery.trim()) params.q = searchQuery.trim();
      if (statusFilter) params.status = statusFilter;
      if (agentFilter) params.agent_name = agentFilter;

      const [runsRes, statsRes, toolsRes] = await Promise.all([
        fetchAgentRuns(params),
        fetchObservabilityStats().catch(() => null),
        fetchToolStats().catch(() => []),
      ]);

      setRuns(runsRes.results || []);
      setTotal(runsRes.total || 0);
      setTotalPages(runsRes.total_pages || 1);
      if (statsRes) setStats(statsRes);
      if (toolsRes) setToolStats(toolsRes);
    } catch (err) {
      console.error("Failed to load observability telemetry:", err);
    } finally {
      setLoading(false);
    }
  }, [page, searchQuery, statusFilter, agentFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Polling interval when active runs exist
  useEffect(() => {
    if (!autoRefresh) return;
    const hasActive = runs.some((r) => r.status === "RUNNING" || r.status === "RETRYING");
    const intervalTime = hasActive ? 3000 : 10000;

    const timer = setInterval(() => {
      loadData();
    }, intervalTime);

    return () => clearInterval(timer);
  }, [autoRefresh, runs, loadData]);

  const openDrawer = async (runId) => {
    setSelectedRunId(runId);
    setDrawerLoading(true);
    try {
      const [detail, tree] = await Promise.all([
        fetchAgentRunDetail(runId),
        fetchAgentRunTree(runId).catch(() => null),
      ]);
      setRunDetail(detail);
      setRunTree(tree);
    } catch (err) {
      console.error("Failed to fetch run details:", err);
    } finally {
      setDrawerLoading(false);
    }
  };

  const closeDrawer = () => {
    setSelectedRunId(null);
    setRunDetail(null);
    setRunTree(null);
  };

  const getStatusBadge = (st) => {
    switch (st) {
      case "COMPLETED":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">COMPLETED</span>;
      case "RUNNING":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 animate-pulse">RUNNING</span>;
      case "FAILED":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">FAILED</span>;
      case "RETRYING":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">RETRYING</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-500/10 text-slate-400 border border-slate-500/30">{st}</span>;
    }
  };

  const downloadLogs = () => {
    if (!runDetail || !runDetail.logs) return;
    const content = runDetail.logs.join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `agent_run_${runDetail.id}_logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-6 text-slate-100 bg-slate-950 min-h-screen">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-cyan-400 animate-pulse"><ActivityIcon /></span>
            <h1 className="text-2xl font-bold tracking-tight text-white">Tool & Agent Observability</h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time AI execution telemetry, tool invocation trees, latency metrics, decision audit, and prompt sanitization logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition flex items-center gap-2 ${
              autoRefresh
                ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/20"
                : "bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700"
            }`}
          >
            <RefreshIcon spinning={autoRefresh} />
            {autoRefresh ? "Live Auto-Refresh ON" : "Auto-Refresh OFF"}
          </button>
          <button
            onClick={loadData}
            className="px-3.5 py-1.5 bg-slate-800 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 hover:bg-slate-700 flex items-center gap-1.5"
          >
            <RefreshIcon spinning={false} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center gap-4">
          <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-lg">
            <ActivityIcon />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Total Agent Runs</div>
            <div className="text-xl font-bold text-white mt-0.5">{stats?.total_runs ?? 0}</div>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center gap-4">
          <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-lg">
            <CheckIcon />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Success Rate</div>
            <div className="text-xl font-bold text-white mt-0.5">{stats?.success_rate_pct ?? 100}%</div>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center gap-4">
          <div className="p-3 bg-amber-500/10 text-amber-400 rounded-lg">
            <ClockIcon />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Avg Total Latency</div>
            <div className="text-xl font-bold text-white mt-0.5">{stats?.average_latency_ms ?? 0} ms</div>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center gap-4">
          <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-lg">
            <ZapIcon />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Completed Runs</div>
            <div className="text-xl font-bold text-white mt-0.5">{stats?.completed_runs ?? 0}</div>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center gap-4">
          <div className="p-3 bg-rose-500/10 text-rose-400 rounded-lg">
            <AlertIcon />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Failed Executions</div>
            <div className="text-xl font-bold text-white mt-0.5">{stats?.failed_runs ?? 0}</div>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <span className="text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"><SearchIcon /></span>
          <input
            type="text"
            placeholder="Search runs by ID, agent, prompt, decision, or log keywords..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-slate-400"><FilterIcon /></span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50"
            >
              <option value="">All Statuses</option>
              <option value="RUNNING">RUNNING</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="FAILED">FAILED</option>
              <option value="RETRYING">RETRYING</option>
            </select>
          </div>

          <select
            value={agentFilter}
            onChange={(e) => {
              setAgentFilter(e.target.value);
              setPage(1);
            }}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50"
          >
            <option value="">All Agents</option>
            <option value="CrimeIntelAssistant">CrimeIntelAssistant</option>
            <option value="ProactiveCrimeAnalyst">ProactiveCrimeAnalyst</option>
            <option value="CaseInvestigationAgent">CaseInvestigationAgent</option>
            <option value="CyberFraudAgent">CyberFraudAgent</option>
            <option value="MasterOrchestrator">MasterOrchestrator</option>
          </select>
        </div>
      </div>

      {/* Main Execution Runs Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Run ID & Parent</th>
                <th className="py-3 px-4">Agent Name</th>
                <th className="py-3 px-4">Trigger & User</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Total Latency</th>
                <th className="py-3 px-4">Tools Called</th>
                <th className="py-3 px-4">Started At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan="8" className="py-8 text-center text-slate-500">
                    <RefreshIcon spinning={true} />
                    Fetching real-time observability telemetry...
                  </td>
                </tr>
              ) : runs.length === 0 ? (
                <tr>
                  <td colSpan="8" className="py-8 text-center text-slate-500">
                    No agent execution runs matched your search criteria.
                  </td>
                </tr>
              ) : (
                runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/40 transition group">
                    <td className="py-3 px-4 font-mono">
                      <div className="font-semibold text-cyan-400 group-hover:underline cursor-pointer" onClick={() => openDrawer(r.id)}>
                        {r.id.slice(0, 8)}...
                      </div>
                      {r.parent_run_id && (
                        <div className="text-[10px] text-indigo-400 flex items-center gap-1 mt-0.5">
                          Parent: {r.parent_run_id.slice(0, 6)}
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-medium text-white flex items-center gap-1.5">
                        <CpuIcon />
                        {r.agent_name}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{r.execution_type}</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="text-slate-200">{r.user_name || "System"}</div>
                      <div className="text-[10px] text-slate-500">{r.trigger_source}</div>
                    </td>

                    <td className="py-3 px-4">{getStatusBadge(r.status)}</td>

                    <td className="py-3 px-4 font-mono font-medium text-slate-200">
                      {r.total_latency_ms ? `${r.total_latency_ms} ms` : "—"}
                    </td>

                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 text-xs bg-slate-800 text-slate-300 rounded-md font-mono border border-slate-700">
                        {r.tool_calls ? r.tool_calls.length : 0} tools
                      </span>
                    </td>

                    <td className="py-3 px-4 text-slate-400">
                      {new Date(r.started_at || r.created_at).toLocaleTimeString()}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => openDrawer(r.id)}
                        className="px-2.5 py-1 text-[11px] bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 border border-cyan-500/30 rounded-lg font-medium transition flex items-center gap-1 ml-auto"
                      >
                        Inspect
                        <ChevronRightIcon />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="bg-slate-950 px-4 py-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing <span className="text-white font-medium">{runs.length}</span> of <span className="text-white font-medium">{total}</span> execution runs
          </div>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 bg-slate-900 border border-slate-800 rounded disabled:opacity-40 hover:bg-slate-800"
            >
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 bg-slate-900 border border-slate-800 rounded disabled:opacity-40 hover:bg-slate-800"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Registered Tools Performance Rankings */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <CpuIcon />
          Registered Agent Tools Telemetry
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {toolStats.map((t) => (
            <div key={t.tool_name} className="bg-slate-950 border border-slate-800/80 rounded-lg p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-cyan-400 font-medium">{t.tool_name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                  {t.total_invocations} calls
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Avg Latency:</span>
                <span className="text-white font-mono">{t.avg_duration_ms} ms</span>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Failure Rate:</span>
                <span className={t.failure_rate_pct > 0 ? "text-rose-400 font-mono" : "text-emerald-400 font-mono"}>
                  {t.failure_rate_pct}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Run Inspection Side Drawer */}
      {selectedRunId && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-2xl bg-slate-950 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
              <div>
                <div className="flex items-center gap-2">
                  <CpuIcon />
                  <h2 className="text-base font-bold text-white">Execution Telemetry Inspector</h2>
                  {runDetail && getStatusBadge(runDetail.status)}
                </div>
                <div className="text-xs font-mono text-slate-400 mt-1">Run ID: {selectedRunId}</div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={downloadLogs}
                  title="Download execution logs"
                  className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700"
                >
                  <DownloadIcon />
                </button>
                <button onClick={closeDrawer} className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg">
                  <CloseIcon />
                </button>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center border-b border-slate-800 bg-slate-950 px-5">
              {["overview", "tree", "tools", "logs"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2.5 text-xs font-medium border-b-2 capitalize transition ${
                    activeTab === tab
                      ? "border-cyan-400 text-cyan-400 font-semibold"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Drawer Content Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {drawerLoading ? (
                <div className="py-12 text-center text-slate-500">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-cyan-400" />
                  Fetching execution tree and trace logs...
                </div>
              ) : runDetail ? (
                <>
                  {activeTab === "overview" && (
                    <div className="space-y-4">
                      {/* Latency Breakdown Bar */}
                      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                        <div className="text-xs font-semibold text-slate-300">Total Latency Breakdown</div>
                        <div className="text-xl font-bold text-cyan-400 font-mono">{runDetail.total_latency_ms || 0} ms</div>
                        <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden flex">
                          <div
                            style={{ width: `${Math.min(100, ((runDetail.tool_execution_time_ms || 0) / (runDetail.total_latency_ms || 1)) * 100)}%` }}
                            className="bg-cyan-500 h-full"
                            title="Tool execution time"
                          />
                          <div
                            style={{ width: `${Math.min(100, ((runDetail.model_inference_time_ms || 0) / (runDetail.total_latency_ms || 1)) * 100)}%` }}
                            className="bg-indigo-500 h-full"
                            title="Model inference time"
                          />
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500 inline-block"/> Tool Time: {runDetail.tool_execution_time_ms || 0}ms</span>
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-indigo-500 inline-block"/> Model Time: {runDetail.model_inference_time_ms || 0}ms</span>
                        </div>
                      </div>

                      {/* Prompts & Outputs */}
                      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                        <div>
                          <div className="text-xs font-semibold text-slate-400 mb-1">Sanitized Input Prompt</div>
                          <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-lg text-xs font-mono text-slate-200 whitespace-pre-wrap">
                            {runDetail.input_prompt || "None"}
                          </div>
                        </div>

                        <div>
                          <div className="text-xs font-semibold text-slate-400 mb-1">Agent Output Summary</div>
                          <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-lg text-xs font-mono text-slate-200 whitespace-pre-wrap">
                            {runDetail.output_summary || "None"}
                          </div>
                        </div>
                      </div>

                      {/* Decision & Metadata */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                          <div className="text-xs text-slate-400">Final Decision</div>
                          <div className="text-sm font-semibold text-white mt-1">{runDetail.decision || "N/A"}</div>
                        </div>
                        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                          <div className="text-xs text-slate-400">Confidence Score</div>
                          <div className="text-sm font-semibold text-emerald-400 mt-1">
                            {runDetail.confidence_score ? `${(runDetail.confidence_score * 100).toFixed(0)}%` : "N/A"}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeTab === "tree" && (
                    <div className="space-y-4">
                      <div className="text-xs font-semibold text-slate-300">Nested Execution Tree</div>
                      {runTree ? (
                        <div className="space-y-3">
                          {/* Root Run */}
                          <div className="p-3.5 bg-slate-900 border border-cyan-500/40 rounded-xl">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-cyan-400 text-xs">{runTree.root_run.agent_name} (Root)</span>
                              {getStatusBadge(runTree.root_run.status)}
                            </div>
                            <div className="text-xs text-slate-400 mt-1 font-mono">{runTree.root_run.input_prompt}</div>
                          </div>

                          {/* Child Tool Calls */}
                          {runTree.tool_calls.map((tc) => (
                            <div key={tc.id} className="ml-6 p-3 bg-slate-900/60 border border-slate-800 rounded-lg border-l-2 border-l-indigo-400">
                              <div className="flex items-center justify-between text-xs">
                                <span className="font-mono text-indigo-300 font-semibold">{tc.tool_name}</span>
                                <span className="font-mono text-slate-400">{tc.duration_ms} ms</span>
                              </div>
                            </div>
                          ))}

                          {/* Child Runs */}
                          {runTree.child_runs.map((c) => (
                            <div key={c.id} className="ml-6 p-3.5 bg-slate-900 border border-indigo-500/30 rounded-xl">
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-indigo-400 text-xs">{c.agent_name} (Sub-Agent)</span>
                                {getStatusBadge(c.status)}
                              </div>
                              <div className="text-xs text-slate-400 mt-1 font-mono">{c.input_prompt}</div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-slate-500">No execution tree data available.</div>
                      )}
                    </div>
                  )}

                  {activeTab === "tools" && (
                    <div className="space-y-3">
                      <div className="text-xs font-semibold text-slate-300">Tool Calls ({runDetail.tool_calls?.length || 0})</div>
                      {runDetail.tool_calls?.length === 0 ? (
                        <div className="text-xs text-slate-500">No tool invocations recorded for this run.</div>
                      ) : (
                        runDetail.tool_calls.map((tc) => (
                          <div key={tc.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-xs font-bold text-cyan-400">{tc.tool_name}</span>
                              <span className="text-xs font-mono text-slate-400">{tc.duration_ms} ms</span>
                            </div>
                            <div>
                              <div className="text-[11px] text-slate-400">Input Parameters:</div>
                              <pre className="text-[11px] bg-slate-950 p-2 rounded text-slate-300 font-mono overflow-x-auto">
                                {JSON.stringify(tc.input_params, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <div className="text-[11px] text-slate-400">Output Result:</div>
                              <pre className="text-[11px] bg-slate-950 p-2 rounded text-slate-300 font-mono overflow-x-auto">
                                {JSON.stringify(tc.output_result, null, 2)}
                              </pre>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {activeTab === "logs" && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-slate-300">Step-by-Step Execution Logs</div>
                      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-300 space-y-1.5 max-h-96 overflow-y-auto">
                        {runDetail.logs?.map((l, i) => (
                          <div key={i} className="leading-relaxed border-b border-slate-800/40 pb-1">
                            {l}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
