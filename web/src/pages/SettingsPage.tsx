import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import * as api from "../lib/api";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";

export function SettingsPage() {
  const { token, user, setUser } = useAuth();
  const toast = useToast();
  const canEdit =
    !!user?.permissions?.includes("config.geofence") || !!user?.permissions?.includes("owner.full");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [radius, setRadius] = useState("");
  const [accuracy, setAccuracy] = useState("");
  const [source, setSource] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwLoading, setPwLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    api
      .getGeofenceConfig(token)
      .then((c) => {
        setLat(String(c.lat));
        setLon(String(c.lon));
        setRadius(String(c.radius_m));
        setAccuracy(String(c.max_accuracy_m));
        setSource(c.source);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load geofence"));
  }, [token]);

  if (!token) return null;

  const onSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!canEdit) return;
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const c = await api.putGeofenceConfig(token, {
        lat: Number(lat),
        lon: Number(lon),
        radius_m: Number(radius),
        max_accuracy_m: Number(accuracy),
      });
      setSource(c.source);
      setInfo("Geofence saved. New checks use these coordinates.");
      toast.success("Geofence saved", "New yard checks use these coordinates.");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Save failed";
      setError(msg);
      toast.error("Could not save geofence", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="Settings" subtitle="Geofence · yard location" backTo="/more" wide>
      {info && (
        <div className="panel" style={{ padding: "1rem" }}>
          {info}
        </div>
      )}
      {error && <div className="err">{error}</div>}

      <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={onSave}>
        <div className="brand-mark" style={{ fontSize: "1.2rem" }}>
          Yard geofence
        </div>
        <p className="muted" style={{ margin: 0, fontSize: "0.85rem" }}>
          Source: {source || "…"} · Circle around JV premises. Operators must be inside for critical ops.
        </p>
        <div className="field">
          <label>Latitude</label>
          <input value={lat} onChange={(e) => setLat(e.target.value)} required disabled={!canEdit} />
        </div>
        <div className="field">
          <label>Longitude</label>
          <input value={lon} onChange={(e) => setLon(e.target.value)} required disabled={!canEdit} />
        </div>
        <div className="field">
          <label>Radius (metres)</label>
          <input value={radius} onChange={(e) => setRadius(e.target.value)} required disabled={!canEdit} />
        </div>
        <div className="field">
          <label>Max GPS accuracy (metres)</label>
          <input value={accuracy} onChange={(e) => setAccuracy(e.target.value)} required disabled={!canEdit} />
        </div>
        {canEdit ? (
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Saving…" : "Save geofence"}
          </button>
        ) : (
          <div className="muted">View only — need config.geofence to edit.</div>
        )}
      </form>

      <form
        className="panel stack"
        style={{ padding: "1.25rem", marginTop: "1rem" }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!token) return;
          if (newPw !== confirmPw) {
            setError("New passwords do not match.");
            toast.error("Passwords do not match");
            return;
          }
          setPwLoading(true);
          setError(null);
          setInfo(null);
          void api
            .changePassword(token, curPw, newPw)
            .then((u) => {
              setUser(u);
              setCurPw("");
              setNewPw("");
              setConfirmPw("");
              setInfo("Password updated.");
              toast.success("Password updated");
            })
            .catch((err) => {
              const msg = err instanceof Error ? err.message : "Password change failed";
              setError(msg);
              toast.error("Password change failed", msg);
            })
            .finally(() => setPwLoading(false));
        }}
      >
        <div className="brand-mark" style={{ fontSize: "1.2rem" }}>
          Change password
        </div>
        <p className="muted" style={{ margin: 0, fontSize: "0.85rem" }}>
          Signed in as {user?.user_code}. Change seed defaults before production day-1.
        </p>
        <div className="field">
          <label>Current password</label>
          <input type="password" value={curPw} onChange={(e) => setCurPw(e.target.value)} required autoComplete="current-password" />
        </div>
        <div className="field">
          <label>New password</label>
          <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} required minLength={8} autoComplete="new-password" />
        </div>
        <div className="field">
          <label>Confirm new password</label>
          <input type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} required minLength={8} autoComplete="new-password" />
        </div>
        <button className="btn btn-primary" type="submit" disabled={pwLoading}>
          {pwLoading ? "Updating…" : "Update password"}
        </button>
      </form>
    </AppShell>
  );
}
