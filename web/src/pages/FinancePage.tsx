import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import * as api from "../lib/api";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";

type Tab = "advances" | "settlements" | "gst";

export function FinancePage() {
  const { token } = useAuth();
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("advances");
  const [customers, setCustomers] = useState<api.Party[]>([]);
  const [advances, setAdvances] = useState<api.AdvanceEntry[]>([]);
  const [balances, setBalances] = useState<api.AdvanceBalance[]>([]);
  const [settlements, setSettlements] = useState<api.Settlement[]>([]);
  const [gstResult, setGstResult] = useState<api.GstReconcileResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [customerId, setCustomerId] = useState("");
  const [entryDate, setEntryDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [direction, setDirection] = useState<"PAID" | "RECEIVED_BACK">("PAID");
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");

  const [periodFrom, setPeriodFrom] = useState("2026-03-01");
  const [periodTo, setPeriodTo] = useState("2026-08-31");
  const [feedstock, setFeedstock] = useState("");
  const [delivery, setDelivery] = useState("");
  const [bleach, setBleach] = useState("0");
  const [burner, setBurner] = useState("0");
  const [burnerRate, setBurnerRate] = useState("55");
  const [procRate, setProcRate] = useState("8.4");

  const [gstFrom, setGstFrom] = useState("2026-01-01");
  const [gstTo, setGstTo] = useState(() => new Date().toISOString().slice(0, 10));

  const refresh = async () => {
    if (!token) return;
    const [c, a, b, s] = await Promise.all([
      api.listCustomers(token),
      api.listAdvances(token),
      api.listAdvanceBalances(token),
      api.listSettlements(token),
    ]);
    setCustomers(c);
    setAdvances(a);
    setBalances(b);
    setSettlements(s);
    if (!customerId && c[0]) setCustomerId(c[0].id);
  };

  useEffect(() => {
    if (!token) return;
    void refresh().catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!token) return null;

  const onAdvance = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      await api.createAdvance(token, {
        customer_id: customerId,
        entry_date: entryDate,
        direction,
        amount: Number(amount),
        reference: reference || undefined,
        notes: notes || undefined,
      });
      setAmount("");
      setReference("");
      setNotes("");
      setInfo("Advance saved.");
      toast.success("Advance saved");
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Advance failed";
      setError(msg);
      toast.error("Advance failed", msg);
    } finally {
      setLoading(false);
    }
  };

  const onSettlement = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const row = await api.createSettlement(token, {
        customer_id: customerId,
        period_from: periodFrom,
        period_to: periodTo,
        auto_fill_yard: true,
        feedstock_kg: feedstock ? Number(feedstock) : undefined,
        delivery_kg: delivery ? Number(delivery) : undefined,
        bleaching_return_kg: Number(bleach || 0),
        burner_fuel_kg: Number(burner || 0),
        burner_rate: Number(burnerRate || 0),
        processing_rate_per_kg: Number(procRate || 8.4),
        gst_percent: 18,
      });
      setInfo(`Settlement ${row.report_no} drafted · payable ₹${row.payable.toLocaleString("en-IN")}`);
      toast.success("Settlement drafted", `${row.report_no} · payable ₹${row.payable.toLocaleString("en-IN")}`);
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Settlement failed";
      setError(msg);
      toast.error("Settlement failed", msg);
    } finally {
      setLoading(false);
    }
  };

  const onGst = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const res = await api.reconcileGst(token, gstFrom, gstTo);
      setGstResult(res);
      setInfo(`GST reconcile: ${res.matched}/${res.total} matched · ${res.mismatches} issues`);
      toast.success("GST reconcile done", `${res.matched}/${res.total} matched`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "GST reconcile failed";
      setError(msg);
      toast.error("GST reconcile failed", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="Finance" subtitle="Advances · settlement · GST reconcile" backTo="/more" wide>
      {info && <div className="panel" style={{ padding: "1rem" }}>{info}</div>}
      {error && <div className="err">{error}</div>}
      {loading && <div className="muted">Working…</div>}

      <div className="seg-tabs" role="tablist">
        {(
          [
            ["advances", "Advances"],
            ["settlements", "Settlements"],
            ["gst", "GST reconcile"],
          ] as [Tab, string][]
        ).map(([id, label]) => (
          <button key={id} type="button" className={tab === id ? "seg-tab active" : "seg-tab"} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "advances" && (
        <>
          <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={(e) => void onAdvance(e)}>
            <div className="brand-mark" style={{ fontSize: "1.15rem" }}>Advance ledger</div>
            <div className="field">
              <label>Customer</label>
              <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>{c.code} — {c.name}</option>
                ))}
              </select>
            </div>
            <div className="field"><label>Date</label><input type="date" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} required /></div>
            <div className="field">
              <label>Direction</label>
              <select value={direction} onChange={(e) => setDirection(e.target.value as "PAID" | "RECEIVED_BACK")}>
                <option value="PAID">Paid (to plant / JV)</option>
                <option value="RECEIVED_BACK">Received back</option>
              </select>
            </div>
            <div className="field"><label>Amount ₹</label><input value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" required /></div>
            <div className="field"><label>Reference</label><input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="UTR / cheque" /></div>
            <div className="field"><label>Notes</label><input value={notes} onChange={(e) => setNotes(e.target.value)} /></div>
            <button className="btn btn-primary" type="submit" disabled={loading || !customerId}>Post advance</button>
          </form>

          {balances.length > 0 && (
            <div className="panel" style={{ padding: "1rem", marginTop: "1rem" }}>
              <div className="brand-mark" style={{ fontSize: "1rem" }}>Open balances</div>
              <ul className="stack" style={{ margin: "0.75rem 0 0", padding: 0, listStyle: "none" }}>
                {balances.map((b) => (
                  <li key={b.customer_id} className="muted">
                    {b.customer_code} — paid ₹{b.paid_total.toLocaleString("en-IN")} · back ₹{b.received_back_total.toLocaleString("en-IN")} · bal ₹{b.balance.toLocaleString("en-IN")}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="panel" style={{ padding: "1rem", marginTop: "1rem" }}>
            <div className="brand-mark" style={{ fontSize: "1rem" }}>Recent entries</div>
            <ul className="stack" style={{ margin: "0.75rem 0 0", padding: 0, listStyle: "none" }}>
              {advances.slice(0, 20).map((a) => (
                <li key={a.id} className="muted">
                  {a.entry_date} · {a.direction} · ₹{a.amount.toLocaleString("en-IN")}{a.reference ? ` · ${a.reference}` : ""}
                </li>
              ))}
              {advances.length === 0 && <li className="muted">No advances yet.</li>}
            </ul>
          </div>
        </>
      )}

      {tab === "settlements" && (
        <>
          <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={(e) => void onSettlement(e)}>
            <div className="brand-mark" style={{ fontSize: "1.15rem" }}>Draft settlement</div>
            <p className="muted" style={{ margin: 0 }}>
              Yard delivery kg/trips auto-fill from weighments. Leave feedstock blank to derive from delivery + bleaching + burner.
            </p>
            <div className="field">
              <label>Customer</label>
              <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>{c.code} — {c.name}</option>
                ))}
              </select>
            </div>
            <div className="field"><label>Period from</label><input type="date" value={periodFrom} onChange={(e) => setPeriodFrom(e.target.value)} /></div>
            <div className="field"><label>Period to</label><input type="date" value={periodTo} onChange={(e) => setPeriodTo(e.target.value)} /></div>
            <div className="field"><label>Feedstock kg (optional)</label><input value={feedstock} onChange={(e) => setFeedstock(e.target.value)} /></div>
            <div className="field"><label>Delivery kg (optional)</label><input value={delivery} onChange={(e) => setDelivery(e.target.value)} /></div>
            <div className="field"><label>Bleaching return kg</label><input value={bleach} onChange={(e) => setBleach(e.target.value)} /></div>
            <div className="field"><label>Burner fuel kg</label><input value={burner} onChange={(e) => setBurner(e.target.value)} /></div>
            <div className="field"><label>Burner ₹/kg</label><input value={burnerRate} onChange={(e) => setBurnerRate(e.target.value)} /></div>
            <div className="field"><label>Processing ₹/kg</label><input value={procRate} onChange={(e) => setProcRate(e.target.value)} /></div>
            <button className="btn btn-primary" type="submit" disabled={loading || !customerId}>Create draft</button>
          </form>

          <div className="panel" style={{ padding: "1rem", marginTop: "1rem" }}>
            <div className="brand-mark" style={{ fontSize: "1rem" }}>Settlements</div>
            <ul className="stack" style={{ margin: "0.75rem 0 0", padding: 0, listStyle: "none" }}>
              {settlements.map((s) => (
                <li key={s.id} style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
                  <span className="muted">
                    {s.report_no} · {s.status} · {s.period_from}→{s.period_to} · payable ₹{s.payable.toLocaleString("en-IN")}
                  </span>
                  <button
                    type="button"
                    className="btn"
                    disabled={loading}
                    onClick={() => {
                      void (async () => {
                        setLoading(true);
                        setError(null);
                        try {
                          await api.downloadSettlementSupplyPdf(token, s.id);
                          setInfo(`PDF ${s.report_no} downloaded.`);
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "PDF failed");
                        } finally {
                          setLoading(false);
                        }
                      })();
                    }}
                  >
                    PDF
                  </button>
                  {!s.finalized && (
                    <button
                      type="button"
                      className="btn"
                      disabled={loading}
                      onClick={() => {
                        void (async () => {
                          setLoading(true);
                          setError(null);
                          try {
                            await api.finalizeSettlement(token, s.id);
                            setInfo(`${s.report_no} finalized.`);
                            await refresh();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Finalize failed");
                          } finally {
                            setLoading(false);
                          }
                        })();
                      }}
                    >
                      Finalize
                    </button>
                  )}
                </li>
              ))}
              {settlements.length === 0 && <li className="muted">No settlements yet.</li>}
            </ul>
          </div>
        </>
      )}

      {tab === "gst" && (
        <>
          <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={(e) => void onGst(e)}>
            <div className="brand-mark" style={{ fontSize: "1.15rem" }}>GST invoice reconcile</div>
            <p className="muted" style={{ margin: 0 }}>
              Confirmed invoices vs party master GSTIN for the period.
            </p>
            <div className="field"><label>From</label><input type="date" value={gstFrom} onChange={(e) => setGstFrom(e.target.value)} /></div>
            <div className="field"><label>To</label><input type="date" value={gstTo} onChange={(e) => setGstTo(e.target.value)} /></div>
            <button className="btn btn-primary" type="submit" disabled={loading}>Run reconcile</button>
          </form>
          {gstResult && (
            <div className="panel" style={{ padding: "1rem", marginTop: "1rem" }}>
              <div className="brand-mark" style={{ fontSize: "1rem" }}>
                Run {gstResult.run_id.slice(0, 8)} · {gstResult.matched}/{gstResult.total} matched
              </div>
              <ul className="stack" style={{ margin: "0.75rem 0 0", padding: 0, listStyle: "none" }}>
                {gstResult.rows.slice(0, 40).map((r, i) => (
                  <li key={`${r.invoice_id || i}`} className="muted">
                    {r.match_status} · {r.invoice_number || "—"} · inv {r.invoice_gstin || "—"} / party {r.party_gstin || "—"}
                    {r.detail ? ` · ${r.detail}` : ""}
                  </li>
                ))}
                {gstResult.rows.length === 0 && <li className="muted">No confirmed invoices in range.</li>}
              </ul>
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
