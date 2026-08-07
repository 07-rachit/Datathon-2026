import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../lib/api.js";

export default function Login() {
  const [email, setEmail] = useState("admin@crimeintel.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-base flex flex-col items-center justify-center font-body relative overflow-hidden p-4">
      <div className="absolute inset-0 scanline pointer-events-none" />
      
      <div className="w-full max-w-md relative z-10 space-y-6">
        {/* Main Title Banner */}
        <div className="text-center">
          <p className="font-mono text-teal text-xs tracking-[0.3em] mb-2">CASE-ACCESS-SYS</p>
          <h1 className="font-display text-4xl text-ink tracking-wide">
            CRIME<span className="text-amber">INTEL</span>
          </h1>
          <p className="text-muted text-sm mt-1">Authorized Departmental Access & Public Portal</p>
        </div>

        {/* PUBLIC CITIZEN REPORTING BANNER - No Login Required */}
        <div className="bg-panel border-2 border-amber/40 rounded-lg p-5 shadow-xl space-y-3 relative overflow-hidden group hover:border-amber transition">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs text-amber font-bold uppercase tracking-wider flex items-center gap-1.5">
              <span>📢</span> PUBLIC CITIZEN PORTAL
            </span>
            <span className="text-[10px] font-mono text-teal bg-teal/10 px-2 py-0.5 rounded border border-teal/20">
              No Login Required
            </span>
          </div>

          <p className="text-xs text-ink leading-relaxed">
            Citizens can securely file crime reports, attach evidence (Photos, Video, Audio, CCTV), and track report verification using an official Tracking ID.
          </p>

          <button
            onClick={() => navigate("/report-crime")}
            className="w-full bg-amber hover:bg-amber/90 text-base font-mono font-bold text-xs py-3 rounded shadow-lg transition flex items-center justify-center gap-2 tracking-wide"
          >
            <span>🚨</span> REPORT A CRIME / TRACK STATUS &rarr;
          </button>
        </div>

        {/* OFFICER LOGIN FORM */}
        <form
          onSubmit={handleSubmit}
          className="bg-panel border border-line rounded-lg p-6 space-y-4 shadow-2xl"
        >
          <div className="border-b border-line pb-2 mb-2">
            <h2 className="text-xs font-mono text-muted uppercase tracking-wider">Officer / Admin Access</h2>
          </div>

          <div>
            <label className="block text-xs font-mono text-muted mb-1.5 tracking-wide">EMAIL</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
              placeholder="you@department.gov"
            />
          </div>
          <div>
            <label className="block text-xs font-mono text-muted mb-1.5 tracking-wide">PASSWORD</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-crit text-xs font-mono border border-crit/40 bg-crit/10 rounded px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-panel2 hover:bg-line border border-line text-ink font-mono text-xs font-bold rounded py-2.5 tracking-wide transition disabled:opacity-50"
          >
            {loading ? "AUTHENTICATING..." : "OFFICER SIGN IN"}
          </button>

          <p className="text-center text-muted text-[11px] font-mono pt-1">
            Demo Credentials: <span className="text-amber">admin@crimeintel.local</span> / <span className="text-amber">Admin@123</span>
          </p>
        </form>
      </div>
    </div>
  );
}
