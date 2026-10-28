import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import * as api from "../lib/api";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";

export function ChangePasswordPage() {
  const { token, user, setUser, logout } = useAuth();
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  if (!token) return <Navigate to="/login" replace />;
  if (user && !user.must_change_password && !info) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (next !== confirm) {
      setError("New passwords do not match.");
      return;
    }
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const updated = await api.changePassword(token, current, next);
      setUser(updated);
      setInfo("Password updated. Continuing…");
      toast.success("Password updated", "Continuing to home…");
      setCurrent("");
      setNext("");
      setConfirm("");
      setTimeout(() => {
        window.location.assign("/");
      }, 600);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Change failed";
      setError(msg);
      toast.error("Could not update password", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="Change password" subtitle="Required before yard operations" wide>
      {user?.must_change_password && (
        <div className="panel" style={{ padding: "1rem" }}>
          Seed / reset password detected for <strong>{user.user_code}</strong>. Set a personal password to continue.
        </div>
      )}
      {info && <div className="panel" style={{ padding: "1rem" }}>{info}</div>}
      {error && <div className="err">{error}</div>}
      <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={(e) => void onSubmit(e)}>
        <div className="field">
          <label>Current password</label>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required autoComplete="current-password" />
        </div>
        <div className="field">
          <label>New password (min 8)</label>
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={8} autoComplete="new-password" />
        </div>
        <div className="field">
          <label>Confirm new password</label>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} autoComplete="new-password" />
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Saving…" : "Update password"}
        </button>
        <button className="btn" type="button" onClick={() => logout()}>
          Sign out
        </button>
      </form>
    </AppShell>
  );
}
