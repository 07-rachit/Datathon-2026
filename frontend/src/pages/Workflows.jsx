import React, { useState, useEffect, useCallback } from "react";
import {
  createWorkflow,
  fetchWorkflows,
  fetchWorkflowDetail,
  executeWorkflow,
  cancelWorkflow,
  fetchPendingApprovals,
  submitApprovalDecision,
  fetchWorkflowStats,
} from "../lib/api";

const PlayIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const CheckIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const CrossIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const RefreshIcon = ({ spinning }) => (
  <svg className={`w-3.5 h-3.5 ${spinning ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const ShieldAlertIcon = () => (
  <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const PlusIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
);

export default function Workflows() {
  const [activeTab, setActiveTab] = useState("workflows"); // workflows | approvals
  const [workflows, setWorkflows] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState({});

  // Pagination & Filtering
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  // Create Workflow Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState("case_investigation");
  const [newDesc, setNewDesc] = useState("");

  // Inspect Workflow Modal
  const [selectedWf, setSelectedWf] = useState(null);
  const [wfDetail, setWfDetail] = useState(null);

  // Approval decision comments map
  const [approvalComments, setApprovalComments] = useState({});

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const params = { page, page_size: 15 };
      if (searchQuery.trim()) params.q = searchQuery.trim();
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.workflow_type = typeFilter;

      const [wfRes, appRes, statsRes] = await Promise.all([
        fetchWorkflows(params),
        fetchPendingApprovals().catch(() => []),
        fetchWorkflowStats().catch(() => null),
      ]);

      setWorkflows(wfRes.results || []);
      setTotal(wfRes.total || 0);
      setTotalPages(wfRes.total_pages || 1);
      setApprovals(appRes || []);
      if (statsRes) setStats(statsRes);
    } catch (err) {
      console.error("Failed to load workflows:", err);
    } finally {
      setLoading(false);
    }
  }, [page, searchQuery, statusFilter, typeFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await createWorkflow({
        workflow_type: newType,
        title: newTitle || "New Multi-Step Workflow",
        description: newDesc,
      });
      setShowCreateModal(false);
      setNewTitle("");
      setNewDesc("");
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail?.message || "Failed to create workflow");
    }
  };

  const handleExecute = async (id) => {
    setActionLoading((prev) => ({ ...prev, [id]: true }));
    try {
      const updated = await executeWorkflow(id);
      setWorkflows((prev) => prev.map((w) => (w.id === id ? updated : w)));
      if (selectedWf?.id === id) setWfDetail(updated);
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail?.message || "Execution error");
    } finally {
      setActionLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const handleCancel = async (id) => {
    if (!confirm("Are you sure you want to cancel this workflow?")) return;
    try {
      const updated = await cancelWorkflow(id);
      setWorkflows((prev) => prev.map((w) => (w.id === id ? updated : w)));
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail?.message || "Failed to cancel workflow");
    }
  };

  const handleDecision = async (appId, decision) => {
    const comments = approvalComments[appId] || "";
    try {
      await submitApprovalDecision(appId, { decision, comments });
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail?.message || "Failed to submit decision");
    }
  };

  const openInspectModal = async (wf) => {
    setSelectedWf(wf);
    try {
      const detail = await fetchWorkflowDetail(wf.id);
      setWfDetail(detail);
    } catch (err) {
      console.error(err);
    }
  };

  const getRiskBadge = (risk) => {
    switch (risk) {
      case "CRITICAL":
        return <span className="px-2 py-0.5 text-xs font-bold rounded bg-rose-500/20 text-rose-400 border border-rose-500/40">CRITICAL</span>;
      case "HIGH":
        return <span className="px-2 py-0.5 text-xs font-bold rounded bg-amber-500/20 text-amber-400 border border-amber-500/40">HIGH</span>;
      case "MEDIUM":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-500/10 text-slate-400 border border-slate-500/30">LOW</span>;
    }
  };

  const getStatusBadge = (st) => {
    switch (st) {
      case "COMPLETED":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">COMPLETED</span>;
      case "WAITING_FOR_APPROVAL":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse">WAITING APPROVAL</span>;
      case "RUNNING":
      case "RESUMING":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 animate-pulse">RUNNING</span>;
      case "REJECTED":
      case "CANCELLED":
      case "FAILED":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">{st}</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-800 text-slate-300 border border-slate-700">{st}</span>;
    }
  };

  return (
    <div className="p-6 space-y-6 text-slate-100 bg-slate-950 min-h-screen">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Multi-Step Workflow Orchestration
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Resumable AI agent execution plans, risk-classified step progression, and human approval gates.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs rounded-lg transition flex items-center gap-2 shadow-lg shadow-cyan-500/20"
          >
            <PlusIcon />
            Plan New Workflow
          </button>
          <button
            onClick={loadData}
            className="px-3.5 py-2 bg-slate-800 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 hover:bg-slate-700 flex items-center gap-1.5"
          >
            <RefreshIcon spinning={loading} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400">Total Workflows</div>
            <div className="text-xl font-bold text-white mt-1">{stats?.total_workflows ?? 0}</div>
          </div>
          <span className="p-3 bg-cyan-500/10 text-cyan-400 rounded-lg font-mono text-xs font-bold">WF</span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400">Pending Approvals</div>
            <div className="text-xl font-bold text-amber-400 mt-1">{stats?.pending_approval_requests ?? 0}</div>
          </div>
          <ShieldAlertIcon />
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400">Completed Workflows</div>
            <div className="text-xl font-bold text-emerald-400 mt-1">{stats?.completed_workflows ?? 0}</div>
          </div>
          <span className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-lg"><CheckIcon /></span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400">Rejected / Failed</div>
            <div className="text-xl font-bold text-rose-400 mt-1">{stats?.failed_or_rejected ?? 0}</div>
          </div>
          <span className="p-2.5 bg-rose-500/10 text-rose-400 rounded-lg"><CrossIcon /></span>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center border-b border-slate-800">
        <button
          onClick={() => setActiveTab("workflows")}
          className={`px-5 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === "workflows"
              ? "border-cyan-400 text-cyan-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Workflow Orchestrator ({total})
        </button>

        <button
          onClick={() => setActiveTab("approvals")}
          className={`px-5 py-2.5 text-xs font-semibold border-b-2 transition flex items-center gap-2 ${
            activeTab === "approvals"
              ? "border-amber-400 text-amber-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Human Approval Center
          {approvals.length > 0 && (
            <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-500 text-slate-950 rounded-full">
              {approvals.length} PENDING
            </span>
          )}
        </button>
      </div>

      {/* TAB 1: WORKFLOW ORCHESTRATOR */}
      {activeTab === "workflows" && (
        <div className="space-y-4">
          {/* Main Table */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Workflow Title</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Risk Level</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Step Progress</th>
                    <th className="py-3 px-4">Initiator</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {loading ? (
                    <tr>
                      <td colSpan="7" className="py-8 text-center text-slate-500">
                        Loading workflow execution telemetry...
                      </td>
                    </tr>
                  ) : workflows.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="py-8 text-center text-slate-500">
                        No workflows found. Click "Plan New Workflow" to initiate one.
                      </td>
                    </tr>
                  ) : (
                    workflows.map((w) => (
                      <tr key={w.id} className="hover:bg-slate-800/40 transition">
                        <td className="py-3 px-4 font-medium text-white">
                          <div className="font-semibold text-cyan-400 hover:underline cursor-pointer" onClick={() => openInspectModal(w)}>
                            {w.title}
                          </div>
                          {w.description && <div className="text-[11px] text-slate-400">{w.description}</div>}
                        </td>

                        <td className="py-3 px-4 font-mono text-slate-300">{w.workflow_type}</td>

                        <td className="py-3 px-4">{getRiskBadge(w.risk_level)}</td>

                        <td className="py-3 px-4">{getStatusBadge(w.status)}</td>

                        <td className="py-3 px-4 w-40">
                          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                            <span>Step {w.current_step_index} / {w.total_steps}</span>
                            <span>{w.progress_pct}%</span>
                          </div>
                          <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                            <div className="bg-cyan-500 h-full transition-all duration-300" style={{ width: `${w.progress_pct}%` }} />
                          </div>
                        </td>

                        <td className="py-3 px-4 text-slate-400">{w.initiator_user_name || "System"}</td>

                        <td className="py-3 px-4 text-right space-x-2">
                          {w.status !== "COMPLETED" && w.status !== "REJECTED" && w.status !== "CANCELLED" && (
                            <button
                              disabled={actionLoading[w.id]}
                              onClick={() => handleExecute(w.id)}
                              className="px-2.5 py-1 text-[11px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded hover:bg-cyan-500/20 font-medium inline-flex items-center gap-1"
                            >
                              <PlayIcon />
                              {w.status === "WAITING_FOR_APPROVAL" ? "Check Gate" : "Execute Step"}
                            </button>
                          )}
                          <button
                            onClick={() => openInspectModal(w)}
                            className="px-2.5 py-1 text-[11px] bg-slate-800 text-slate-300 border border-slate-700 rounded hover:bg-slate-700"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: APPROVAL CENTER */}
      {activeTab === "approvals" && (
        <div className="space-y-4">
          <div className="text-sm font-semibold text-white">Pending Human Review Requests</div>
          {approvals.length === 0 ? (
            <div className="p-8 bg-slate-900/60 border border-slate-800 rounded-xl text-center text-slate-500 text-xs">
              No pending approval requests. High-risk actions will pause here for officer signoff.
            </div>
          ) : (
            approvals.map((appReq) => (
              <div key={appReq.id} className="bg-slate-900/90 border border-amber-500/30 rounded-xl p-5 space-y-4 shadow-xl">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <ShieldAlertIcon />
                      <h3 className="text-base font-bold text-white">Human Approval Gate Required</h3>
                      {getRiskBadge(appReq.risk_level)}
                    </div>
                    <p className="text-xs text-slate-400 mt-1">{appReq.risk_explanation}</p>
                  </div>
                  <div className="text-xs font-mono text-slate-400">Request ID: {appReq.id.slice(0, 8)}</div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block font-medium">Affected Resource</span>
                    <span className="text-white font-mono">{appReq.affected_resources || "N/A"}</span>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block font-medium">Expected Impact</span>
                    <span className="text-slate-200">{appReq.expected_impact || "N/A"}</span>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block font-medium">Proposed Action</span>
                    <span className="text-cyan-400 font-mono">{appReq.proposed_action || "N/A"}</span>
                  </div>
                </div>

                {/* Reviewer Comment Box */}
                <div>
                  <textarea
                    rows={2}
                    placeholder="Enter review decision comments or authorization rationale..."
                    value={approvalComments[appReq.id] || ""}
                    onChange={(e) => setApprovalComments({ ...approvalComments, [appReq.id]: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-end gap-3 pt-1">
                  <button
                    onClick={() => handleDecision(appReq.id, "REJECTED")}
                    className="px-4 py-2 bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20 text-xs font-semibold rounded-lg transition"
                  >
                    Reject Workflow
                  </button>

                  <button
                    onClick={() => handleDecision(appReq.id, "APPROVED")}
                    className="px-5 py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold rounded-lg transition shadow-lg shadow-emerald-500/20 flex items-center gap-1.5"
                  >
                    <CheckIcon />
                    Approve & Resume Execution
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Plan New Workflow Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-950 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">Plan Multi-Step Workflow</h3>

            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Workflow Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-white"
                >
                  <option value="case_investigation">Case Investigation (4 Steps)</option>
                  <option value="financial_seizure">Financial Account Seizure (4 Steps - CRITICAL)</option>
                  <option value="suspect_warrant">Judicial Arrest Warrant (4 Steps - CRITICAL)</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Workflow Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Audit Syndicate Transactions & Freeze Account"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-white"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Description</label>
                <textarea
                  rows={3}
                  placeholder="Context and investigative scope..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-white"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-lg"
                >
                  Generate Plan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Inspect Workflow Modal */}
      {selectedWf && wfDetail && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-950 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">{wfDetail.title}</h3>
                <div className="text-xs text-slate-400 mt-0.5">{wfDetail.workflow_type}</div>
              </div>
              <button onClick={() => { setSelectedWf(null); setWfDetail(null); }} className="text-slate-400 hover:text-white">
                <CrossIcon />
              </button>
            </div>

            {/* Step-by-Step Timeline */}
            <div className="space-y-3">
              <div className="text-xs font-semibold text-slate-300">Execution Step Plan</div>
              {wfDetail.steps?.map((step) => (
                <div key={step.id} className="p-3.5 bg-slate-900 border border-slate-800 rounded-lg space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-white">
                      Step #{step.step_number}: {step.step_name}
                    </span>
                    <div className="flex items-center gap-2">
                      {getRiskBadge(step.risk_level)}
                      {getStatusBadge(step.status)}
                    </div>
                  </div>
                  {step.output_result && (
                    <pre className="text-[11px] bg-slate-950 p-2 rounded text-cyan-300 font-mono overflow-x-auto">
                      {JSON.stringify(step.output_result, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
