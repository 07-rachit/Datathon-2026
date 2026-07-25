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
    <div className="min-h-screen bg-base flex items-center justify-center font-body relative overflow-hidden">
      <div className="absolute inset-0 scanline pointer-events-none" />
      <div className="w-full max-w-sm relative z-10">
        <div className="text-center mb-8">
          <p className="font-mono text-teal text-xs tracking-[0.3em] mb-2">CASE-ACCESS-SYS</p>
          <h1 className="font-display text-4xl text-ink tracking-wide">
            CRIME<span className="text-amber">INTEL</span>
          </h1>
          <p className="text-muted text-sm mt-1">Restricted access &mdash; authorized personnel only</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-panel border border-line rounded-md p-6 space-y-4 shadow-2xl"
        >
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
            className="w-full bg-amber text-base font-semibold rounded py-2.5 text-sm tracking-wide hover:brightness-110 transition disabled:opacity-50"
          >
            {loading ? "AUTHENTICATING..." : "SIGN IN"}
          </button>
        </form>

        <p className="text-center text-muted text-xs mt-4 font-mono">
          demo: admin@crimeintel.local / Admin@123
        </p>
      </div>
    </div>
  );
}
