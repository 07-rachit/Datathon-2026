import { useState, useEffect } from "react";
import { fetchCitizenReports, verifyCitizenReport, analyzeReportAI } from "../lib/api.js";

export default function CitizenReportsAdmin() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [selectedReport, setSelectedReport] = useState(null);
  const [actionModal, setActionModal] = useState(null); // { type: "approve" | "reject", report: obj }
  const [rejectionReason, setRejectionReason] = useState("");
  const [processingId, setProcessingId] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  useEffect(() => {
    loadReports();
  }, [statusFilter]);

  async function loadReports() {
    try {
      setLoading(true);
      const data = await fetchCitizenReports(statusFilter);
      setReports(data);
    } catch (err) {
      console.error("Failed to fetch citizen reports", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(report, action) {
    try {
      setProcessingId(report.id);
      const res = await verifyCitizenReport(
        report.id,
        action,
        action === "reject" ? rejectionReason : ""
      );

      if (action === "approve") {
        setToastMessage(`✅ Report ${report.tracking_id} approved! Case ${res.created_case_id || "ID"} generated & integrated into TRACE Engine.`);
      } else {
        setToastMessage(`❌ Report ${report.tracking_id} marked as rejected.`);
      }

      setActionModal(null);
      setRejectionReason("");
      loadReports();
    } catch (err) {
      alert(err.response?.data?.detail || "Action failed. Please try again.");
    } finally {
      setProcessingId(null);
    }
  }

  async function handleReAnalyzeAI(reportId) {
    try {
      setProcessingId(reportId);
      await analyzeReportAI(reportId);
      setToastMessage("🤖 AI analysis re-executed successfully.");
      loadReports();
    } catch (err) {
      alert("AI re-analysis failed.");
    } finally {
      setProcessingId(null);
    }
  }

  // Metrics calculation
  const pendingCount = reports.filter((r) => r.status === "pending").length;
  const criticalCount = reports.filter((r) => r.ai_priority === "critical" || r.ai_priority === "high").length;
  const verifiedCount = reports.filter((r) => r.status === "verified" || r.status === "approved").length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="p-4 bg-teal/20 border border-teal/40 rounded-lg text-teal text-sm font-mono flex items-center justify-between animate-fade-in shadow-xl">
          <span>{toastMessage}</span>
          <button onClick={() => setToastMessage(null)} className="text-teal font-bold hover:underline">
            ✕
          </button>
        </div>
      )}

      {/* Header Banner */}
      <div className="bg-panel border border-line p-6 rounded-lg shadow-xl relative overflow-hidden">
        <div className="scanline absolute inset-0 pointer-events-none opacity-30"></div>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs text-amber px-2 py-0.5 bg-amber/10 border border-amber/30 rounded uppercase tracking-wider">
                Officer Desk
              </span>
              <span className="text-muted text-xs font-mono">• Verification Pipeline</span>
            </div>
            <h1 className="font-display text-3xl text-ink tracking-wide">
              CITIZEN REPORTS <span className="text-amber">VERIFICATION</span>
            </h1>
            <p className="text-muted text-sm mt-1">
              Review citizen submitted crime reports, run AI classification, verify evidence, and auto-generate official cases in TRACE Engine.
            </p>
          </div>

          {/* Quick Metrics */}
          <div className="flex gap-3">
            <div className="bg-base border border-line px-4 py-2.5 rounded-lg text-center font-mono">
              <p className="text-[10px] text-muted uppercase">Pending Review</p>
              <p className="text-xl font-bold text-amber">{pendingCount}</p>
            </div>
            <div className="bg-base border border-line px-4 py-2.5 rounded-lg text-center font-mono">
              <p className="text-[10px] text-muted uppercase">High/Critical Priority</p>
              <p className="text-xl font-bold text-crit">{criticalCount}</p>
            </div>
            <div className="bg-base border border-line px-4 py-2.5 rounded-lg text-center font-mono">
              <p className="text-[10px] text-muted uppercase">Cases Created</p>
              <p className="text-xl font-bold text-teal">{verifiedCount}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between bg-panel p-2 rounded-lg border border-line">
        <div className="flex gap-2">
          {[
            { key: "pending", label: "⏳ PENDING VERIFICATION" },
            { key: "verified", label: "✅ APPROVED / CASE CREATED" },
            { key: "rejected", label: "❌ REJECTED" },
            { key: "", label: "ALL REPORTS" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              className={`px-4 py-2 text-xs font-mono rounded transition ${
                statusFilter === tab.key
                  ? "bg-amber text-base font-bold shadow"
                  : "text-muted hover:text-ink hover:bg-panel2"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <button
          onClick={loadReports}
          className="text-xs font-mono text-muted hover:text-ink px-3 py-1.5 rounded border border-line bg-panel2"
        >
          🔄 Refresh List
        </button>
      </div>

      {/* Report List */}
      {loading ? (
        <div className="p-12 text-center text-muted font-mono text-sm bg-panel border border-line rounded-lg">
          ⌛ Loading citizen reports...
        </div>
      ) : reports.length === 0 ? (
        <div className="p-12 text-center text-muted font-mono text-sm bg-panel border border-line rounded-lg">
          No reports found matching current filter filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {reports.map((report) => (
            <div
              key={report.id}
              className="bg-panel border border-line hover:border-amber/50 rounded-lg p-5 transition space-y-4 shadow-lg"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-line pb-3">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-lg font-bold text-amber">{report.tracking_id}</span>
                  <span className="text-xs font-mono bg-panel2 border border-line px-2.5 py-1 rounded text-ink font-semibold">
                    {report.crime_type}
                  </span>
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                    report.ai_priority === "critical"
                      ? "bg-crit/20 text-crit border border-crit/40"
                      : report.ai_priority === "high"
                      ? "bg-amber/20 text-amber border border-amber/40"
                      : "bg-teal/20 text-teal border border-teal/40"
                  }`}>
                    Priority: {report.ai_priority?.toUpperCase()}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 text-xs font-mono font-bold rounded uppercase ${
                    report.status === "verified" || report.status === "approved"
                      ? "bg-teal/20 text-teal border border-teal/40"
                      : report.status === "rejected"
                      ? "bg-crit/20 text-crit border border-crit/40"
                      : "bg-amber/20 text-amber border border-amber/40"
                  }`}>
                    Status: {report.status}
                  </span>
                </div>
              </div>

              {/* Report Description & Details */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2 space-y-2">
                  <p className="text-xs font-mono text-muted uppercase">Incident Details & Description</p>
                  <p className="text-sm text-ink leading-relaxed">{report.description}</p>
                  <div className="flex flex-wrap gap-4 text-xs font-mono text-muted pt-2 border-t border-line">
                    <span>📍 Location: {report.location}</span>
                    <span>📅 Date: {new Date(report.incident_date).toLocaleString()}</span>
                  </div>
                </div>

                {/* AI Summary Box */}
                <div className="bg-panel2 p-3.5 rounded-lg border border-line space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-amber font-bold flex items-center gap-1">
                      🤖 TRACE AI Summary
                    </span>
                    <button
                      onClick={() => handleReAnalyzeAI(report.id)}
                      disabled={processingId === report.id}
                      className="text-[10px] font-mono text-muted hover:text-amber underline"
                    >
                      Re-Analyze
                    </button>
                  </div>
                  <p className="text-xs text-ink leading-relaxed font-body">
                    {report.ai_summary || "AI analysis available."}
                  </p>
                </div>
              </div>

              {/* Reporter Contact & Evidence items bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-line text-xs font-mono">
                <div className="text-muted flex items-center gap-2">
                  <span className="text-amber">🔒 RBAC Contact:</span>
                  <span className="text-ink font-semibold">{report.reporter_name}</span>
                  <span>({report.reporter_phone})</span>
                  {report.reporter_email && <span>• {report.reporter_email}</span>}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedReport(selectedReport?.id === report.id ? null : report)}
                    className="bg-panel2 hover:bg-line border border-line text-ink text-xs px-3 py-1.5 rounded transition"
                  >
                    📁 Evidence ({report.evidence_items?.length || 0})
                  </button>

                  {report.status === "pending" && (
                    <>
                      <button
                        onClick={() => setActionModal({ type: "reject", report })}
                        disabled={processingId === report.id}
                        className="bg-crit/20 hover:bg-crit/30 text-crit border border-crit/40 text-xs px-3 py-1.5 rounded transition font-bold"
                      >
                        Reject Report
                      </button>
                      <button
                        onClick={() => setActionModal({ type: "approve", report })}
                        disabled={processingId === report.id}
                        className="bg-amber hover:bg-amber/90 text-base text-xs font-bold px-4 py-1.5 rounded transition shadow"
                      >
                        Approve & Create Case →
                      </button>
                    </>
                  )}

                  {report.created_case_id && (
                    <span className="text-xs font-mono text-teal font-bold bg-teal/10 px-3 py-1.5 rounded border border-teal/30">
                      Created Case: {report.created_case_id}
                    </span>
                  )}
                </div>
              </div>

              {/* Evidence Expanded Section */}
              {selectedReport?.id === report.id && (
                <div className="bg-panel2 p-4 rounded-lg border border-line space-y-2 animate-fade-in mt-3">
                  <p className="text-xs font-mono text-teal uppercase">Attached Evidence Files</p>
                  {report.evidence_items && report.evidence_items.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {report.evidence_items.map((ev, idx) => (
                        <div key={idx} className="bg-base p-3 rounded border border-line flex items-center justify-between text-xs font-mono">
                          <div className="flex items-center gap-2 truncate">
                            <span className="text-amber">📄</span>
                            <span className="truncate text-ink">[{ev.file_type.toUpperCase()}] {ev.file_name}</span>
                          </div>
                          <span className="text-[10px] text-muted">{ev.file_path}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted font-mono">No files attached with this report.</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Verification / Approval Confirmation Modal */}
      {actionModal && (
        <div className="fixed inset-0 bg-base/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-panel border border-line max-w-lg w-full rounded-lg p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-display text-ink border-b border-line pb-2">
              {actionModal.type === "approve" ? "APPROVE REPORT & CREATE CASE" : "REJECT CITIZEN REPORT"}
            </h3>

            <p className="text-xs font-mono text-muted">
              Tracking ID: <span className="text-amber font-bold">{actionModal.report.tracking_id}</span> ({actionModal.report.crime_type})
            </p>

            {actionModal.type === "approve" ? (
              <div className="bg-panel2 p-4 rounded border border-line space-y-2 text-xs font-mono text-ink">
                <p className="text-teal font-bold">Action Details:</p>
                <p>1. Generates official Case ID in `cases` database.</p>
                <p>2. Automatically maps incident location to TRACE Hotspot Map & Analytics.</p>
                <p>3. Dispatches notifications to duty officers & investigators.</p>
              </div>
            ) : (
              <div>
                <label className="block text-xs font-mono text-muted mb-1">
                  REJECTION REASON <span className="text-crit">*</span>
                </label>
                <textarea
                  rows={3}
                  placeholder="Specify why the report is being rejected (e.g. Duplicate submission, invalid evidence)..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full bg-base border border-line rounded px-3 py-2 text-sm text-ink focus:border-amber focus:outline-none"
                />
              </div>
            )}

            <div className="flex justify-end gap-3 pt-3 border-t border-line font-mono text-xs">
              <button
                onClick={() => setActionModal(null)}
                className="px-4 py-2 rounded bg-panel2 border border-line text-muted hover:text-ink"
              >
                Cancel
              </button>

              <button
                onClick={() => handleVerify(actionModal.report, actionModal.type)}
                disabled={processingId === actionModal.report.id}
                className={`px-5 py-2 rounded font-bold transition shadow ${
                  actionModal.type === "approve"
                    ? "bg-amber text-base hover:bg-amber/90"
                    : "bg-crit text-ink hover:bg-crit/90"
                }`}
              >
                {processingId === actionModal.report.id
                  ? "Processing..."
                  : actionModal.type === "approve"
                  ? "Confirm Approval & Create Case"
                  : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
