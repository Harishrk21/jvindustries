import { useCallback, useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import * as api from "../lib/api";
import {
  clearSyncedDrafts,
  enqueueOfflineDraft,
  listOfflineDrafts,
  markDraftConflict,
  removeOfflineDraft,
  type OfflineDraft,
} from "../lib/offlineQueue";
import { useAuth } from "../state/auth";

export function OfflinePage() {
  const { token } = useAuth();
  const [drafts, setDrafts] = useState<OfflineDraft[]>([]);
  const [online, setOnline] = useState(typeof navigator !== "undefined" ? navigator.onLine : true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [rules, setRules] = useState<string[]>([]);
  const [type, setType] = useState("MATERIAL_LOADING_OUTWARD");
  const [notes, setNotes] = useState("");

  const refresh = useCallback(() => setDrafts(listOfflineDrafts()), []);

  useEffect(() => {
    refresh();
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, [refresh]);

  useEffect(() => {
    if (!token) return;
    api
      .syncPolicy(token)
      .then((p) => setRules(p.rules))
      .catch(() => setRules([]));
  }, [token]);

  function queueDraft() {
    enqueueOfflineDraft({ type, notes: notes.trim() || undefined });
    setNotes("");
    setMsg("Draft queued on this device.");
    setErr(null);
    refresh();
  }

  async function pushAll() {
    if (!token) return;
    const pending = listOfflineDrafts().filter((d) => !d.conflict);
    if (!pending.length) {
      setMsg("Nothing to sync.");
      return;
    }
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const res = await api.syncPush(
        token,
        pending.map((d) => ({
          client_transaction_id: d.client_transaction_id,
          type: d.type,
          notes: d.notes,
          device_id: d.device_id,
          gps: d.gps,
          queued_at: d.queued_at,
        })),
      );
      const okIds: string[] = [];
      for (const r of res.results) {
        if (r.outcome === "CREATED" || r.outcome === "IDEMPOTENT") {
          okIds.push(r.client_transaction_id);
        } else if (r.outcome === "CONFLICT") {
          markDraftConflict(r.client_transaction_id, r.message, r.transaction_id || undefined);
        }
      }
      clearSyncedDrafts(okIds);
      refresh();
      setMsg(
        `Sync done — accepted ${res.accepted}, conflicts ${res.conflicts}, errors ${res.errors}.`,
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Sync failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      title="Offline queue"
      subtitle={online ? "Online — ready to sync" : "Offline — drafts stay on device"}
      backTo="/more"
      wide
    >
      {msg && (
        <div className="panel" style={{ padding: "1rem" }}>
          {msg}
        </div>
      )}
      {err && <div className="err">{err}</div>}

      <section className="panel stack" style={{ padding: "1.25rem" }}>
        <div className="brand-mark" style={{ fontSize: "1.15rem" }}>
          Queue a draft
        </div>
        <p className="muted" style={{ margin: 0, fontSize: "0.85rem" }}>
          Use when the network is down. Sync pushes with the same client id (idempotent).
        </p>
        <div className="field">
          <label>Type</label>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="MATERIAL_LOADING_OUTWARD">Material loading (out)</option>
            <option value="MATERIAL_RECEIVING_INWARD">Material receiving (in)</option>
            <option value="JOB_WORK">Job work</option>
            <option value="OTHER_MOVEMENT">Other movement</option>
          </select>
        </div>
        <div className="field">
          <label>Notes (optional)</label>
          <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Gate note…" />
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button type="button" className="btn btn-dark" onClick={queueDraft}>
            Save offline
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy || !online || !drafts.some((d) => !d.conflict)}
            onClick={() => void pushAll()}
          >
            {busy ? "Syncing…" : "Sync now"}
          </button>
        </div>
      </section>

      <section className="stack">
        <div className="brand-mark" style={{ fontSize: "1.15rem" }}>
          Queued ({drafts.length})
        </div>
        {!drafts.length && <p className="muted">No offline drafts.</p>}
        {drafts.map((d) => (
          <article key={d.client_transaction_id} className="panel stack" style={{ padding: "1rem", gap: "0.35rem" }}>
            <div style={{ fontWeight: 600 }}>{d.type.replace(/_/g, " ")}</div>
            <div className="muted" style={{ fontSize: "0.78rem", wordBreak: "break-all" }}>
              {d.client_transaction_id}
            </div>
            <div className="muted" style={{ fontSize: "0.78rem" }}>
              Queued {new Date(d.queued_at).toLocaleString()}
            </div>
            {d.notes && <div style={{ fontSize: "0.9rem" }}>{d.notes}</div>}
            {d.conflict && (
              <div className="err">
                Conflict: {d.last_error}
                {d.server_transaction_id ? ` (${d.server_transaction_id})` : ""}
              </div>
            )}
            <button
              type="button"
              className="btn btn-ghost"
              style={{ alignSelf: "flex-start" }}
              onClick={() => {
                removeOfflineDraft(d.client_transaction_id);
                refresh();
              }}
            >
              Discard
            </button>
          </article>
        ))}
      </section>

      {!!rules.length && (
        <section className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.15rem" }}>
            Conflict policy
          </div>
          <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.85rem" }}>
            {rules.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      )}
    </AppShell>
  );
}
