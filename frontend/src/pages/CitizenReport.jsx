import { useState } from "react";
import { submitCitizenReport, trackCitizenReport } from "../lib/api.js";

export default function CitizenReport() {
  const [activeTab, setActiveTab] = useState("report"); // "report" or "track"

  // Report Form State
  const [crimeType, setCrimeType] = useState("Cyber Fraud / Phishing");
  const [incidentDate, setIncidentDate] = useState(
    new Date().toISOString().slice(0, 16)
  );
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [reporterName, setReporterName] = useState("");
  const [reporterPhone, setReporterPhone] = useState("");
  const [reporterEmail, setReporterEmail] = useState("");
  
  // Evidence upload simulation
  const [evidenceList, setEvidenceList] = useState([]);
  const [evidenceName, setEvidenceName] = useState("");
  const [evidenceType, setEvidenceType] = useState("image");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [submissionResult, setSubmissionResult] = useState(null);

  // Tracking State
  const [trackingIdInput, setTrackingIdInput] = useState("");
  const [trackingLoading, setTrackingLoading] = useState(false);
  const [trackedReport, setTrackedReport] = useState(null);
  const [trackingError, setTrackingError] = useState(null);

  function handleAddEvidence() {
    if (!evidenceName.trim()) return;
    setEvidenceList([
      ...evidenceList,
      { file_name: evidenceName.trim(), file_type: evidenceType, file_path: `/uploads/evidence/${evidenceName.trim()}` }
    ]);
    setEvidenceName("");
  }

  function handleRemoveEvidence(index) {
    setEvidenceList(evidenceList.filter((_, i) => i !== index));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    if (!location.trim() || !description.trim() || !reporterName.trim() || !reporterPhone.trim()) {
      setError("Please fill out all required fields marked with *");
      return;
    }

    try {
      setLoading(true);
      const payload = {
        crime_type: crimeType,
        incident_date: new Date(incidentDate).toISOString(),
        location: location.trim(),
        latitude: 12.9716,
        longitude: 77.5946,
        description: description.trim(),
        reporter_name: reporterName.trim(),
        reporter_phone: reporterPhone.trim(),
        reporter_email: reporterEmail.trim() || null,
        evidence: evidenceList,
      };

      const result = await submitCitizenReport(payload);
      setSubmissionResult(result);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to submit report. Please check server connection.");
    } finally {
      setLoading(false);
    }
  }

  async function handleTrackSearch(e) {
    if (e) e.preventDefault();
    if (!trackingIdInput.trim()) return;
    setTrackingError(null);
    setTrackingLoading(true);
    setTrackedReport(null);

    try {
      const res = await trackCitizenReport(trackingIdInput.trim());
      setTrackedReport(res);
    } catch (err) {
      setTrackingError(err.response?.data?.detail || "No report found with that Tracking ID.");
    } finally {
      setTrackingLoading(false);
    }
  }

  function handlePrintReceipt() {
    window.print();
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-panel border border-line p-6 rounded-lg shadow-xl relative overflow-hidden">
        <div className="scanline absolute inset-0 pointer-events-none opacity-30"></div>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs text-amber px-2 py-0.5 bg-amber/10 border border-amber/30 rounded uppercase tracking-wider">
                TRACE Module
              </span>
              <span className="text-muted text-xs font-mono">• Citizen Portal</span>
            </div>
            <h1 className="font-display text-3xl text-ink tracking-wide">
              CITIZEN <span className="text-amber">CRIME REPORTING</span>
            </h1>
            <p className="text-muted text-sm mt-1 max-w-2xl">
              Securely submit crime reports directly to the TRACE Investigation Engine. Track verification status in real time and generate official submission receipts.
            </p>
          </div>

          {/* Navigation Tabs */}
          <div className="flex bg-panel2 p-1 rounded-md border border-line">
            <button
              onClick={() => { setActiveTab("report"); setSubmissionResult(null); }}
              className={`px-4 py-2 text-xs font-mono rounded transition ${
                activeTab === "report"
                  ? "bg-amber text-base font-bold shadow"
                  : "text-muted hover:text-ink"
              }`}
            >
              + REPORT A CRIME
            </button>
            <button
              onClick={() => setActiveTab("track")}
              className={`px-4 py-2 text-xs font-mono rounded transition ${
                activeTab === "track"
                  ? "bg-amber text-base font-bold shadow"
                  : "text-muted hover:text-ink"
              }`}
            >
              🔍 TRACK STATUS
            </button>
          </div>
        </div>
      </div>

      {/* ── TAB 1: REPORT FORM ────────────────────────────────────────────── */}
      {activeTab === "report" && !submissionResult && (
        <form onSubmit={handleSubmit} className="bg-panel border border-line rounded-lg p-6 space-y-6 shadow-lg animate-fade-in">
          {error && (
            <div className="p-4 bg-crit/10 border border-crit/30 rounded text-crit text-sm font-mono flex items-center gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {/* Section 1: Crime Details */}
          <div>
            <h2 className="text-sm font-mono text-teal uppercase tracking-wider mb-4 border-b border-line pb-2">
              01. Incident & Location Details
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono text-muted mb-1">
                  CRIME TYPE <span className="text-crit">*</span>
                </label>
                <select
                  value={crimeType}
                  onChange={(e) => setCrimeType(e.target.value)}
                  className="w-full bg-base border border-line rounded px-3 py-2 text-sm text-ink focus:border-amber focus:outline-none"
                >
                  <option value="Cyber Fraud / Phishing">Cyber Fraud / Phishing</option>
                  <option value="Burglary">Burglary / Break-in</option>
                  <option value="Vehicle Theft">Vehicle Theft</option>
                  <option value="Robbery / Extortion">Robbery / Extortion</option>
                  <option value="Assault">Physical Assault</option>
                  <option value="Narcotics Incident">Narcotics Incident</option>
                  <option value="CCTV Suspicious Activity">CCTV Suspicious Activity</option>
                  <option value="Other Crime">Other Crime</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-muted mb-1">
                  DATE & TIME OF INCIDENT <span className="text-crit">*</span>
                </label>
                <input
                  type="datetime-local"
                  value={incidentDate}
                  onChange={(e) => setIncidentDate(e.target.value)}
                  className="w-full bg-base border border-line rounded px-3 py-2 text-sm text-ink focus:border-amber focus:outline-none"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-mono text-muted mb-1">
                  INCIDENT LOCATION / ADDRESS <span className="text-crit">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Near Commercial Street Kiosk #4, Indiranagar, Bengaluru"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="w-full bg-base border border-line rounded px-3 py-2 text-sm text-ink focus:border-amber focus:outline-none"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-mono text-muted mb-1">
                  CRIME DESCRIPTION & EVIDENCE SUMMARY <span className="text-crit">*</span>
                </label>
                <textarea
                  rows={4}
                  placeholder="Describe the incident in detail: what happened, persons involved, vehicle numbers, money lost, or suspicious observations..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-base border border-line rounded px-3 py-2 text-sm text-ink focus:border-amber focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Upload Evidence */}
          <div>
            <h2 className="text-sm font-mono text-teal uppercase tracking-wider mb-4 border-b border-line pb-2 flex items-center justify-between">
              <span>02. Evidence Attachments (Optional)</span>
              <span className="text-xs text-muted font-normal">Images, Video, Audio, CCTV clips, PDFs</span>
            </h2>

            <div className="bg-panel2 p-4 rounded-lg border border-line space-y-3">
              <div className="flex flex-col sm:flex-row gap-3">
                <select
                  value={evidenceType}
                  onChange={(e) => setEvidenceType(e.target.value)}
                  className="bg-base border border-line rounded px-3 py-2 text-xs text-ink focus:border-amber focus:outline-none font-mono"
                >
                  <option value="image">Image / Photo</option>
                  <option value="video">Video Recording</option>
                  <option value="audio">Audio Clip</option>
                  <option value="cctv">CCTV Footage</option>
                  <option value="document">PDF / Document</option>
                </select>
                <input
                  type="text"
                  placeholder="File name (e.g., cctv_footage_camera1.mp4)"
                  value={evidenceName}
                  onChange={(e) => setEvidenceName(e.target.value)}
                  className="flex-1 bg-base border border-line rounded px-3 py-2 text-xs text-ink focus:border-amber focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleAddEvidence}
                  className="bg-teal/20 text-teal border border-teal/40 hover:bg-teal hover:text-base font-mono text-xs px-4 py-2 rounded transition"
                >
                  + Add Evidence File
                </button>
              </div>

              {evidenceList.length > 0 && (
                <div className="space-y-2 mt-3 pt-3 border-t border-line">
                  <p className="text-xs font-mono text-muted uppercase">Attached Evidence Items ({evidenceList.length}):</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {evidenceList.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-base px-3 py-2 rounded border border-line text-xs font-mono">
                        <span className="truncate text-ink">📁 [{item.file_type.toUpperCase()}] {item.file_name}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveEvidence(idx)}
                          className="text-crit hover:underline ml-2"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Section 3: Reporter Details */}
          <div>
            <h2 className="text-sm font-mono text-teal uppercase tracking-wider mb-2 border-b border-line pb-2 flex items-center justify-between">
              <span>03. Reporter Contact Details</span>
              <span className="text-[10px] text-amber font-mono bg-amber/10 px-2 py-0.5 rounded border border-amber/20">
                🔒 RBAC Protected
              </span>
            </h2>
            <p className="text-xs text-muted mb-4">
              Your contact details are encrypted and protected under RBAC. Only assigned investigating officers can view your contact information.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-mono text-muted mb-1">
                  FULL NAME <span className="text-crit">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Rohan Mehta"
                  value={reporterName}
                  onChange={(e) => setReporterName(e.target.value)}
                  className="w-full bg-base border border-line rounded px-3 py-2 text-sm text-ink focus:border-amber focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-muted mb-1">
                  MOBILE NUMBER <span className="text-crit">*</span>
                </label>
                <input
                  type="tel"
                  placeholder="e.g. +91-9876543210"
                  value={reporterPhone}
                  onChange={(e) => setReporterPhone(e.target.value)}
                  className="w-full bg-base border border-line rounded px-3 py-2 text-sm text-ink focus:border-amber focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-muted mb-1">
                  EMAIL ADDRESS (OPTIONAL)
                </label>
                <input
                  type="email"
                  placeholder="e.g. rohan.m@example.com"
                  value={reporterEmail}
                  onChange={(e) => setReporterEmail(e.target.value)}
                  className="w-full bg-base border border-line rounded px-3 py-2 text-sm text-ink focus:border-amber focus:outline-none"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-line flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="bg-amber hover:bg-amber/90 text-base font-mono font-bold text-sm px-6 py-3 rounded shadow-lg transition flex items-center gap-2"
            >
              {loading ? (
                <><span>⌛</span> Submitting & AI Processing...</>
              ) : (
                <><span>🚀</span> SUBMIT CRIME REPORT</>
              )}
            </button>
          </div>
        </form>
      )}

      {/* ── SUCCESS STATE & RECEIPT VIEW ──────────────────────────────────── */}
      {submissionResult && (
        <div className="bg-panel border border-line rounded-lg p-6 space-y-6 animate-slide-up shadow-2xl">
          <div className="flex items-center justify-between border-b border-line pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">✅</span>
                <h2 className="text-xl font-display text-ink">REPORT SUBMITTED SUCCESSFULLY</h2>
              </div>
              <p className="text-xs font-mono text-muted mt-1">
                Every report is processed through the TRACE Investigation Engine.
              </p>
            </div>
            <div className="flex items-center gap-2 print:hidden">
              <button
                onClick={handlePrintReceipt}
                className="bg-panel2 hover:bg-line border border-line text-ink text-xs font-mono px-3 py-2 rounded transition"
              >
                🖨️ Print / Download Receipt
              </button>
              <button
                onClick={() => {
                  setTrackingIdInput(submissionResult.tracking_id);
                  setActiveTab("track");
                  handleTrackSearch();
                }}
                className="bg-amber text-base font-bold font-mono text-xs px-3 py-2 rounded shadow transition"
              >
                🔍 Track Status Now
              </button>
            </div>
          </div>

          {/* Tracking ID Hero Box */}
          <div className="bg-base border-2 border-amber/40 p-6 rounded-lg text-center space-y-2 relative">
            <p className="text-xs font-mono text-muted uppercase tracking-widest">OFFICIAL SUBMISSION TRACKING ID</p>
            <p className="font-mono text-3xl md:text-4xl text-amber font-bold tracking-wider selection:bg-amber selection:text-base">
              {submissionResult.tracking_id}
            </p>
            <p className="text-xs text-muted">
              Save this Tracking ID to track status, download receipt, or reference with duty officers.
            </p>
          </div>

          {/* Workflow Status Timeline */}
          <div className="bg-panel2 p-4 rounded-lg border border-line space-y-3">
            <p className="text-xs font-mono text-teal uppercase tracking-wider">Live Workflow Progress</p>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-center text-xs font-mono">
              <div className="p-2 bg-teal/20 border border-teal/40 text-teal rounded font-semibold">
                ✓ 1. Report Filed
              </div>
              <div className="p-2 bg-amber/20 border border-amber/40 text-amber rounded font-semibold animate-pulse">
                ⏳ 2. Pending Verification
              </div>
              <div className="p-2 bg-base border border-line text-muted rounded">
                3. Officer Review
              </div>
              <div className="p-2 bg-base border border-line text-muted rounded">
                4. Case ID & Hotspot Integration
              </div>
            </div>
          </div>

          {/* AI Analysis Initial Finding */}
          {submissionResult.ai_summary && (
            <div className="bg-panel2 p-4 rounded-lg border border-line space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-mono text-amber uppercase tracking-wider flex items-center gap-1">
                  <span>🤖</span> TRACE AI Engine Preliminary Summary
                </p>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-amber/10 text-amber border border-amber/20 font-bold">
                  Priority: {submissionResult.ai_priority?.toUpperCase()}
                </span>
              </div>
              <p className="text-sm text-ink leading-relaxed font-body">
                {submissionResult.ai_summary}
              </p>
            </div>
          )}

          <div className="pt-2 text-center border-t border-line">
            <button
              onClick={() => setSubmissionResult(null)}
              className="text-xs font-mono text-muted hover:text-amber transition underline"
            >
              + Submit Another Crime Report
            </button>
          </div>
        </div>
      )}

      {/* ── TAB 2: TRACK STATUS ───────────────────────────────────────────── */}
      {activeTab === "track" && (
        <div className="bg-panel border border-line rounded-lg p-6 space-y-6 shadow-lg animate-fade-in">
          <div>
            <h2 className="text-sm font-mono text-teal uppercase tracking-wider mb-3">
              Track Crime Report Status
            </h2>
            <form onSubmit={handleTrackSearch} className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="Enter Tracking ID (e.g. TRK-2026-00145)"
                value={trackingIdInput}
                onChange={(e) => setTrackingIdInput(e.target.value)}
                className="flex-1 bg-base border border-line rounded px-4 py-2.5 font-mono text-sm text-ink focus:border-amber focus:outline-none"
              />
              <button
                type="submit"
                disabled={trackingLoading}
                className="bg-amber hover:bg-amber/90 text-base font-mono font-bold text-xs px-6 py-2.5 rounded transition shadow"
              >
                {trackingLoading ? "Searching..." : "LOOKUP TRACKING ID"}
              </button>
            </form>
            <div className="mt-2 flex items-center gap-2 text-xs font-mono text-muted">
              <span>Quick Demo IDs:</span>
              <button
                type="button"
                onClick={() => { setTrackingIdInput("TRK-2026-00145"); }}
                className="text-amber hover:underline"
              >
                TRK-2026-00145
              </button>
              <span>•</span>
              <button
                type="button"
                onClick={() => { setTrackingIdInput("TRK-2026-00146"); }}
                className="text-amber hover:underline"
              >
                TRK-2026-00146
              </button>
            </div>
          </div>

          {trackingError && (
            <div className="p-4 bg-crit/10 border border-crit/30 rounded text-crit text-xs font-mono">
              ⚠️ {trackingError}
            </div>
          )}

          {trackedReport && (
            <div className="space-y-6 pt-4 border-t border-line animate-slide-up">
              {/* Report Header Info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-panel2 p-4 rounded-lg border border-line">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-lg font-bold text-amber">{trackedReport.tracking_id}</span>
                    <span className="text-xs font-mono text-muted">• {trackedReport.crime_type}</span>
                  </div>
                  <p className="text-xs text-muted mt-0.5">Location: {trackedReport.location}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 text-xs font-mono font-bold rounded uppercase tracking-wider ${
                    trackedReport.status === "verified" || trackedReport.status === "approved"
                      ? "bg-teal/20 text-teal border border-teal/40"
                      : trackedReport.status === "rejected"
                      ? "bg-crit/20 text-crit border border-crit/40"
                      : "bg-amber/20 text-amber border border-amber/40 animate-pulse"
                  }`}>
                    Status: {trackedReport.status}
                  </span>
                </div>
              </div>

              {/* Case Integration Notice if Verified */}
              {trackedReport.created_case_id && (
                <div className="p-4 bg-teal/10 border border-teal/30 rounded-lg text-xs font-mono space-y-1">
                  <p className="text-teal font-bold flex items-center gap-2">
                    <span>🎉</span> OFFICIAL CASE GENERATED & INTEGRATED
                  </p>
                  <p className="text-ink">
                    This citizen report was reviewed and approved. Official Case ID:{" "}
                    <span className="text-amber font-bold underline">{trackedReport.created_case_id}</span> has been created in TRACE Engine, Cases Dashboard, and Hotspot Map.
                  </p>
                </div>
              )}

              {/* Rejection Notice if Rejected */}
              {trackedReport.status === "rejected" && (
                <div className="p-4 bg-crit/10 border border-crit/30 rounded-lg text-xs font-mono space-y-1">
                  <p className="text-crit font-bold">❌ REPORT REJECTED AFTER OFFICER REVIEW</p>
                  <p className="text-ink">Reason: {trackedReport.rejection_reason || "Report could not be verified."}</p>
                </div>
              )}

              {/* Description & AI Summary */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-panel2 p-4 rounded-lg border border-line space-y-2">
                  <p className="text-xs font-mono text-teal uppercase">Report Details</p>
                  <p className="text-xs text-ink leading-relaxed">{trackedReport.description}</p>
                  <div className="pt-2 text-[10px] font-mono text-muted border-t border-line">
                    Reporter: {trackedReport.reporter_name} ({trackedReport.reporter_phone})
                  </div>
                </div>

                <div className="bg-panel2 p-4 rounded-lg border border-line space-y-2">
                  <p className="text-xs font-mono text-amber uppercase flex items-center gap-1">
                    <span>🤖</span> AI Priority & Investigation Findings
                  </p>
                  <p className="text-xs text-ink leading-relaxed">
                    {trackedReport.ai_summary || "AI processing in progress."}
                  </p>
                  <div className="pt-2 text-[10px] font-mono text-muted border-t border-line flex justify-between">
                    <span>Priority: {trackedReport.ai_priority?.toUpperCase() || "MEDIUM"}</span>
                    <span>Category: {trackedReport.ai_classification || "Unclassified"}</span>
                  </div>
                </div>
              </div>

              {/* Attached Evidence Items */}
              {trackedReport.evidence_items && trackedReport.evidence_items.length > 0 && (
                <div className="bg-panel2 p-4 rounded-lg border border-line space-y-2">
                  <p className="text-xs font-mono text-teal uppercase">Attached Evidence Files ({trackedReport.evidence_items.length})</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {trackedReport.evidence_items.map((ev, idx) => (
                      <div key={idx} className="bg-base p-2.5 rounded border border-line flex items-center justify-between text-xs font-mono">
                        <span className="truncate text-ink">📁 [{ev.file_type?.toUpperCase()}] {ev.file_name}</span>
                        <span className="text-[10px] text-muted">{new Date(ev.created_at).toLocaleDateString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
