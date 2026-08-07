import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchOffenders, fetchOffenderProfile } from "../lib/api.js";

const RISK_BADGE = {
  high: "text-crit border-crit/40 bg-crit/10",
  medium: "text-amber border-amber/40 bg-amber/10",
  low: "text-teal border-teal/40 bg-teal/10",
};

function RiskBadge({ category, score }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold uppercase border ${
        RISK_BADGE[category] || "text-muted border-line"
      }`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
      {category} ({score})
    </span>
  );
}

function OffenderDrawer({ personId, onClose }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOffenderProfile(personId)
      .then(setProfile)
      .finally(() => setLoading(false));
  }, [personId]);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-end z-50">
      <div className="bg-panel border-l border-line w-full max-w-xl h-full p-6 overflow-y-auto shadow-2xl flex flex-col">
        <div className="flex items-center justify-between border-b border-line pb-4 mb-6">
          <div>
            <p className="font-mono text-teal text-[10px] tracking-[0.25em]">BEHAVIORAL PROFILE</p>
            <h3 className="font-display text-2xl text-ink">{profile?.name || "Loading..."}</h3>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-ink font-mono text-xl transition"
          >
            ✕
          </button>
        </div>

        {loading && (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-muted font-mono text-sm">Calculating behavioral risk profile...</p>
          </div>
        )}

        {profile && (
          <div className="space-y-6 flex-1">
            {/* Risk Summary Header */}
            <div className="bg-panel2 border border-line rounded-lg p-5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-muted text-xs font-mono uppercase">Composite Risk Score</p>
                  <p className="font-display text-4xl text-ink mt-0.5">{profile.risk_score} <span className="text-xs font-mono text-muted">/ 100</span></p>
                </div>
                <RiskBadge category={profile.risk_category} score={profile.risk_score} />
              </div>

              {/* Score Breakdown Bar */}
              <div className="mt-4 pt-3 border-t border-line/60">
                <p className="text-muted text-xs font-mono uppercase mb-2">Score Components</p>
                <div className="space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-muted">Case Volume (10 pts/case):</span>
                    <span className="text-ink">{profile.risk_breakdown.volume_pts} pts</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Max Case Severity:</span>
                    <span className="text-ink">{profile.risk_breakdown.severity_pts} pts</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Activity Recency:</span>
                    <span className="text-ink">{profile.risk_breakdown.recency_pts} pts</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">MO Pattern Repetition:</span>
                    <span className="text-ink">{profile.risk_breakdown.mo_repetition_pts} pts</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Network Centrality:</span>
                    <span className="text-ink">{profile.risk_breakdown.network_centrality_pts} pts</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Non-bias Guarantee Notice */}
            <div className="bg-teal/5 border border-teal/30 rounded p-3 text-xs font-mono text-teal leading-relaxed">
              <strong>Fairness & Non-Bias Guarantee:</strong> Risk scores are strictly derived from objective behavioral and case signals. Demographic attributes are excluded.
            </div>

            {/* MO Tags */}
            <div>
              <h4 className="text-ink font-display text-base mb-2">Identified Modus Operandi (MO) Tags</h4>
              <div className="flex flex-wrap gap-1.5">
                {profile.mo_tags.length === 0 && (
                  <p className="text-muted text-xs font-mono">No specific MO tags recorded.</p>
                )}
                {profile.mo_tags.map((tag, i) => (
                  <span key={i} className="px-2.5 py-1 rounded text-xs font-mono bg-panel2 border border-amber/40 text-amber">
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Linked Cases Timeline */}
            <div>
              <h4 className="text-ink font-display text-base mb-3">
                Linked Case Records ({profile.linked_cases.length})
              </h4>
              <div className="space-y-2">
                {profile.linked_cases.map((c) => (
                  <Link
                    key={c.id}
                    to={`/cases/${c.id}`}
                    className="block bg-panel2 border border-line hover:border-teal rounded p-3 transition"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-xs text-teal">{c.case_id}</span>
                      <span className="text-xs font-mono text-muted">{c.district}</span>
                    </div>
                    <p className="text-ink text-sm font-medium">{c.title}</p>
                    <p className="text-muted text-xs font-mono mt-1">
                      {c.crime_type} &middot; {c.severity} &middot; {new Date(c.incident_date).toLocaleDateString()}
                    </p>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Offenders() {
  const [offenders, setOffenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [selectedPersonId, setSelectedPersonId] = useState(null);

  useEffect(() => {
    fetchOffenders()
      .then(setOffenders)
      .catch(() => setError("Could not load offender profiles. Check authorization."))
      .finally(() => setLoading(false));
  }, []);

  const filteredOffenders = offenders.filter((o) => {
    if (filter === "all") return true;
    return o.risk_category === filter;
  });

  return (
    <div className="p-8">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">CRIMINOLOGY · BEHAVIORAL PROFILING</p>
          <h2 className="font-display text-3xl text-ink">Offender Risk Directory</h2>
        </div>
        <a
          href="/RISK_SCORING.md"
          target="_blank"
          rel="noreferrer"
          className="text-xs font-mono text-teal border border-teal/40 hover:bg-teal/10 rounded px-3 py-1.5 transition"
        >
          📄 View Scoring Model & Formula
        </a>
      </div>

      {error && (
        <p className="text-crit text-sm font-mono border border-crit/40 bg-crit/10 rounded px-4 py-3 mb-6">
          {error}
        </p>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-6">
        {["all", "high", "medium", "low"].map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 rounded text-xs font-mono uppercase transition border ${
              filter === cat
                ? "bg-amber text-base font-semibold border-amber"
                : "border-line text-muted hover:text-ink bg-panel"
            }`}
          >
            {cat} {cat !== "all" && `Risk`}
          </button>
        ))}
      </div>

      {/* Directory Table */}
      <div className="bg-panel border border-line rounded-md overflow-hidden shadow-lg">
        <table className="w-full">
          <thead>
            <tr className="border-b border-line bg-panel2/50">
              <th className="text-left px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                Offender / Suspect
              </th>
              <th className="text-left px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                Phone Link
              </th>
              <th className="text-center px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                Cases
              </th>
              <th className="text-left px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                MO Pattern Tags
              </th>
              <th className="text-left px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                Last Active
              </th>
              <th className="text-right px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                Risk Rating
              </th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted text-sm font-mono">
                  Running criminal history & behavioral risk scoring...
                </td>
              </tr>
            )}
            {!loading && filteredOffenders.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted text-sm font-mono">
                  No offenders match the selected filter.
                </td>
              </tr>
            )}
            {filteredOffenders.map((o) => (
              <tr
                key={o.person_id}
                onClick={() => setSelectedPersonId(o.person_id)}
                className="border-t border-line hover:bg-panel2/60 cursor-pointer transition"
              >
                <td className="px-4 py-3">
                  <p className="text-ink text-sm font-medium hover:text-teal transition">{o.name}</p>
                </td>
                <td className="px-4 py-3 text-muted text-xs font-mono">
                  {o.phone_number || "No phone linked"}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-panel2 border border-line text-ink">
                    {o.case_count}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {o.mo_tags.map((t, idx) => (
                      <span key={idx} className="text-[10px] font-mono px-2 py-0.5 rounded bg-panel2 text-amber border border-amber/30">
                        {t}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3 text-muted text-xs font-mono">
                  {o.last_recorded_date ? new Date(o.last_recorded_date).toLocaleDateString() : "Unknown"}
                </td>
                <td className="px-4 py-3 text-right">
                  <RiskBadge category={o.risk_category} score={o.risk_score} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedPersonId && (
        <OffenderDrawer
          personId={selectedPersonId}
          onClose={() => setSelectedPersonId(null)}
        />
      )}
    </div>
  );
}
