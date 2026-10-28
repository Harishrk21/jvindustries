import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { useAuth } from "../state/auth";
import { AppShell } from "../components/AppShell";

export function AlertsPage() {
  const { token } = useAuth();
  const [notes, setNotes] = useState<api.AppNotification[]>([]);
  const [msgs, setMsgs] = useState<api.WhatsappMsg[]>([]);
  const [txnPk, setTxnPk] = useState("");
  const [title, setTitle] = useState("Yard attention");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [n, m] = await Promise.all([api.listNotifications(token), api.listWhatsappMessages(token)]);
      setNotes(n);
      setMsgs(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!token) return null;

  const onMark = async (id: string) => {
    await api.markNotificationRead(token, id);
    await refresh();
  };

  const onAlert = async () => {
    if (!body.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.sendManualAlert(token, { title, body: body.trim(), severity: "WARN" });
      setBody("");
      setInfo("Alert created (WhatsApp mock/inbox logged).");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Alert failed");
    } finally {
      setLoading(false);
    }
  };

  const onPdf = async (kind: "customer" | "internal" | "gate-pass") => {
    if (!txnPk.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const id = txnPk.trim();
      const path =
        kind === "gate-pass"
          ? `/api/v1/pdfs/gate-pass/${id}`
          : `/api/v1/pdfs/transaction/${id}?variant=${kind}`;
      await api.downloadPdf(token, path, `${kind}-${id.slice(0, 8)}.pdf`);
      setInfo(`${kind} PDF downloaded.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF download failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="Alerts & PDFs" subtitle="WhatsApp log · management inbox · downloads" backTo="/more" wide>
        {info && (
          <div className="panel" style={{ padding: "1rem" }}>
            {info}
          </div>
        )}
        {error && <div className="err">{error}</div>}
        {loading && <div className="muted">Working…</div>}

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Download PDF
          </div>
          <div className="field">
            <label>Transaction UUID</label>
            <input value={txnPk} onChange={(e) => setTxnPk(e.target.value)} placeholder="From gate / job-work" />
          </div>
          <div className="action-grid">
            <button className="action-tile" type="button" onClick={() => onPdf("customer")}>
              Customer PDF
              <span>Delivery · weighment slip</span>
            </button>
            <button className="action-tile" type="button" onClick={() => onPdf("internal")}>
              Internal PDF
              <span>Audit · stock flags</span>
            </button>
            <button className="action-tile" type="button" onClick={() => onPdf("gate-pass")}>
              Gate pass PDF
              <span>Needs gate pass first</span>
            </button>
          </div>
        </div>

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Send management alert
          </div>
          <div className="field">
            <label>Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="field">
            <label>Body</label>
            <input value={body} onChange={(e) => setBody(e.target.value)} placeholder="What needs attention" />
          </div>
          <button className="btn btn-primary" type="button" onClick={onAlert}>
            Create alert
          </button>
        </div>

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Inbox
          </div>
          <button className="btn btn-ghost" type="button" onClick={refresh}>
            Refresh
          </button>
          {notes.length === 0 && <div className="muted">No alerts yet.</div>}
          {notes.map((n) => (
            <div key={n.id} className="stat-card" style={{ textAlign: "left" }}>
              <div className="muted">
                {n.severity} · {n.category}
                {n.is_read ? "" : " · NEW"}
              </div>
              <strong>{n.title}</strong>
              <div>{n.body}</div>
              <div className="muted">
                {n.transaction_id || "—"} · WA {n.whatsapp_sent ? "sent" : "inbox"}
              </div>
              {!n.is_read && (
                <button className="btn btn-ghost" type="button" style={{ marginTop: "0.5rem" }} onClick={() => onMark(n.id)}>
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            WhatsApp messages
          </div>
          {msgs.slice(0, 10).map((m) => (
            <div key={m.id} className="muted">
              {m.template_name} → {m.to_mobile} · {m.delivery_status} · {m.provider}
            </div>
          ))}
        </div>
      </AppShell>
  );
}
