import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMyTasks, fetchMyAssignedCases, updateCaseTask, getCurrentUser } from "../lib/api.js";

const SEVERITY_COLOR = {
  low: "#3FD6C1",
  medium: "#F0A202",
  high: "#E8833A",
  critical: "#E23D5B",
};

export default function MyWork() {
  const currentUser = getCurrentUser();
  const [assignedCases, setAssignedCases] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  function loadData() {
    setLoading(true);
    Promise.all([fetchMyAssignedCases(), fetchMyTasks()])
      .then(([casesData, tasksData]) => {
        setAssignedCases(casesData);
        setTasks(tasksData);
      })
      .catch(() => setError("Failed to load your assigned work items."))
      .finally(() => setLoading(false));
  }

  async function handleMarkDone(taskId, caseId) {
    try {
      await updateCaseTask(caseId, taskId, { status: "done" });
      loadData();
    } catch {
      setError("Failed to update task status.");
    }
  }

  if (loading) {
    return <div className="p-8 text-muted font-mono text-sm">Loading your workspace...</div>;
  }

  return (
    <div className="p-8 max-w-6xl space-y-8">
      {/* Top Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <p className="font-mono text-teal text-xs tracking-[0.2em]">PERSONAL WORKSPACE</p>
          <span className="font-mono text-[10px] bg-amber/10 border border-amber/40 text-amber px-2 py-0.5 rounded uppercase">
            {currentUser?.role || "Officer"}
          </span>
        </div>
        <h2 className="font-display text-3xl text-ink">My Work & Assigned Cases</h2>
        <p className="text-muted text-xs font-mono mt-1">
          Track active case assignments, pending tasks, and due dates assigned to {currentUser?.name || "you"}.
        </p>
      </div>

      {error && (
        <div className="border border-crit/40 bg-crit/10 text-crit text-xs font-mono p-3 rounded">
          {error}
        </div>
      )}

      {/* ── SECTION 1: MY ASSIGNED CASES ─────────────────────────────────── */}
      <div>
        <h3 className="font-display text-xl text-ink mb-4 flex items-center justify-between">
          <span>📁 Active Case Assignments ({assignedCases.length})</span>
        </h3>

        {assignedCases.length === 0 ? (
          <div className="bg-panel border border-line rounded-lg p-6 text-center text-muted font-mono text-xs">
            You are not currently assigned to any active cases.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {assignedCases.map((c) => (
              <div key={c.assignment_id} className="bg-panel border border-line rounded-lg p-4 font-mono text-xs flex flex-col justify-between space-y-3 hover:border-line/80 transition">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-teal font-bold">{c.case_code}</span>
                    <span
                      className="px-2 py-0.5 rounded text-[10px] uppercase font-bold text-bg"
                      style={{ backgroundColor: SEVERITY_COLOR[c.severity] || "#F0A202" }}
                    >
                      {c.severity}
                    </span>
                  </div>
                  <h4 className="font-body text-ink text-sm font-semibold leading-snug line-clamp-2">
                    {c.title}
                  </h4>
                  <div className="flex items-center gap-2 text-[10px] text-muted mt-2">
                    <span>📍 {c.district}</span>
                    <span>&middot;</span>
                    <span className="uppercase">{c.crime_type}</span>
                  </div>
                </div>

                <div className="border-t border-line/40 pt-3 flex items-center justify-between">
                  <span className="bg-teal/10 border border-teal/40 text-teal text-[10px] px-2 py-0.5 rounded font-bold uppercase">
                    {c.role_on_case}
                  </span>
                  <Link
                    to={`/cases/${c.case_id}`}
                    className="text-amber hover:underline text-xs font-semibold"
                  >
                    Open Case File ➔
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── SECTION 2: MY OPEN TASKS ACROSS ALL CASES ─────────────────────── */}
      <div>
        <h3 className="font-display text-xl text-ink mb-4 flex items-center justify-between">
          <span>📋 My Open Tasks ({tasks.length})</span>
        </h3>

        {tasks.length === 0 ? (
          <div className="bg-panel border border-line rounded-lg p-6 text-center text-muted font-mono text-xs">
            🎉 All caught up! No pending tasks assigned to you.
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((t) => {
              const isOverdue = t.due_date && new Date(t.due_date) < new Date();

              return (
                <div
                  key={t.id}
                  className="bg-panel border border-line rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-teal/50 transition"
                >
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center gap-2 font-mono text-xs">
                      {t.case_code && (
                        <Link
                          to={`/cases/${t.case_id}`}
                          className="text-teal font-bold hover:underline"
                        >
                          {t.case_code}
                        </Link>
                      )}
                      <span
                        className="px-1.5 py-0.2 rounded text-[9px] uppercase font-bold text-bg"
                        style={{ backgroundColor: SEVERITY_COLOR[t.case_severity] || "#F0A202" }}
                      >
                        {t.case_severity || "medium"}
                      </span>
                      {t.due_date && (
                        <span className={`text-[10px] ml-2 ${isOverdue ? "text-crit font-bold" : "text-muted"}`}>
                          📅 Due: {new Date(t.due_date).toLocaleDateString()} {isOverdue ? "(OVERDUE)" : ""}
                        </span>
                      )}
                    </div>

                    <h4 className="font-body text-ink text-sm font-semibold">{t.title}</h4>
                    {t.description && (
                      <p className="text-muted text-xs font-body leading-relaxed">{t.description}</p>
                    )}
                    <p className="text-muted text-[10px] font-mono">
                      Created by {t.created_by_name} &middot; {new Date(t.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleMarkDone(t.id, t.case_id)}
                      className="bg-teal text-bg font-mono text-xs font-bold px-3 py-1.5 rounded hover:brightness-110 transition whitespace-nowrap"
                    >
                      ✓ Mark Complete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
