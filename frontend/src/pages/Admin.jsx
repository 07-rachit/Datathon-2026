import { useEffect, useState } from "react";
import { listUsers, createUser, updateUser, deactivateUser } from "../lib/api.js";
import { getCurrentUser } from "../lib/api.js";

const ROLES = ["viewer", "investigator", "analyst", "admin"];

const ROLE_COLOR = {
  admin: "text-crit border-crit/40",
  analyst: "text-amber border-amber/40",
  investigator: "text-teal border-teal/40",
  viewer: "text-muted border-line",
};

function Badge({ role }) {
  return (
    <span
      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${ROLE_COLOR[role] || "text-muted border-line"}`}
    >
      {role}
    </span>
  );
}

function InviteModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "viewer" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const user = await createUser(form);
      onCreated(user);
      onClose();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create user.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-panel border border-line rounded-lg w-[440px] p-6 shadow-2xl">
        <p className="font-mono text-teal text-[10px] tracking-[0.25em] mb-1">ADMIN · CREATE ACCOUNT</p>
        <h3 className="font-display text-xl text-ink mb-5">Invite New User</h3>
        {error && (
          <p className="text-crit text-xs font-mono border border-crit/40 bg-crit/10 rounded px-3 py-2 mb-4">
            {error}
          </p>
        )}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-muted text-xs font-mono uppercase block mb-1">Full Name</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
              placeholder="Inspector Sharma"
            />
          </div>
          <div>
            <label className="text-muted text-xs font-mono uppercase block mb-1">Email</label>
            <input
              required
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
              placeholder="officer@district.gov.in"
            />
          </div>
          <div>
            <label className="text-muted text-xs font-mono uppercase block mb-1">
              Password <span className="normal-case">(min 8 chars)</span>
            </label>
            <input
              required
              type="password"
              minLength={8}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
              placeholder="••••••••"
            />
          </div>
          <div>
            <label className="text-muted text-xs font-mono uppercase block mb-1">Role</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="text-sm font-mono text-muted hover:text-ink transition px-4 py-2 border border-line rounded"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="bg-amber text-base font-semibold text-sm px-5 py-2 rounded hover:brightness-110 transition disabled:opacity-50"
            >
              {saving ? "Creating…" : "Create User"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function UserRow({ user, currentUserId, onUpdate, onDeactivate }) {
  const [roleValue, setRoleValue] = useState(user.role);
  const [saving, setSaving] = useState(false);
  const isSelf = user.id === currentUserId;

  async function handleRoleChange(newRole) {
    setRoleValue(newRole);
    setSaving(true);
    try {
      const updated = await updateUser(user.id, { role: newRole });
      onUpdate(updated);
    } catch {
      setRoleValue(user.role); // revert
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate() {
    if (!window.confirm(`Deactivate ${user.email}? They will no longer be able to log in.`)) return;
    try {
      await deactivateUser(user.id);
      onDeactivate(user.id);
    } catch (err) {
      alert(err?.response?.data?.detail || "Could not deactivate user.");
    }
  }

  return (
    <tr className="border-t border-line hover:bg-panel2/40 transition">
      <td className="px-4 py-3">
        <p className="text-ink text-sm">{user.name}</p>
        <p className="text-muted text-xs font-mono">{user.email}</p>
      </td>
      <td className="px-4 py-3">
        {isSelf ? (
          <Badge role={user.role} />
        ) : (
          <select
            value={roleValue}
            disabled={saving}
            onChange={(e) => handleRoleChange(e.target.value)}
            className="bg-panel border border-line rounded px-2 py-1 text-xs font-mono text-ink focus:outline-none focus:ring-1 focus:ring-teal disabled:opacity-50"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        )}
      </td>
      <td className="px-4 py-3">
        <span
          className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
            user.is_active ? "text-teal border-teal/40" : "text-muted border-line"
          }`}
        >
          {user.is_active ? "active" : "inactive"}
        </span>
      </td>
      <td className="px-4 py-3 text-muted text-xs font-mono">
        {new Date(user.created_at).toLocaleDateString("en-IN", {
          day: "2-digit",
          month: "short",
          year: "numeric",
        })}
      </td>
      <td className="px-4 py-3 text-right">
        {!isSelf && user.is_active && (
          <button
            onClick={handleDeactivate}
            className="text-xs font-mono text-muted hover:text-crit transition"
          >
            Deactivate
          </button>
        )}
        {isSelf && <span className="text-xs font-mono text-muted/50">you</span>}
        {!user.is_active && <span className="text-xs font-mono text-muted/40">—</span>}
      </td>
    </tr>
  );
}

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const currentUser = getCurrentUser();

  useEffect(() => {
    listUsers()
      .then(setUsers)
      .catch(() => setError("Could not load users. Are you logged in as admin?"))
      .finally(() => setLoading(false));
  }, []);

  function handleUpdate(updated) {
    setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
  }

  function handleDeactivate(userId) {
    setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, is_active: false } : u)));
  }

  function handleCreated(user) {
    setUsers((prev) => [user, ...prev]);
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">SYSTEM · ADMIN ONLY</p>
          <h2 className="font-display text-3xl text-ink">User Management</h2>
        </div>
        <button
          onClick={() => setShowInvite(true)}
          className="bg-amber text-base font-semibold text-sm px-5 py-2.5 rounded hover:brightness-110 transition flex items-center gap-2"
        >
          <span className="text-base font-mono text-lg leading-none">+</span> Invite User
        </button>
      </div>

      {error && (
        <p className="text-crit text-sm font-mono border border-crit/40 bg-crit/10 rounded px-4 py-3 mb-6">
          {error}
        </p>
      )}

      <div className="bg-panel border border-line rounded-md overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-line">
              <th className="text-left px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                User
              </th>
              <th className="text-left px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                Role
              </th>
              <th className="text-left px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                Status
              </th>
              <th className="text-left px-4 py-3 text-muted text-xs font-mono uppercase tracking-wide">
                Created
              </th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted text-sm">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted text-sm">
                  No users found.
                </td>
              </tr>
            )}
            {users.map((u) => (
              <UserRow
                key={u.id}
                user={u}
                currentUserId={currentUser?.id}
                onUpdate={handleUpdate}
                onDeactivate={handleDeactivate}
              />
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-muted text-xs font-mono">
        {users.filter((u) => u.is_active).length} active ·{" "}
        {users.filter((u) => !u.is_active).length} inactive
      </p>

      {showInvite && (
        <InviteModal onClose={() => setShowInvite(false)} onCreated={handleCreated} />
      )}
    </div>
  );
}
