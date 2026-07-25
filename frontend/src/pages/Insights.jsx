import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ScatterChart, Scatter, ZAxis, LineChart, Line
} from "recharts";
import { fetchDemographicInsights, fetchSocioeconomicCorrelation, fetchSeasonalTrends } from "../lib/api.js";

const COLORS = ["#3FD6C1", "#F0A202", "#E8833A", "#E23D5B", "#7C8AA3", "#5B8DEF"];

export default function Insights() {
  const [demographics, setDemographics] = useState(null);
  const [correlation, setCorrelation] = useState(null);
  const [seasonal, setSeasonal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchDemographicInsights(), fetchSocioeconomicCorrelation(), fetchSeasonalTrends()])
      .then(([demoData, corrData, seasonData]) => {
        setDemographics(demoData);
        setCorrelation(corrData);
        setSeasonal(seasonData);
      })
      .catch(() => setError("Could not load socio-demographic insights. Analyst or Admin role required."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6 flex items-end justify-between">
        <div>
          <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">SOCIO-DEMOGRAPHIC ANALYSIS & SEASONAL TRENDS</p>
          <h2 className="font-display text-3xl text-ink">Crime Patterns & Socioeconomic Correlation</h2>
        </div>
        <span className="text-xs font-mono text-amber border border-amber/40 bg-amber/10 px-3 py-1.5 rounded">
          DEMO MODE: Synthetic Demographic Data
        </span>
      </div>

      {/* Mandatory Policy Disclaimer Banner */}
      <div className="bg-amber/10 border border-amber/40 rounded-md p-4 mb-8 flex items-start gap-3">
        <span className="text-amber font-mono text-xl leading-none">⚠️</span>
        <div>
          <p className="text-ink font-display text-sm font-semibold mb-0.5">Statistical & Policy Disclaimer</p>
          <p className="text-muted text-xs leading-relaxed font-body">
            These socio-demographic insights and correlation metrics represent aggregate statistical patterns intended strictly for macro policy planning, resource allocation, and preventive intervention strategies. 
            <strong className="text-ink"> Under no circumstances shall these aggregate models be utilized for individual suspect profiling, targeted enforcement, or discriminatory practices.</strong>
          </p>
        </div>
      </div>

      {error ? (
        <div className="border border-crit/40 bg-crit/10 text-crit p-4 rounded font-mono text-sm">{error}</div>
      ) : loading ? (
        <div className="text-muted font-mono text-sm py-12 text-center">Computing aggregate demographic distributions...</div>
      ) : (
        <div className="space-y-8">
          {/* Seasonal Trends & Day-of-Week Analysis */}
          {seasonal && (
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-panel border border-line rounded-md p-5">
                <p className="font-display text-lg mb-1">Month-of-Year Seasonal Pattern</p>
                <p className="text-muted text-xs font-mono mb-4">Historical crime volume distribution across calendar months</p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={seasonal.monthly_trends}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#243242" />
                      <XAxis dataKey="month" stroke="#7C8AA3" fontSize={11} />
                      <YAxis stroke="#7C8AA3" fontSize={11} />
                      <Tooltip contentStyle={{ backgroundColor: "#151D28", borderColor: "#243242", color: "#F1F5F9" }} />
                      <Bar dataKey="case_count" fill="#3FD6C1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-panel border border-line rounded-md p-5">
                <p className="font-display text-lg mb-1">Day-of-Week Distribution</p>
                <p className="text-muted text-xs font-mono mb-4">Weekly incident frequency pattern</p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={seasonal.weekday_trends}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#243242" />
                      <XAxis dataKey="day" stroke="#7C8AA3" fontSize={11} />
                      <YAxis stroke="#7C8AA3" fontSize={11} />
                      <Tooltip contentStyle={{ backgroundColor: "#151D28", borderColor: "#243242", color: "#F1F5F9" }} />
                      <Bar dataKey="case_count" fill="#F0A202" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* High Context Events Reference Cards */}
          {seasonal?.high_context_events && (
            <div className="bg-panel border border-line rounded-md p-5">
              <p className="font-display text-lg mb-3">High-Risk Context Event Windows</p>
              <div className="grid grid-cols-3 gap-4">
                {seasonal.high_context_events.map((evt, idx) => (
                  <div key={idx} className="bg-panel2 border border-line rounded p-4 text-xs font-mono">
                    <p className="text-teal font-semibold text-sm mb-1">{evt.name}</p>
                    <p className="text-muted mb-2">Period: {evt.period}</p>
                    <span className="inline-block px-2 py-0.5 rounded bg-amber/10 border border-amber/40 text-amber text-[10px]">
                      {evt.risk_level}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Demographics Grid */}
          {demographics && (
            <div className="grid grid-cols-2 gap-6">
              {/* Age Groups */}
              <div className="bg-panel border border-line rounded-md p-5">
                <p className="font-display text-lg mb-1">Age Involvement Distribution</p>
                <p className="text-muted text-xs font-mono mb-4">Aggregate count of involved individuals by age bracket</p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={demographics.by_age_group}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#243242" />
                      <XAxis dataKey="label" stroke="#7C8AA3" fontSize={11} />
                      <YAxis stroke="#7C8AA3" fontSize={11} />
                      <Tooltip contentStyle={{ backgroundColor: "#151D28", borderColor: "#243242", color: "#F1F5F9" }} />
                      <Bar dataKey="count" fill="#3FD6C1" radius={[4, 4, 0, 0]}>
                        {demographics.by_age_group.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Area Type */}
              <div className="bg-panel border border-line rounded-md p-5">
                <p className="font-display text-lg mb-1">Urban vs Rural Incident Split</p>
                <p className="text-muted text-xs font-mono mb-4">Geographic distribution of recorded incidents</p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={demographics.by_area_type}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#243242" />
                      <XAxis dataKey="label" stroke="#7C8AA3" fontSize={11} />
                      <YAxis stroke="#7C8AA3" fontSize={11} />
                      <Tooltip contentStyle={{ backgroundColor: "#151D28", borderColor: "#243242", color: "#F1F5F9" }} />
                      <Bar dataKey="count" fill="#F0A202" radius={[4, 4, 0, 0]}>
                        {demographics.by_area_type.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* Socioeconomic Correlation Table */}
          {correlation && (
            <div className="bg-panel border border-line rounded-md p-5">
              <p className="font-display text-xl mb-1">District Socioeconomic Indicator Correlation</p>
              <p className="text-muted text-xs font-mono mb-4">Macro-level correlation between district crime volume, unemployment, and literacy rates</p>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs font-mono">
                  <thead>
                    <tr className="border-b border-line text-muted uppercase">
                      <th className="py-2.5 px-3">District</th>
                      <th className="py-2.5 px-3 text-right">Crime Count</th>
                      <th className="py-2.5 px-3 text-right">Unemployment Rate</th>
                      <th className="py-2.5 px-3 text-right">Literacy Rate</th>
                      <th className="py-2.5 px-3 text-right">Urbanization %</th>
                      <th className="py-2.5 px-3 text-right">Population</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line/40">
                    {correlation.district_correlations.map((row) => (
                      <tr key={row.district} className="hover:bg-panel2/50 transition">
                        <td className="py-3 px-3 text-ink font-semibold">{row.district}</td>
                        <td className="py-3 px-3 text-right text-amber font-bold">{row.crime_count}</td>
                        <td className="py-3 px-3 text-right text-teal">{row.unemployment_rate}%</td>
                        <td className="py-3 px-3 text-right text-ink">{row.literacy_rate}%</td>
                        <td className="py-3 px-3 text-right text-muted">{row.urbanization_pct}%</td>
                        <td className="py-3 px-3 text-right text-muted">{row.population.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
