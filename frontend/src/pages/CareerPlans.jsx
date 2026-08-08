import { useEffect, useState } from "react";
import { fetchCareerPlans, createCareerPlan, getCurrentUser } from "../lib/api.js";

const DIFFICULTY_COLORS = {
  Beginner: "bg-teal/20 text-teal border-teal/40",
  Intermediate: "bg-amber/20 text-amber border-amber/40",
  Advanced: "bg-orange-500/20 text-orange-400 border-orange-500/40",
  Expert: "bg-crit/20 text-crit border-crit/40",
};

export default function CareerPlans() {
  const [q, setQ] = useState("");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [goal, setGoal] = useState("");
  const [deadlineRange, setDeadlineRange] = useState("");
  const [sortBy, setSortBy] = useState("newest");
  const [page, setPage] = useState(1);

  const [data, setData] = useState({
    total: 0,
    page: 1,
    page_size: 12,
    total_pages: 1,
    results: [],
    available_topics: [],
    available_goals: [],
    available_difficulties: ["Beginner", "Intermediate", "Advanced", "Expert"],
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newTopic, setNewTopic] = useState("Cyber Forensics");
  const [newDifficulty, setNewDifficulty] = useState("Intermediate");
  const [newGoal, setNewGoal] = useState("");
  const [newDeadline, setNewDeadline] = useState("");
  const [newTags, setNewTags] = useState("");
  const [newMilestones, setNewMilestones] = useState("");
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState("");

  const currentUser = getCurrentUser();

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const params = { page, page_size: 12, sort_by: sortBy };
      if (q.trim()) params.q = q.trim();
      if (topic) params.topic = topic;
      if (difficulty) params.difficulty = difficulty;
      if (goal) params.goal = goal;

      if (deadlineRange) {
        const now = new Date();
        if (deadlineRange === "30_days") {
          const future = new Date();
          future.setDate(now.getDate() + 30);
          params.deadline_before = future.toISOString();
        } else if (deadlineRange === "90_days") {
          const future = new Date();
          future.setDate(now.getDate() + 90);
          params.deadline_before = future.toISOString();
        }
      }

      const res = await fetchCareerPlans(params);
      setData(res);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load career plans. Is the backend server online?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, topic, difficulty, goal, deadlineRange, sortBy, page]);

  function handleResetFilters() {
    setQ("");
    setTopic("");
    setDifficulty("");
    setGoal("");
    setDeadlineRange("");
    setSortBy("newest");
    setPage(1);
  }

  const activeFilterCount =
    (q ? 1 : 0) + (topic ? 1 : 0) + (difficulty ? 1 : 0) + (goal ? 1 : 0) + (deadlineRange ? 1 : 0);

  async function handleCreatePlan(e) {
    e.preventDefault();
    if (!newTitle.trim() || !newTopic.trim() || !newGoal.trim()) {
      setCreateError("Title, Topic, and Target Goal are required.");
      return;
    }
    setCreateSubmitting(true);
    setCreateError("");
    try {
      await createCareerPlan({
        title: newTitle.trim(),
        description: newDesc.trim() || null,
        topic: newTopic.trim(),
        difficulty_level: newDifficulty,
        target_goal: newGoal.trim(),
        deadline: newDeadline ? new Date(newDeadline).toISOString() : null,
        tags: newTags.trim() || null,
        milestones: newMilestones.trim() || null,
      });
      setShowCreateModal(false);
      setNewTitle("");
      setNewDesc("");
      setNewGoal("");
      setNewDeadline("");
      setNewTags("");
      setNewMilestones("");
      loadData();
    } catch (err) {
      setCreateError(err.response?.data?.detail || "Failed to create career plan.");
    } finally {
      setCreateSubmitting(false);
    }
  }

  return (
    <div className="p-8 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">LEARNING & DEVELOPMENT</p>
          <h2 className="font-display text-3xl text-ink">Career Plans & Learning Search</h2>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-amber hover:bg-amber/90 font-mono font-bold text-xs px-4 py-2.5 rounded text-base shadow transition flex items-center gap-2 self-start md:self-auto"
        >
          <span>🎯</span> Create Career Plan
        </button>
      </div>

      {/* Prominent Search & Filter Control Bar */}
      <div className="bg-panel border border-line rounded-lg p-5 space-y-4 shadow-sm">
        {/* Search Input Bar */}
        <div className="relative">
          <span className="absolute left-3.5 top-3 text-muted text-sm font-mono">🔍</span>
          <input
            type="text"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            placeholder="Search career plans by keyword, title, description, milestones, notes, or tags..."
            className="w-full bg-panel2 border border-line rounded-lg pl-10 pr-10 py-2.5 text-ink text-sm font-body focus:outline-none focus:ring-1 focus:ring-teal transition"
          />
          {q && (
            <button
              onClick={() => setQ("")}
              className="absolute right-3 top-2.5 text-muted hover:text-ink text-sm font-mono"
            >
              ✕
            </button>
          )}
        </div>

        {/* Filter Controls Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          {/* Topic Filter */}
          <div>
            <label className="block text-[10px] font-mono text-muted uppercase mb-1">Topic</label>
            <select
              value={topic}
              onChange={(e) => { setTopic(e.target.value); setPage(1); }}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="">All Topics</option>
              {data.available_topics.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {/* Difficulty Filter */}
          <div>
            <label className="block text-[10px] font-mono text-muted uppercase mb-1">Difficulty</label>
            <select
              value={difficulty}
              onChange={(e) => { setDifficulty(e.target.value); setPage(1); }}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="">All Difficulties</option>
              {data.available_difficulties.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Target Goal Filter */}
          <div>
            <label className="block text-[10px] font-mono text-muted uppercase mb-1">Target Goal</label>
            <select
              value={goal}
              onChange={(e) => { setGoal(e.target.value); setPage(1); }}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="">All Target Goals</option>
              {data.available_goals.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>

          {/* Deadline Filter */}
          <div>
            <label className="block text-[10px] font-mono text-muted uppercase mb-1">Deadline Horizon</label>
            <select
              value={deadlineRange}
              onChange={(e) => { setDeadlineRange(e.target.value); setPage(1); }}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="">Any Time</option>
              <option value="30_days">Next 30 Days</option>
              <option value="90_days">Next 90 Days</option>
            </select>
          </div>

          {/* Sort By */}
          <div>
            <label className="block text-[10px] font-mono text-muted uppercase mb-1">Sort By</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="deadline">Deadline Soonest</option>
              <option value="alphabetical">Alphabetical (A-Z)</option>
            </select>
          </div>
        </div>

        {/* Active Filter Chips Bar & Reset Button */}
        {activeFilterCount > 0 && (
          <div className="pt-3 border-t border-line/50 flex items-center justify-between flex-wrap gap-2 text-xs font-mono">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-muted">Active Filters ({activeFilterCount}):</span>

              {q && (
                <span className="bg-panel2 border border-teal/40 text-teal px-2.5 py-1 rounded flex items-center gap-1.5">
                  Keyword: "{q}"
                  <button onClick={() => setQ("")} className="hover:text-white">✕</button>
                </span>
              )}
              {topic && (
                <span className="bg-panel2 border border-teal/40 text-teal px-2.5 py-1 rounded flex items-center gap-1.5">
                  Topic: {topic}
                  <button onClick={() => setTopic("")} className="hover:text-white">✕</button>
                </span>
              )}
              {difficulty && (
                <span className="bg-panel2 border border-teal/40 text-teal px-2.5 py-1 rounded flex items-center gap-1.5">
                  Difficulty: {difficulty}
                  <button onClick={() => setDifficulty("")} className="hover:text-white">✕</button>
                </span>
              )}
              {goal && (
                <span className="bg-panel2 border border-teal/40 text-teal px-2.5 py-1 rounded flex items-center gap-1.5">
                  Goal: {goal}
                  <button onClick={() => setGoal("")} className="hover:text-white">✕</button>
                </span>
              )}
              {deadlineRange && (
                <span className="bg-panel2 border border-teal/40 text-teal px-2.5 py-1 rounded flex items-center gap-1.5">
                  Deadline: {deadlineRange.replace("_", " ")}
                  <button onClick={() => setDeadlineRange("")} className="hover:text-white">✕</button>
                </span>
              )}
            </div>

            <button
              onClick={handleResetFilters}
              className="bg-crit/10 hover:bg-crit/20 border border-crit/40 text-crit px-3 py-1 rounded font-semibold transition flex items-center gap-1"
            >
              <span>🔄</span> Reset Filters
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-crit/10 border border-crit/40 text-crit text-xs font-mono p-4 rounded">
          {error}
        </div>
      )}

      {/* Career Plan Cards Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-panel border border-line rounded-lg p-5 animate-pulse space-y-3">
              <div className="h-4 bg-panel2 rounded w-3/4" />
              <div className="h-3 bg-panel2 rounded w-1/2" />
              <div className="h-16 bg-panel2 rounded w-full" />
            </div>
          ))}
        </div>
      ) : data.results.length === 0 ? (
        /* Empty State Illustration */
        <div className="bg-panel border border-line rounded-lg p-12 text-center space-y-4">
          <div className="text-4xl">📚</div>
          <h3 className="font-display text-xl text-ink">No Career Plans Found</h3>
          <p className="text-muted text-sm max-w-md mx-auto">
            No learning plans matched your current keyword search and topic/difficulty filter criteria.
          </p>
          {activeFilterCount > 0 && (
            <button
              onClick={handleResetFilters}
              className="bg-amber hover:bg-amber/90 font-mono font-bold text-xs px-5 py-2.5 rounded text-base transition inline-flex items-center gap-2"
            >
              <span>🔄</span> Clear Search & Reset Filters
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {data.results.map((plan) => {
            const diffClass = DIFFICULTY_COLORS[plan.difficulty_level] || "bg-slate-700/40 text-slate-400 border-slate-600";
            return (
              <div
                key={plan.id}
                className="bg-panel border border-line hover:border-teal rounded-lg p-5 flex flex-col justify-between transition shadow-sm space-y-4"
              >
                <div className="space-y-3">
                  {/* Topic & Difficulty Badges */}
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="bg-teal/10 text-teal border border-teal/30 px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold">
                      {plan.topic}
                    </span>
                    <span className={`border px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold ${diffClass}`}>
                      {plan.difficulty_level}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="font-display text-lg text-ink font-semibold leading-snug">
                    {plan.title}
                  </h3>

                  {/* Target Goal */}
                  <div className="bg-panel2 border border-line/60 rounded p-2.5">
                    <p className="text-muted text-[10px] font-mono uppercase">Target Qualification / Goal</p>
                    <p className="text-ink text-xs font-mono font-semibold mt-0.5">🎯 {plan.target_goal}</p>
                  </div>

                  {/* Description */}
                  {plan.description && (
                    <p className="text-muted text-xs font-body line-clamp-3 leading-relaxed">
                      {plan.description}
                    </p>
                  )}

                  {/* Milestones Preview */}
                  {plan.milestones && (
                    <div className="text-[11px] font-mono text-slate-300 bg-panel2/50 border border-line/40 rounded p-2">
                      <p className="text-muted text-[9px] uppercase font-semibold mb-1">Key Milestones</p>
                      <pre className="font-mono whitespace-pre-wrap text-[11px] text-slate-300 leading-tight">
                        {plan.milestones.split("\n").slice(0, 3).join("\n")}
                      </pre>
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-line/60 space-y-2 text-xs font-mono">
                  {/* Deadline & Status */}
                  <div className="flex justify-between items-center text-muted text-[11px]">
                    <span>
                      📅 Deadline: {plan.deadline ? new Date(plan.deadline).toLocaleDateString() : "Open"}
                    </span>
                    <span className="capitalize text-teal font-semibold">
                      {plan.status}
                    </span>
                  </div>

                  {/* Tags */}
                  {plan.tags && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {plan.tags.split(",").slice(0, 4).map((tag, idx) => (
                        <span key={idx} className="bg-panel2 text-muted px-2 py-0.5 rounded text-[10px]">
                          #{tag.trim()}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Owner */}
                  {plan.owner_name && (
                    <p className="text-[10px] text-muted font-mono">Owner: {plan.owner_name}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {data.total_pages > 1 && (
        <div className="flex items-center justify-between border-t border-line pt-4 font-mono text-xs">
          <p className="text-muted">
            Showing Page {data.page} of {data.total_pages} ({data.total} total plans)
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="bg-panel border border-line hover:border-teal disabled:opacity-50 px-3 py-1.5 rounded transition"
            >
              ← Previous
            </button>
            <span className="px-3 py-1.5 text-teal font-bold bg-panel2 rounded">
              {page}
            </span>
            <button
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              className="bg-panel border border-line hover:border-teal disabled:opacity-50 px-3 py-1.5 rounded transition"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Create Career Plan Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-base/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleCreatePlan} className="bg-panel border border-line rounded-lg max-w-xl w-full p-6 shadow-2xl space-y-4 font-body relative max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-line pb-3">
              <h3 className="font-display text-lg text-ink">Create New Career Plan</h3>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="text-muted hover:text-ink font-mono text-sm"
              >
                ✕
              </button>
            </div>

            {createError && (
              <div className="bg-crit/10 border border-crit/40 text-crit text-xs p-3 rounded font-mono">
                {createError}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-mono text-muted uppercase mb-1">Plan Title *</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Advanced Cyber Crime Incident Response & Malware Analysis"
                  className="w-full bg-panel2 border border-line rounded p-2.5 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-muted uppercase mb-1">Topic *</label>
                  <input
                    type="text"
                    required
                    value={newTopic}
                    onChange={(e) => setNewTopic(e.target.value)}
                    placeholder="e.g. Cyber Forensics, Financial Intelligence..."
                    className="w-full bg-panel2 border border-line rounded p-2.5 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-muted uppercase mb-1">Difficulty Level *</label>
                  <select
                    value={newDifficulty}
                    onChange={(e) => setNewDifficulty(e.target.value)}
                    className="w-full bg-panel2 border border-line rounded p-2.5 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal font-mono"
                  >
                    <option value="Beginner">Beginner</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Advanced">Advanced</option>
                    <option value="Expert">Expert</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-muted uppercase mb-1">Target Goal / Qualification *</label>
                <input
                  type="text"
                  required
                  value={newGoal}
                  onChange={(e) => setNewGoal(e.target.value)}
                  placeholder="e.g. Certified Digital Forensics Examiner (CDFE)"
                  className="w-full bg-panel2 border border-line rounded p-2.5 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-muted uppercase mb-1">Description</label>
                <textarea
                  rows={3}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Detailed learning objectives and target outcomes..."
                  className="w-full bg-panel2 border border-line rounded p-2.5 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-muted uppercase mb-1">Target Deadline</label>
                  <input
                    type="date"
                    value={newDeadline}
                    onChange={(e) => setNewDeadline(e.target.value)}
                    className="w-full bg-panel2 border border-line rounded p-2.5 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-muted uppercase mb-1">Tags (Comma-separated)</label>
                  <input
                    type="text"
                    value={newTags}
                    onChange={(e) => setNewTags(e.target.value)}
                    placeholder="forensics, python, aml"
                    className="w-full bg-panel2 border border-line rounded p-2.5 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-muted uppercase mb-1">Milestones (One per line)</label>
                <textarea
                  rows={3}
                  value={newMilestones}
                  onChange={(e) => setNewMilestones(e.target.value)}
                  placeholder="1. Disk Imaging&#10;2. Memory Volatility&#10;3. Final Capstone Report"
                  className="w-full bg-panel2 border border-line rounded p-2.5 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal font-mono"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-line">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-xs font-mono text-muted hover:text-ink transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createSubmitting}
                className="bg-amber hover:bg-amber/90 font-mono font-bold text-xs px-5 py-2.5 rounded text-base shadow transition disabled:opacity-50"
              >
                {createSubmitting ? "Creating..." : "Save Career Plan"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
