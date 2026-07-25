import { useState } from "react";
import { importCasesCSV } from "../lib/api.js";

export default function Import() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function handleFileChange(e) {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError("");
    }
  }

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await importCasesCSV(file);
      setResult(res);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to import CSV file.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">DATA INGESTION · BULK IMPORT</p>
          <h2 className="font-display text-3xl text-ink">Bulk Case Import</h2>
        </div>
        <a
          href="/api/import/cases/csv/template"
          download="case_import_template.csv"
          className="text-xs font-mono text-teal border border-teal/40 hover:bg-teal/10 rounded px-4 py-2 transition inline-flex items-center gap-1.5"
        >
          <span>↓</span> Download CSV Template
        </a>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-panel border border-line rounded-md p-6">
          <h3 className="font-display text-xl text-ink mb-2">Upload CSV</h3>
          <p className="text-muted text-xs font-body mb-4">
            Upload a spreadsheet containing crime case records. Existing case IDs will be skipped automatically.
          </p>

          {error && (
            <p className="text-crit text-xs font-mono border border-crit/40 bg-crit/10 rounded px-3 py-2 mb-4">
              {error}
            </p>
          )}

          <form onSubmit={handleUpload} className="space-y-4">
            <div className="border-2 border-dashed border-line hover:border-teal rounded-lg p-6 text-center cursor-pointer transition">
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="hidden"
                id="csv-upload"
              />
              <label htmlFor="csv-upload" className="cursor-pointer block">
                <p className="text-ink font-mono text-sm mb-1">
                  {file ? file.name : "Select CSV File"}
                </p>
                <p className="text-muted text-xs font-mono">
                  {file ? `${(file.size / 1024).toFixed(1)} KB` : "Click to browse or drag file here"}
                </p>
              </label>
            </div>

            <button
              type="submit"
              disabled={!file || loading}
              className="w-full bg-amber text-base font-semibold text-sm py-2.5 rounded hover:brightness-110 transition disabled:opacity-50"
            >
              {loading ? "Importing Cases..." : "Start Import"}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-line">
            <p className="text-muted text-xs font-mono uppercase mb-2">Required Columns:</p>
            <ul className="text-xs font-mono text-muted space-y-1 list-disc list-inside">
              <li>case_id</li>
              <li>title</li>
              <li>crime_type</li>
              <li>district</li>
              <li>station_name</li>
              <li>status (open/closed/under_review)</li>
              <li>severity (low/medium/high/critical)</li>
              <li>incident_date (YYYY-MM-DD)</li>
            </ul>
          </div>
        </div>

        <div className="lg:col-span-2 bg-panel border border-line rounded-md p-6">
          <h3 className="font-display text-xl text-ink mb-4">Import Results</h3>

          {!result && !loading && (
            <div className="h-64 flex items-center justify-center border border-line/40 rounded bg-panel2/30">
              <p className="text-muted text-xs font-mono">No import operation run yet.</p>
            </div>
          )}

          {loading && (
            <div className="h-64 flex flex-col items-center justify-center border border-line/40 rounded bg-panel2/30">
              <div className="w-8 h-8 border-2 border-teal border-t-transparent rounded-full animate-spin mb-3"></div>
              <p className="text-ink text-sm font-mono">Processing rows and rebuilding RAG index...</p>
            </div>
          )}

          {result && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-panel2 border border-teal/40 rounded p-4">
                  <p className="text-muted text-xs font-mono uppercase mb-1">Cases Successfully Imported</p>
                  <p className="text-teal font-display text-3xl">{result.imported}</p>
                </div>
                <div className="bg-panel2 border border-line rounded p-4">
                  <p className="text-muted text-xs font-mono uppercase mb-1">Rows Skipped</p>
                  <p className="text-amber font-display text-3xl">{result.skipped.length}</p>
                </div>
              </div>

              {result.skipped.length > 0 && (
                <div>
                  <h4 className="text-ink font-display text-base mb-2">Skipped Rows Log</h4>
                  <div className="border border-line rounded overflow-hidden max-h-60 overflow-y-auto">
                    <table className="w-full text-xs font-mono">
                      <thead className="bg-panel2 border-b border-line sticky top-0">
                        <tr>
                          <th className="text-left px-3 py-2 text-muted">Row #</th>
                          <th className="text-left px-3 py-2 text-muted">Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.skipped.map((s, i) => (
                          <tr key={i} className="border-b border-line/40 hover:bg-panel2/50">
                            <td className="px-3 py-2 text-amber font-mono">{s.row}</td>
                            <td className="px-3 py-2 text-muted">{s.reason}</td>
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
      </div>
    </div>
  );
}
