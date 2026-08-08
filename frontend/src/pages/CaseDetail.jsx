import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api, {
  fetchSimilarCases,
  fetchFinancialTrail,
  fetchCaseTimeline,
  fetchCaseAssignments,
  createCaseAssignment,
  removeCaseAssignment,
  fetchCaseTasks,
  createCaseTask,
  updateCaseTask,
  deleteCaseTask,
  fetchCaseComments,
  createCaseComment,
  deleteCaseComment,
  fetchOfficers,
  fetchCaseInvestigation,
  updateCaseInvestigation,
  getCurrentUser,
} from "../lib/api.js";

const SEVERITY_COLOR = {
  low: "#3FD6C1",
  medium: "#F0A202",
  high: "#E8833A",
  critical: "#E23D5B",
};

const Field = ({ label, value }) => (
  <div className="bg-panel border border-line rounded p-3">
    <p className="text-muted text-[10px] uppercase font-mono">{label}</p>
    <p className="text-ink text-sm font-semibold mt-0.5">{value}</p>
  </div>
);

const Section = ({ title, children }) => (
  <div className="mb-8">
    <h3 className="font-display text-lg text-ink mb-3">{title}</h3>
    {children}
  </div>
);

export default function CaseDetail() {
  const { id } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [similarCases, setSimilarCases] = useState([]);
  const [financialTrail, setFinancialTrail] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [showSensitive, setShowSensitive] = useState(false);

  // Collaboration State
  const [assignments, setAssignments] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [comments, setComments] = useState([]);
  const [officers, setOfficers] = useState([]);
  
  // Investigation Label State
  const [investigationData, setInvestigationData] = useState(null);
  const [showLabelModal, setShowLabelModal] = useState(false);
  const [newLabel, setNewLabel] = useState("Suspected");
  const [newNote, setNewNote] = useState("");
  const [investigationError, setInvestigationError] = useState("");
  const [investigationSubmitting, setInvestigationSubmitting] = useState(false);
  const [investigationSuccessMsg, setInvestigationSuccessMsg] = useState("");

  // Forms state
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assignUserId, setAssignUserId] = useState("");
  const [assignRole, setAssignRole] = useState("Supporting Officer");
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskDesc, setNewTaskDesc] = useState("");
  const [newTaskAssignee, setNewTaskAssignee] = useState("");
  const [newTaskDueDate, setNewTaskDueDate] = useState("");
  const [newCommentText, setNewCommentText] = useState("");
  const [collabError, setCollabError] = useState("");

  const currentUser = getCurrentUser();
  const isAdmin = currentUser?.role === "admin";
  const isAnalyst = currentUser?.role === "analyst";
  const isInvestigator = currentUser?.role === "investigator";
  const isSupervisor = isAdmin || isAnalyst;
  const canModify = isSupervisor || isInvestigator;

  const DEMO_CASE_FALLBACK = {
    id, case_id: `CASE-${id?.toUpperCase() || 'DEMO'}`, title: "Case Intelligence Record",
    crime_type: "General", severity: "medium", status: "open", district: "Patna",
    station_name: "CrimeIntel Demo Station", incident_date: "2026-01-15T00:00:00Z",
    description: "This case is part of the demo dataset. Connect to Supabase or seed the local database to view real case data.",
    latitude: 25.6, longitude: 85.1,
  };

  useEffect(() => {
    api
      .get(`/cases/${id}`)
      .then(({ data }) => setCaseData(data))
      .catch(() => {
        // Try fetching from the cases list to find a match
        api.get(`/cases?page_size=100`)
          .then(({ data }) => {
            const found = (data.results || []).find(c => c.id === id || c.case_id === id);
            if (found) { setCaseData(found); }
            else { setCaseData(DEMO_CASE_FALLBACK); }
          })
          .catch(() => setCaseData(DEMO_CASE_FALLBACK));
      });
    
    fetchSimilarCases(id).then(setSimilarCases).catch(() => setSimilarCases([]));
    fetchFinancialTrail(id).then(setFinancialTrail).catch(() => setFinancialTrail(null));
    fetchCaseTimeline(id).then(setTimeline).catch(() => setTimeline([]));
    fetchCaseInvestigation(id).then(setInvestigationData).catch(() => setInvestigationData(null));

    // Collaboration Data
    loadCollaborationData();
  }, [id]);

  async function handleSaveInvestigationLabel() {
    if (!newNote.trim() || newNote.trim().length < 3) {
      setInvestigationError("Investigator note is required and must be at least 3 characters.");
      return;
    }
    setInvestigationSubmitting(true);
    setInvestigationError("");
    setInvestigationSuccessMsg("");
    try {
      const updated = await updateCaseInvestigation(id, {
        label: newLabel,
        note: newNote.trim(),
      });
      setInvestigationData(updated);
      setCaseData((prev) => ({
        ...prev,
        investigation_label: updated.current_label,
        investigator_note: updated.investigator_note,
        reviewer_name: updated.reviewer_name,
        review_timestamp: updated.review_timestamp,
      }));
      setShowLabelModal(false);
      setInvestigationSuccessMsg(`Investigation label updated to '${updated.current_label}' successfully!`);
      setTimeout(() => setInvestigationSuccessMsg(""), 5000);
    } catch (err) {
      setInvestigationError(err.response?.data?.error?.message || err.response?.data?.detail || "Failed to update investigation label.");
    } finally {
      setInvestigationSubmitting(false);
    }
  }

  const renderLabelBadge = (label) => {
    const l = label || "Unreviewed";
    if (l === "Suspected") {
      return <span className="bg-amber/20 text-amber border border-amber/40 px-2.5 py-1 rounded text-xs font-mono font-semibold">⚠️ Suspected</span>;
    }
    if (l === "Verified") {
      return <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 px-2.5 py-1 rounded text-xs font-mono font-semibold">✓ Verified</span>;
    }
    if (l === "Needs Review") {
      return <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded text-xs font-mono font-semibold">🔍 Needs Review</span>;
    }
    return <span className="bg-slate-700/40 text-slate-400 border border-slate-600 px-2.5 py-1 rounded text-xs font-mono">Unreviewed</span>;
  };

  function loadCollaborationData() {
    fetchCaseAssignments(id).then(setAssignments).catch(() => setAssignments([]));
    fetchCaseTasks(id).then(setTasks).catch(() => setTasks([]));
    fetchCaseComments(id).then(setComments).catch(() => setComments([]));
    fetchOfficers().then(setOfficers).catch(() => setOfficers([]));
  }

  async function handleExport() {
    setExporting(true);
    try {
      const response = await api.get(`/export/cases/${id}/report`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${caseData.case_id}_report.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError("Could not generate the PDF report.");
    } finally {
      setExporting(false);
    }
  }

  // Assignment Handlers
  async function handleAssignOfficer(e) {
    e.preventDefault();
    setCollabError("");
    const targetId = isSupervisor ? assignUserId : currentUser.id;
    if (!targetId) {
      setCollabError("Please select an officer to assign.");
      return;
    }
    try {
      await createCaseAssignment(id, {
        assigned_to_user_id: targetId,
        role_on_case: assignRole,
      });
      setShowAssignModal(false);
      setAssignUserId("");
      fetchCaseAssignments(id).then(setAssignments);
    } catch (err) {
      setCollabError(err.response?.data?.detail || "Failed to assign officer.");
    }
  }

  async function handleRemoveAssignment(assignmentId) {
    setCollabError("");
    try {
      await removeCaseAssignment(id, assignmentId);
      fetchCaseAssignments(id).then(setAssignments);
    } catch (err) {
      setCollabError(err.response?.data?.detail || "Failed to remove assignment.");
    }
  }

  // Task Handlers
  async function handleCreateTask(e) {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    setCollabError("");
    try {
      await createCaseTask(id, {
        title: newTaskTitle.trim(),
        description: newTaskDesc.trim() || null,
        assigned_to_user_id: newTaskAssignee || null,
        due_date: newTaskDueDate ? new Date(newTaskDueDate).toISOString() : null,
      });
      setNewTaskTitle("");
      setNewTaskDesc("");
      setNewTaskAssignee("");
      setNewTaskDueDate("");
      fetchCaseTasks(id).then(setTasks);
    } catch (err) {
      setCollabError(err.response?.data?.detail || "Failed to create task.");
    }
  }

  async function handleToggleTaskStatus(taskId, currentStatus) {
    setCollabError("");
    const nextStatus = currentStatus === "done" ? "todo" : currentStatus === "todo" ? "in_progress" : "done";
    try {
      await updateCaseTask(id, taskId, { status: nextStatus });
      fetchCaseTasks(id).then(setTasks);
    } catch (err) {
      setCollabError(err.response?.data?.detail || "Failed to update task status.");
    }
  }

  async function handleDeleteTask(taskId) {
    setCollabError("");
    try {
      await deleteCaseTask(id, taskId);
      fetchCaseTasks(id).then(setTasks);
    } catch (err) {
      setCollabError(err.response?.data?.detail || "Failed to delete task.");
    }
  }

  // Comment Handlers
  async function handlePostComment(e) {
    e.preventDefault();
    if (!newCommentText.trim()) return;
    setCollabError("");
    try {
      await createCaseComment(id, { content: newCommentText.trim() });
      setNewCommentText("");
      fetchCaseComments(id).then(setComments);
    } catch (err) {
      setCollabError(err.response?.data?.detail || "Failed to post comment.");
    }
  }

  async function handleDeleteComment(commentId) {
    setCollabError("");
    try {
      await deleteCaseComment(id, commentId);
      fetchCaseComments(id).then(setComments);
    } catch (err) {
      setCollabError(err.response?.data?.detail || "Failed to delete comment.");
    }
  }

  if (error) {
    return (
      <div className="p-8">
        <p className="text-crit text-sm font-mono border border-crit/40 bg-crit/10 rounded px-4 py-3">
          {error}
        </p>
        <Link to="/cases" className="text-teal text-sm hover:underline mt-4 inline-block">
          ← Back to case search
        </Link>
      </div>
    );
  }

  if (!caseData) {
    return <div className="p-8 text-muted text-sm font-mono">Loading case file...</div>;
  }

  const fir = caseData.fir_details;
  const comp = caseData.complainant;
  const cs = caseData.chargesheet;

  return (
    <div className="p-8 max-w-4xl">
      <Link to="/cases" className="text-muted text-xs font-mono hover:text-teal transition">
        ← BACK TO CASE SEARCH
      </Link>

      <div className="flex items-start justify-between mt-3 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <p className="font-mono text-teal text-xs tracking-[0.2em]">{caseData.case_id}</p>
            {fir?.crime_no && (
              <span className="font-mono text-[10px] bg-panel2 border border-teal/40 text-teal px-2 py-0.5 rounded">
                FIR Crime No: {fir.crime_no}
              </span>
            )}
          </div>
          <h2 className="font-display text-3xl text-ink">{caseData.title}</h2>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="bg-amber text-base font-semibold rounded px-4 py-2 text-sm hover:brightness-110 transition disabled:opacity-50 whitespace-nowrap"
        >
          {exporting ? "Generating..." : "⬇ Export PDF Report"}
        </button>
      </div>

      {collabError && (
        <div className="mb-4 border border-crit/40 bg-crit/10 text-crit text-xs font-mono p-3 rounded">
          {collabError}
        </div>
      )}

      {investigationSuccessMsg && (
        <div className="mb-4 border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 text-xs font-mono p-3 rounded flex items-center justify-between">
          <span>✓ {investigationSuccessMsg}</span>
          <button onClick={() => setInvestigationSuccessMsg("")} className="text-muted hover:text-ink">✕</button>
        </div>
      )}

      {/* ── SECURITY CASE INVESTIGATION REVIEW & LABELS SECTION ───────────────── */}
      <Section title="🏷️ Security Case Investigation Review & Labels">
        <div className="bg-panel border border-line rounded-lg p-5 space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-line pb-4">
            <div>
              <p className="text-muted text-xs font-mono uppercase mb-1">Current Investigation Status</p>
              <div className="flex items-center gap-3">
                {renderLabelBadge(caseData.investigation_label)}
                {investigationData?.reviewer_name && (
                  <span className="text-xs text-muted font-mono">
                    Reviewed by <strong className="text-ink">{investigationData.reviewer_name}</strong> on{" "}
                    {new Date(investigationData.review_timestamp).toLocaleString()}
                  </span>
                )}
              </div>
            </div>

            {canModify && (
              <button
                onClick={() => {
                  setNewLabel(caseData.investigation_label && caseData.investigation_label !== "Unreviewed" ? caseData.investigation_label : "Suspected");
                  setNewNote(caseData.investigator_note || "");
                  setShowLabelModal(true);
                }}
                className="bg-amber hover:bg-amber/90 text-base font-mono font-bold text-xs px-4 py-2 rounded shadow transition flex items-center gap-2"
              >
                <span>🏷️</span> Update Investigation Label & Note
              </button>
            )}
          </div>

          {/* Current Note */}
          {caseData.investigator_note && (
            <div className="bg-panel2 border border-line rounded p-4">
              <p className="text-muted text-xs font-mono uppercase mb-1">Investigator Rationale & Evidence Note</p>
              <p className="text-ink text-sm leading-relaxed whitespace-pre-wrap">{caseData.investigator_note}</p>
            </div>
          )}

          {/* Chronological Investigation History Timeline */}
          <div>
            <h4 className="font-mono text-xs text-muted uppercase tracking-wider mb-3">Investigation Audit History</h4>
            {!investigationData || !investigationData.history || investigationData.history.length === 0 ? (
              <p className="text-muted text-xs font-mono">No prior investigation label reviews recorded.</p>
            ) : (
              <div className="space-y-3 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-line">
                {investigationData.history.map((hist) => (
                  <div key={hist.id} className="relative pl-8 bg-panel2 border border-line rounded p-3 text-xs font-mono">
                    <div className="absolute left-2 top-3.5 w-2.5 h-2.5 rounded-full bg-teal" />
                    <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-muted">Changed from</span>
                        <span className="text-muted font-bold">{hist.previous_label || "Unreviewed"}</span>
                        <span className="text-teal">➔</span>
                        {renderLabelBadge(hist.new_label)}
                      </div>
                      <span className="text-muted text-[11px]">
                        {new Date(hist.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-ink mt-1 font-body text-xs">{hist.investigator_note}</p>
                    <p className="text-muted text-[10px] mt-1">Reviewer: {hist.reviewer_name} (ID: {hist.reviewer_id})</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Section>

      {/* ── CASE COLLABORATION SECTION ───────────────────────────────────── */}
      <Section title="🤝 Case Collaboration & Coordination">
        <div className="space-y-6 bg-panel border border-line rounded-lg p-5">
          {/* 1. Assigned Officers Sub-section */}
          <div>
            <div className="flex items-center justify-between mb-3 border-b border-line/40 pb-2">
              <h4 className="font-mono text-xs text-amber uppercase font-semibold">
                Assigned Officers ({assignments.length})
              </h4>
              {canModify && (
                <button
                  onClick={() => setShowAssignModal(!showAssignModal)}
                  className="bg-teal text-bg font-mono text-xs px-2.5 py-1 rounded font-semibold hover:brightness-110 transition"
                >
                  {isSupervisor ? "+ Assign Officer" : "+ Claim Case"}
                </button>
              )}
            </div>

            {showAssignModal && (
              <form onSubmit={handleAssignOfficer} className="bg-panel2 border border-line p-3 rounded mb-4 space-y-3">
                <p className="text-xs font-mono text-ink">
                  {isSupervisor ? "Assign an officer to this case:" : "Self-assign to this case:"}
                </p>
                {isSupervisor && (
                  <select
                    value={assignUserId}
                    onChange={(e) => setAssignUserId(e.target.value)}
                    className="w-full bg-bg border border-line rounded px-3 py-1.5 text-xs text-ink font-body"
                    required
                  >
                    <option value="">-- Select Officer --</option>
                    {officers.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.name} ({o.email}) - {o.role.toUpperCase()}
                      </option>
                    ))}
                  </select>
                )}
                <div>
                  <label className="text-[11px] font-mono text-muted block mb-1">Role on Case</label>
                  <input
                    type="text"
                    value={assignRole}
                    onChange={(e) => setAssignRole(e.target.value)}
                    placeholder="e.g. Lead Investigator, Supporting Officer"
                    className="w-full bg-bg border border-line rounded px-3 py-1.5 text-xs text-ink font-body"
                    required
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowAssignModal(false)}
                    className="text-xs font-mono text-muted px-3 py-1 hover:text-ink transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="bg-amber text-base text-xs font-mono font-semibold px-3 py-1 rounded hover:brightness-110 transition"
                  >
                    Save Assignment
                  </button>
                </div>
              </form>
            )}

            {assignments.length === 0 ? (
              <p className="text-muted text-xs font-mono">No officers assigned to this case yet.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {assignments.map((a) => (
                  <div key={a.id} className="bg-panel2 border border-line rounded p-3 text-xs font-mono flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-ink font-bold">{a.assigned_to_name}</span>
                        <span className="text-[10px] bg-teal/10 border border-teal/40 text-teal px-1.5 py-0.5 rounded uppercase">
                          {a.role_on_case}
                        </span>
                      </div>
                      <p className="text-[10px] text-muted mt-1">
                        Assigned by {a.assigned_by_name} &middot; {new Date(a.assigned_at).toLocaleDateString()}
                      </p>
                    </div>
                    {(isSupervisor || a.assigned_to_user_id === currentUser?.id) && (
                      <button
                        onClick={() => handleRemoveAssignment(a.id)}
                        className="text-muted hover:text-crit text-[11px] font-mono transition"
                        title="Remove Assignment"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 2. Tasks Checklist Sub-section */}
          <div>
            <div className="flex items-center justify-between mb-3 border-b border-line/40 pb-2">
              <h4 className="font-mono text-xs text-teal uppercase font-semibold">
                Investigative Tasks ({tasks.filter((t) => t.status === "done").length}/{tasks.length} Completed)
              </h4>
            </div>

            {/* Add Task Form */}
            {canModify && (
              <form onSubmit={handleCreateTask} className="bg-panel2 border border-line rounded p-3 mb-4 space-y-2">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                    placeholder="New task title (e.g. Verify CCTV footage)..."
                    className="flex-1 bg-bg border border-line rounded px-3 py-1.5 text-xs text-ink outline-none focus:border-teal transition"
                    required
                  />
                  <button
                    type="submit"
                    disabled={!newTaskTitle.trim()}
                    className="bg-teal text-bg font-mono text-xs px-3 py-1.5 rounded font-semibold hover:brightness-110 transition disabled:opacity-40"
                  >
                    + Add Task
                  </button>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newTaskDesc}
                    onChange={(e) => setNewTaskDesc(e.target.value)}
                    placeholder="Optional description..."
                    className="flex-1 bg-bg border border-line rounded px-3 py-1 text-xs text-ink outline-none"
                  />
                  <select
                    value={newTaskAssignee}
                    onChange={(e) => setNewTaskAssignee(e.target.value)}
                    className="bg-bg border border-line rounded px-2 py-1 text-xs text-ink font-body"
                  >
                    <option value="">Unassigned</option>
                    {officers.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.name}
                      </option>
                    ))}
                  </select>
                  <input
                    type="date"
                    value={newTaskDueDate}
                    onChange={(e) => setNewTaskDueDate(e.target.value)}
                    className="bg-bg border border-line rounded px-2 py-1 text-xs text-ink font-body"
                  />
                </div>
              </form>
            )}

            {tasks.length === 0 ? (
              <p className="text-muted text-xs font-mono">No tasks created for this case yet.</p>
            ) : (
              <div className="space-y-2">
                {tasks.map((t) => {
                  const isDone = t.status === "done";
                  const isInProgress = t.status === "in_progress";
                  const isOverdue = t.due_date && !isDone && new Date(t.due_date) < new Date();

                  return (
                    <div
                      key={t.id}
                      className={`border rounded p-3 text-xs transition flex items-start justify-between ${
                        isDone
                          ? "bg-bg/40 border-line/40 opacity-70"
                          : "bg-panel2 border-line hover:border-line/80"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {canModify ? (
                          <input
                            type="checkbox"
                            checked={isDone}
                            onChange={() => handleToggleTaskStatus(t.id, t.status)}
                            className="mt-0.5 accent-teal cursor-pointer"
                          />
                        ) : (
                          <span className="text-muted mt-0.5">{isDone ? "✓" : "○"}</span>
                        )}
                        <div>
                          <p className={`font-body font-semibold ${isDone ? "line-through text-muted" : "text-ink"}`}>
                            {t.title}
                          </p>
                          {t.description && (
                            <p className="text-muted text-[11px] mt-0.5 leading-snug">{t.description}</p>
                          )}
                          <div className="flex items-center gap-3 mt-2 font-mono text-[10px]">
                            <span
                              className={`px-1.5 py-0.5 rounded uppercase font-bold ${
                                isDone
                                  ? "bg-teal/10 text-teal border border-teal/40"
                                  : isInProgress
                                  ? "bg-amber/10 text-amber border border-amber/40"
                                  : "bg-panel text-muted border border-line"
                              }`}
                            >
                              {t.status.replace("_", " ")}
                            </span>
                            {t.assigned_to_name && (
                              <span className="text-muted">👤 {t.assigned_to_name}</span>
                            )}
                            {t.due_date && (
                              <span className={isOverdue ? "text-crit font-bold" : "text-muted"}>
                                📅 {new Date(t.due_date).toLocaleDateString()} {isOverdue ? "(OVERDUE)" : ""}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {canModify && (
                        <button
                          onClick={() => handleDeleteTask(t.id)}
                          className="text-muted hover:text-crit text-[11px] font-mono transition"
                          title="Delete Task"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 3. Threaded Comments Sub-section */}
          <div>
            <div className="flex items-center justify-between mb-3 border-b border-line/40 pb-2">
              <h4 className="font-mono text-xs text-amber uppercase font-semibold">
                Investigative Notes & Comments ({comments.length})
              </h4>
            </div>

            {canModify && (
              <form onSubmit={handlePostComment} className="mb-4">
                <textarea
                  value={newCommentText}
                  onChange={(e) => setNewCommentText(e.target.value)}
                  placeholder="Write an investigative comment or case update..."
                  rows={2}
                  className="w-full bg-panel2 border border-line rounded p-2 text-xs text-ink outline-none focus:border-teal transition font-body resize-none"
                />
                <div className="flex justify-end mt-1.5">
                  <button
                    type="submit"
                    disabled={!newCommentText.trim()}
                    className="bg-amber text-base font-mono text-xs font-semibold px-3 py-1.5 rounded hover:brightness-110 transition disabled:opacity-40"
                  >
                    Post Comment ↵
                  </button>
                </div>
              </form>
            )}

            {comments.length === 0 ? (
              <p className="text-muted text-xs font-mono">No comments posted on this case yet.</p>
            ) : (
              <div className="space-y-3">
                {comments.map((c) => (
                  <div
                    key={c.id}
                    className={`rounded-lg p-3.5 text-xs font-mono border ${
                      c.is_ai_authored
                        ? "bg-panel2 border-teal/60 shadow-lg ring-1 ring-teal/20"
                        : "bg-panel2 border-line"
                    }`}
                  >
                    <div className="flex items-center justify-between border-b border-line/40 pb-1.5 mb-2">
                      <div className="flex items-center gap-2">
                        {c.is_ai_authored ? (
                          <span className="text-teal font-bold uppercase flex items-center gap-1 text-xs">
                            🤖 AI Agent
                          </span>
                        ) : (
                          <span className="text-teal font-bold">{c.author_name}</span>
                        )}
                        {c.author_role && !c.is_ai_authored && (
                          <span className="text-[9px] uppercase px-1.5 py-0.2 rounded bg-panel border border-line text-muted">
                            {c.author_role}
                          </span>
                        )}
                        {c.is_ai_authored && (
                          <span className="text-[9px] uppercase px-2 py-0.5 rounded bg-teal/10 border border-teal/40 text-teal font-bold tracking-wider">
                            Automated Analysis & Investigative Lead
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-muted">
                        <span>{new Date(c.created_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}</span>
                        {!c.is_ai_authored && (isSupervisor || c.author_user_id === currentUser?.id) && (
                          <button
                            onClick={() => handleDeleteComment(c.id)}
                            className="hover:text-crit transition"
                            title="Delete Comment"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </div>
                    <p className="text-ink text-sm font-body leading-relaxed whitespace-pre-wrap">{c.content}</p>
                  </div>
                ))}
              </div>

            )}
          </div>
        </div>
      </Section>

      <div className="grid grid-cols-4 gap-3 mb-6">
        <Field label="District" value={caseData.district} />
        <Field label="Station" value={caseData.station_name} />
        <Field label="Crime Type" value={caseData.crime_type} />
        <Field label="Incident Date" value={new Date(caseData.incident_date).toLocaleDateString()} />
      </div>

      <div className="flex gap-3 mb-6">
        <span className="text-xs font-mono uppercase px-3 py-1.5 rounded bg-panel2 text-ink border border-line">
          {caseData.status.replace("_", " ")}
        </span>
        <span
          className="text-xs font-mono uppercase px-3 py-1.5 rounded"
          style={{
            color: SEVERITY_COLOR[caseData.severity],
            border: `1px solid ${SEVERITY_COLOR[caseData.severity]}55`,
            background: `${SEVERITY_COLOR[caseData.severity]}11`,
          }}
        >
          {caseData.severity} severity
        </span>
      </div>

      {/* Structured KSP FIR Record Section */}
      {fir && (
        <Section title="KSP FIR Record Metadata">
          <div className="bg-panel border border-line rounded-md p-4 grid grid-cols-3 gap-4 text-xs font-mono">
            <div>
              <p className="text-muted uppercase">Structured Crime No</p>
              <p className="text-teal font-semibold mt-0.5">{fir.crime_no}</p>
            </div>
            <div>
              <p className="text-muted uppercase">Case Category</p>
              <p className="text-ink mt-0.5">{fir.category_name || "FIR"}</p>
            </div>
            <div>
              <p className="text-muted uppercase">Gravity</p>
              <p className="text-amber mt-0.5">{fir.gravity_name || "N/A"}</p>
            </div>
            <div>
              <p className="text-muted uppercase">Crime Head / Sub-Head</p>
              <p className="text-ink mt-0.5">{fir.crime_head_name || "N/A"} → {fir.crime_sub_head_name || "N/A"}</p>
            </div>
            <div>
              <p className="text-muted uppercase">Jurisdiction Police Station</p>
              <p className="text-ink mt-0.5">{fir.police_station_name || caseData.station_name}</p>
            </div>
            <div>
              <p className="text-muted uppercase">Cognizant Court</p>
              <p className="text-ink mt-0.5">{fir.court_name || "N/A"}</p>
            </div>
          </div>
        </Section>
      )}

      {/* Complainant Details Section */}
      {comp && (
        <Section title="Complainant Record">
          <div className="bg-panel border border-line rounded-md p-4 space-y-3 text-xs font-mono">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-muted uppercase">Complainant Name</p>
                <p className="text-ink font-medium mt-0.5">{comp.name}</p>
              </div>
              <div>
                <p className="text-muted uppercase">Age & Gender</p>
                <p className="text-ink mt-0.5">{comp.age ? `${comp.age} yrs` : "N/A"} &middot; {comp.gender || "Unspecified"}</p>
              </div>
              <div>
                <p className="text-muted uppercase">Occupation</p>
                <p className="text-ink mt-0.5">{comp.occupation_name || "N/A"}</p>
              </div>
            </div>

            {/* Sensitive Admin-Only Compliance Card */}
            <div className="border border-line/60 rounded bg-panel2 p-3 mt-3">
              <div className="flex items-center justify-between">
                <span className="text-muted font-mono text-[11px] uppercase flex items-center gap-1.5">
                  🔒 Statutory Sensitive Fields (Religion / Caste)
                </span>
                {isAdmin ? (
                  <button
                    onClick={() => setShowSensitive(!showSensitive)}
                    className="text-teal hover:underline text-[11px] font-mono"
                  >
                    {showSensitive ? "Hide Admin Data" : "View Sensitive Admin Data"}
                  </button>
                ) : (
                  <span className="text-muted/60 text-[10px] font-mono italic">
                    Restricted for statutory compliance (Admin Only)
                  </span>
                )}
              </div>

              {isAdmin && showSensitive && (
                <div className="mt-3 pt-2 border-t border-line grid grid-cols-2 gap-4 text-xs font-mono">
                  <div>
                    <p className="text-muted uppercase">Religion</p>
                    <p className="text-amber mt-0.5">{comp.religion_name || "Unspecified"}</p>
                  </div>
                  <div>
                    <p className="text-muted uppercase">Caste Category</p>
                    <p className="text-amber mt-0.5">{comp.caste_name || "Unspecified"}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Section>
      )}

      {/* Applied Acts & Sections */}
      {caseData.act_sections && caseData.act_sections.length > 0 && (
        <Section title="Applied Acts & Sections">
          <div className="space-y-2">
            {caseData.act_sections.map((a) => (
              <div key={a.id} className="border border-line rounded px-4 py-2.5 bg-panel2 flex items-center justify-between text-xs font-mono">
                <div>
                  <span className="text-amber font-semibold">{a.act_name || "Act"} Section {a.section_number}</span>
                  {a.section_description && <p className="text-muted text-[11px] mt-0.5">{a.section_description}</p>}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Chargesheet Status */}
      {cs && (
        <Section title="Chargesheet Status">
          <div className="bg-panel border border-line rounded-md p-4 grid grid-cols-3 gap-4 text-xs font-mono">
            <div>
              <p className="text-muted uppercase">Filing Date</p>
              <p className="text-ink mt-0.5">{new Date(cs.chargesheet_date).toLocaleDateString()}</p>
            </div>
            <div>
              <p className="text-muted uppercase">Chargesheet Type</p>
              <p className="text-teal font-semibold mt-0.5">Type {cs.cs_type} ({cs.cs_type === "A" ? "Chargesheet" : cs.cs_type === "B" ? "False Case" : "Undetected"})</p>
            </div>
            <div>
              <p className="text-muted uppercase">Filing Officer</p>
              <p className="text-ink mt-0.5">{cs.filing_officer_name || "N/A"}</p>
            </div>
          </div>
        </Section>
      )}

      {/* Investigation Timeline */}
      <Section title="Investigation Timeline">
        {timeline.length === 0 ? (
          <div className="border border-line rounded px-4 py-4 bg-panel2 text-[12px] font-mono text-muted">
            No chronological timeline events recorded yet.
          </div>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[2px] before:bg-line">
            {timeline.map((evt, idx) => (
              <div key={idx} className="relative group">
                {/* Node marker */}
                <div className="absolute -left-[23px] top-1 w-3.5 h-3.5 rounded-full bg-amber border-2 border-bg ring-4 ring-amber/10 group-hover:scale-110 transition" />
                <div className="bg-panel border border-line rounded px-4 py-3 text-xs font-mono">
                  <div className="flex items-center justify-between text-muted text-[11px] mb-1">
                    <span>{new Date(evt.date).toLocaleString()}</span>
                    {evt.actor && <span className="text-teal font-medium">{evt.actor}</span>}
                  </div>
                  <p className="text-ink font-semibold text-sm">{evt.label}</p>
                  {evt.reference_id && (
                    <p className="text-muted text-[10px] uppercase mt-1">Ref ID: {evt.reference_id}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Summary">
        <p className="text-ink text-sm leading-relaxed">{caseData.summary || "No summary recorded."}</p>
      </Section>

      <Section title={`Persons of Interest (${caseData.persons.length})`}>
        {caseData.persons.length === 0 ? (
          <p className="text-muted text-sm">No persons linked to this case yet.</p>
        ) : (
          <div className="space-y-2">
            {caseData.persons.map((p) => (
              <div key={p.id} className="border border-line rounded px-4 py-3 bg-panel2 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-ink text-sm font-medium">{p.name}</p>
                    {p.role_in_case === "suspect" && (
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-crit/10 border border-crit/40 text-crit">
                        Suspect / Accused {p.person_sort_id ? `(${p.person_sort_id})` : ""}
                      </span>
                    )}
                  </div>
                  <p className="text-muted text-xs font-mono capitalize mt-0.5">{p.role_in_case}</p>
                </div>
                <div className="text-right">
                  <p className="text-muted text-xs font-mono">{p.phone_number}</p>
                  <Link to="/offenders" className="text-[11px] font-mono text-teal hover:underline block mt-0.5">
                    View Behavioral Profile →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Financial Transaction Trail Section */}
      <Section title="Financial Crime & Transaction Trail">
        {!financialTrail || financialTrail.edges.length === 0 ? (
          <div className="border border-line rounded px-4 py-6 bg-panel2 text-center">
            <p className="text-muted text-xs font-mono">No linked financial transaction trails for this case.</p>
          </div>
        ) : (
          <div className="bg-panel border border-line rounded-md p-4 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div>
                <p className="text-muted text-xs font-mono uppercase">Total Transferred Volume</p>
                <p className="font-display text-2xl text-teal">₹{financialTrail.total_amount.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted text-xs font-mono uppercase text-right">Flagged Transfers</p>
                <p className="font-display text-2xl text-crit text-right">{financialTrail.flagged_count}</p>
              </div>
            </div>

            <div className="space-y-2">
              {financialTrail.edges.map((tx) => {
                const sourceNode = financialTrail.nodes.find((n) => n.id === tx.source);
                const targetNode = financialTrail.nodes.find((n) => n.id === tx.target);
                return (
                  <div
                    key={tx.id}
                    className={`border rounded p-3 text-xs font-mono ${
                      tx.flagged_reason
                        ? "bg-crit/10 border-crit/40"
                        : "bg-panel2 border-line"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-ink font-semibold">
                        {sourceNode ? `${sourceNode.bank_name} (${sourceNode.account_number_masked})` : "Account"}
                        {" ➔ "}
                        {targetNode ? `${targetNode.bank_name} (${targetNode.account_number_masked})` : "Account"}
                      </span>
                      <span className="text-amber font-display text-sm">₹{tx.amount.toLocaleString()}</span>
                    </div>
                    {tx.flagged_reason && (
                      <p className="text-crit font-mono text-[11px] mt-1">
                        🚩 Flagged: {tx.flagged_reason}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Section>

      <Section title={`Evidence Log (${caseData.evidence.length})`}>
        {caseData.evidence.length === 0 ? (
          <p className="text-muted text-sm">No evidence recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {caseData.evidence.map((e) => (
              <div key={e.id} className="border border-line rounded px-4 py-3 bg-panel2 flex justify-between">
                <p className="text-ink text-sm">{e.description}</p>
                <p className="text-muted text-xs font-mono truncate max-w-[200px]">{e.evidence_hash}</p>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Similar Cases">
        {similarCases.length === 0 ? (
          <p className="text-muted text-sm">No sufficiently similar cases found yet.</p>
        ) : (
          <div className="space-y-2">
            {similarCases.map((sc) => (
              <Link
                key={sc.id}
                to={`/cases/${sc.id}`}
                className="flex items-center justify-between border border-line rounded px-4 py-3 bg-panel2 hover:border-teal transition"
              >
                <div>
                  <p className="font-mono text-xs text-muted">{sc.case_id}</p>
                  <p className="text-ink text-sm">{sc.title}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-muted text-xs">{sc.district}</span>
                  <span className="text-teal text-xs font-mono">{(sc.similarity * 100).toFixed(0)}% match</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Section>

      {/* ── UPDATE INVESTIGATION LABEL MODAL ── */}
      {showLabelModal && (
        <div className="fixed inset-0 bg-base/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-panel border border-line rounded-lg max-w-lg w-full p-6 shadow-2xl space-y-4 font-body relative">
            <div className="flex justify-between items-center border-b border-line pb-3">
              <h3 className="font-display text-lg text-ink">Update Security Investigation Label</h3>
              <button
                onClick={() => setShowLabelModal(false)}
                className="text-muted hover:text-ink text-sm font-mono"
              >
                ✕
              </button>
            </div>

            {investigationError && (
              <div className="bg-crit/10 border border-crit/40 text-crit text-xs p-3 rounded font-mono">
                {investigationError}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-muted uppercase mb-1">Select Investigation Label *</label>
                <div className="grid grid-cols-3 gap-2">
                  {["Suspected", "Verified", "Needs Review"].map((lbl) => (
                    <button
                      key={lbl}
                      type="button"
                      onClick={() => setNewLabel(lbl)}
                      className={`p-3 rounded border text-xs font-mono font-semibold transition text-center ${
                        newLabel === lbl
                          ? "bg-amber/20 border-amber text-amber shadow-lg"
                          : "bg-panel2 border-line text-muted hover:border-teal"
                      }`}
                    >
                      {lbl === "Suspected" && "⚠️ "}
                      {lbl === "Verified" && "✓ "}
                      {lbl === "Needs Review" && "🔍 "}
                      {lbl}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-mono text-muted uppercase">Investigator Reasoning Note *</label>
                  <span className={`text-[11px] font-mono ${newNote.trim().length < 3 ? "text-crit" : "text-teal"}`}>
                    {newNote.trim().length}/1000 chars
                  </span>
                </div>
                <textarea
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  placeholder="Provide detailed investigator rationale, forensic evidence findings, or verification justification..."
                  rows={4}
                  className="w-full bg-panel2 border border-line rounded p-3 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
                />
              </div>

              {/* Mandatory Confirmation Step */}
              <div className="bg-amber/10 border border-amber/30 rounded p-3 text-xs text-amber font-mono">
                ⚠️ <strong>Confirmation Required:</strong> Submitting will record an immutable audit event in Activity History and update the official Security Case review status.
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-line">
              <button
                type="button"
                onClick={() => setShowLabelModal(false)}
                className="px-4 py-2 rounded text-xs font-mono text-muted hover:text-ink transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={investigationSubmitting || newNote.trim().length < 3}
                onClick={handleSaveInvestigationLabel}
                className="bg-amber hover:bg-amber/90 text-base font-semibold text-xs px-5 py-2 rounded shadow transition disabled:opacity-50"
              >
                {investigationSubmitting ? "Saving..." : "Confirm & Save Update"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

