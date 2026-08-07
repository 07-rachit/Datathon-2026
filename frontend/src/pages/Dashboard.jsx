import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { fetchDashboardStats, fetchPredictions } from "../lib/api.js";

const SEVERITY_COLOR = {
  low: "#3FD6C1",
  medium: "#F0A202",
  high: "#E8833A",
  critical: "#E23D5B",
};

const BAR_COLORS = ["#3FD6C1", "#F0A202", "#E8833A", "#E23D5B", "#7C8AA3", "#5B8DEF"];

function StatCard({ label, value, accent }) {
  return (
    <div className="bg-panel border border-line rounded-md px-5 py-4">
      <p className="text-muted text-xs font-mono tracking-wide uppercase mb-1">{label}</p>
      <p className={`font-display text-4xl ${accent || "text-ink"}`}>{value}</p>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [predictions, setPredictions] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboardStats()
      .then(setStats)
      .catch(() => setError("Could not load dashboard data. Is the API running?"));
    fetchPredictions()
      .then(setPredictions)
      .catch(() => {});
  }, []);

  return (
    <div className="p-8">
      <div className="mb-6">
        <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">OVERVIEW</p>
        <h2 className="font-display text-3xl text-ink">Situation Dashboard</h2>
      </div>

      {error && (
        <p className="text-crit text-sm font-mono border border-crit/40 bg-crit/10 rounded px-4 py-3 mb-6">
          {error}
        </p>
      )}

      {stats && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-8">
            <StatCard label="Total Cases" value={stats.total_cases} />
            <StatCard label="Open" value={stats.open_cases} accent="text-amber" />
            <StatCard label="Under Review" value={stats.under_review_cases} accent="text-teal" />
            <StatCard label="Closed" value={stats.closed_cases} accent="text-muted" />
          </div>

          <div className="grid grid-cols-2 gap-4 mb-8">
            <div className="bg-panel border border-line rounded-md p-5">
              <p className="text-ink font-display text-xl mb-4">Crime Type Distribution</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={stats.crime_type_distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#232E42" />
                  <XAxis dataKey="crime_type" tick={{ fill: "#7C8AA3", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#7C8AA3", fontSize: 11 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: "#161F2E", border: "1px solid #232E42", fontSize: 12 }}
                    labelStyle={{ color: "#DCE3EE" }}
                  />
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {stats.crime_type_distribution.map((_, i) => (
                      <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-panel border border-line rounded-md p-5">
              <p className="text-ink font-display text-xl mb-4">District Summary</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={stats.district_summary} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#232E42" />
                  <XAxis type="number" tick={{ fill: "#7C8AA3", fontSize: 11 }} allowDecimals={false} />
                  <YAxis
                    dataKey="district"
                    type="category"
                    tick={{ fill: "#7C8AA3", fontSize: 11 }}
                    width={110}
                  />
                  <Tooltip
                    contentStyle={{ background: "#161F2E", border: "1px solid #232E42", fontSize: 12 }}
                    labelStyle={{ color: "#DCE3EE" }}
                  />
                  <Bar dataKey="count" fill="#3FD6C1" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-panel border border-line rounded-md p-5">
            <p className="text-ink font-display text-xl mb-4">Recent High-Severity Alerts</p>
            <div className="space-y-2">
              {stats.recent_alerts.length === 0 && (
                <p className="text-muted text-sm">No high-severity alerts right now.</p>
              )}
              {stats.recent_alerts.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between border border-line rounded px-4 py-3 bg-panel2"
                >
                  <div>
                    <p className="font-mono text-xs text-muted">{c.case_id}</p>
                    <p className="text-ink text-sm">{c.title}</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-muted text-xs">{c.district}</span>
                    <span
                      className="text-xs font-mono uppercase px-2 py-1 rounded"
                      style={{
                        color: SEVERITY_COLOR[c.severity],
                        border: `1px solid ${SEVERITY_COLOR[c.severity]}55`,
                      }}
                    >
                      {c.severity}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {predictions && predictions.alerts.filter((a) => a.trend === "rising").length > 0 && (
            <div className="bg-panel border border-line rounded-md p-5 mt-6">
              <p className="text-ink font-display text-xl mb-1">Predictive Alerts</p>
              <p className="text-muted text-xs font-mono mb-4">
                Districts trending up &mdash; last 30 days vs. prior 30 days
              </p>
              <div className="space-y-2">
                {predictions.alerts
                  .filter((a) => a.trend === "rising")
                  .map((a) => (
                    <div
                      key={a.district}
                      className="flex items-center justify-between border border-crit/30 bg-crit/5 rounded px-4 py-3"
                    >
                      <div>
                        <p className="text-ink text-sm">{a.district}</p>
                        <p className="text-muted text-xs font-mono">
                          {a.recent_30d} recent vs {a.prior_30d} prior incidents
                        </p>
                      </div>
                      <span className="text-crit text-sm font-mono">
                        ▲ {a.change_pct > 0 ? "+" : ""}{a.change_pct}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
