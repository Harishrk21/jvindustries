import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import * as api from "../lib/api";
import { readGps } from "../lib/device";
import { useAuth } from "../state/auth";

type Tab = "search" | "approvals" | "exceptions";

export function InboxPage() {
  const { token } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "search";

  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [results, setResults] = useState<api.TransactionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedPk, setSelectedPk] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<api.TimelineEvent[]>([]);
  const [timelineMeta, setTimelineMeta] = useState<{
    transaction_id: string;
    status: string;
    vehicle_number?: string | null;
  } | null>(null);
  const [approvals, setApprovals] = useState<api.InboxItem[]>([]);
  const [exceptions, setExceptions] = useState<api.InboxItem[]>([]);
  const [note, setNote] = useState("Verified on site");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const setTab = (t: Tab) => {
    const next = new URLSearchParams(params);
    next.set("tab", t);
    setParams(next, { replace: true });
  };

  const runSearch = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.searchTransactions(token, {
        q: q.trim() || undefined,
        status: status || undefined,
        page_size: 30,
      });
      setResults(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const openTimeline = async (pk: string) => {
    if (!token) return;
    setSelectedPk(pk);
    setLoading(true);
    setError(null);
    try {
      const tl = await api.getTimeline(token, pk);
      setTimeline(tl.events);
      setTimelineMeta({
        transaction_id: tl.transaction_id,
        status: tl.status,
        vehicle_number: tl.vehicle_number,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Timeline failed");
    } finally {
      setLoading(false);
    }
  };

  const refreshInbox = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [a, x] = await Promise.all([api.listApprovals(token), api.listExceptions(token)]);
      setApprovals(a.items);
      setExceptions(x.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Inbox failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) return;
    if (tab === "search") runSearch();
    else refreshInbox();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tab]);

  const approveMismatch = async (item: api.InboxItem) => {
    if (!token || !item.transaction_pk) return;
    if (!note.trim()) {
      setError("Approval note is required.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      await api.approveDocumentMismatch(token, {
        transaction_pk: item.transaction_pk,
        verification_id: item.id,
        approval_note: note.trim(),
        gps,
      });
      setInfo(`Approved ${item.transaction_id || item.id}`);
      await refreshInbox();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setLoading(false);
    }
  };

  if (!token) return null;

  return (
    <AppShell title="Search & Inbox" subtitle="Find transactions · timeline · approvals" backTo="/more" wide>
      <div className="seg-tabs" role="tablist">
        {(
          [
            ["search", "Search"],
            ["approvals", "Approvals"],
            ["exceptions", "Exceptions"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            className={tab === id ? "seg-tab active" : "seg-tab"}
            onClick={() => setTab(id)}
          >
            {label}
            {id === "approvals" && approvals.length > 0 ? ` (${approvals.length})` : ""}
            {id === "exceptions" && exceptions.length > 0 ? ` (${exceptions.length})` : ""}
          </button>
        ))}
      </div>

      {error && <div className="err">{error}</div>}
      {info && <div className="ok">{info}</div>}

      {tab === "search" && (
        <>
          <div className="form-row">
            <label>Search</label>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="JV-… / plate / driver"
              onKeyDown={(e) => e.key === "Enter" && runSearch()}
            />
          </div>
          <div className="form-row">
            <label>Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Any</option>
              <option value="APPROVAL_PENDING">APPROVAL_PENDING</option>
              <option value="EXCEPTION">EXCEPTION</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="DOCUMENTS_VERIFIED">DOCUMENTS_VERIFIED</option>
              <option value="EXIT_PENDING">EXIT_PENDING</option>
            </select>
          </div>
          <button type="button" className="btn primary" disabled={loading} onClick={runSearch}>
            Search ({total})
          </button>

          <ul className="inbox-list">
            {results.map((r) => (
              <li key={r.id}>
                <button type="button" className="inbox-item" onClick={() => openTimeline(r.id)}>
                  <strong>{r.transaction_id}</strong>
                  <span>
                    {r.status} · {r.type}
                  </span>
                  <span>{r.vehicle_number || "No plate"} · {r.driver_name || "—"}</span>
                </button>
              </li>
            ))}
          </ul>

          {selectedPk && timelineMeta && (
            <section className="timeline-panel">
              <h3>
                Timeline · {timelineMeta.transaction_id}
                <span className="muted"> · {timelineMeta.status}</span>
              </h3>
              <ol className="timeline">
                {timeline.map((ev) => (
                  <li key={ev.id}>
                    <div className="tl-status">{ev.to_status}</div>
                    <div className="tl-meta">
                      {ev.from_status ? `${ev.from_status} → ` : ""}
                      {ev.reason || "—"}
                    </div>
                    <div className="tl-time">{new Date(ev.created_at).toLocaleString()}</div>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </>
      )}

      {tab === "approvals" && (
        <>
          <button type="button" className="btn" disabled={loading} onClick={refreshInbox}>
            Refresh
          </button>
          <div className="form-row">
            <label>Approval note (for document mismatch)</label>
            <input value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <ul className="inbox-list">
            {approvals.length === 0 && <li className="muted">No pending approvals.</li>}
            {approvals.map((item) => (
              <li key={`${item.kind}-${item.id}`} className="inbox-card">
                <div>
                  <strong>{item.title}</strong>
                  <div className="muted">{item.kind} · {item.status}</div>
                  <div>{item.transaction_id || "—"}</div>
                  <div className="muted">{item.detail}</div>
                </div>
                <div className="inbox-actions">
                  {item.transaction_pk && (
                    <button type="button" className="btn" onClick={() => openTimeline(item.transaction_pk!)}>
                      Timeline
                    </button>
                  )}
                  {item.kind === "DOCUMENT_MISMATCH" && (
                    <button
                      type="button"
                      className="btn primary"
                      disabled={loading}
                      onClick={() => approveMismatch(item)}
                    >
                      Approve
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          {selectedPk && timelineMeta && tab === "approvals" && (
            <section className="timeline-panel">
              <h3>Timeline · {timelineMeta.transaction_id}</h3>
              <ol className="timeline">
                {timeline.map((ev) => (
                  <li key={ev.id}>
                    <div className="tl-status">{ev.to_status}</div>
                    <div className="tl-meta">{ev.reason || "—"}</div>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </>
      )}

      {tab === "exceptions" && (
        <>
          <button type="button" className="btn" disabled={loading} onClick={refreshInbox}>
            Refresh
          </button>
          <ul className="inbox-list">
            {exceptions.length === 0 && <li className="muted">No open exceptions.</li>}
            {exceptions.map((item) => (
              <li key={item.id} className="inbox-card">
                <div>
                  <strong>{item.title}</strong>
                  <div className="muted">{item.status}</div>
                  <div>{item.transaction_id}</div>
                  <div className="muted">{item.detail}</div>
                </div>
                {item.transaction_pk && (
                  <button type="button" className="btn" onClick={() => openTimeline(item.transaction_pk!)}>
                    Timeline
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </AppShell>
  );
}
