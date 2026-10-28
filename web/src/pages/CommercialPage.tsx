import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import * as api from "../lib/api";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";

type Tab = "supply" | "distillation" | "costing" | "mom";

export function CommercialPage() {
  const { token } = useAuth();
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("supply");
  const [customers, setCustomers] = useState<api.Party[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [customerId, setCustomerId] = useState("");
  const [periodFrom, setPeriodFrom] = useState("2026-03-24");
  const [periodTo, setPeriodTo] = useState("2026-08-20");
  const [feedstock, setFeedstock] = useState("395630");
  const [delivery, setDelivery] = useState("331090");
  const [bleach, setBleach] = useState("24000");
  const [burner, setBurner] = useState("21000");
  const [burnerRate, setBurnerRate] = useState("55");
  const [procRate, setProcRate] = useState("8.4");
  const [advancePaid, setAdvancePaid] = useState("0");
  const [advanceBack, setAdvanceBack] = useState("0");

  const [dFeed, setDFeed] = useState("371630");
  const [dFirst, setDFirst] = useState("180000");
  const [dSecond, setDSecond] = useState("90000");
  const [dBottom, setDBottom] = useState("60000");
  const [dFuel, setDFuel] = useState("20000");

  const [momDate, setMomDate] = useState("2026-10-16");
  const [momObjective, setMomObjective] = useState("Operations, safety & commercial review");
  const [momActions, setMomActions] = useState("Finalize weighing SOP · Commercial Team · 2026-10-30");

  useEffect(() => {
    if (!token) return;
    void api.listCustomers(token).then((c) => {
      setCustomers(c);
      if (c[0]) setCustomerId(c[0].id);
    }).catch(() => undefined);
  }, [token]);

  useEffect(() => {
    if (!token || !customerId) return;
    void api
      .getAdvanceBalance(token, customerId)
      .then((b) => {
        setAdvancePaid(String(b.paid_total));
        setAdvanceBack(String(b.received_back_total));
      })
      .catch(() => {
        setAdvancePaid("0");
        setAdvanceBack("0");
      });
  }, [token, customerId]);

  if (!token) return null;

  const cust = customers.find((c) => c.id === customerId);

  const run = async (e: FormEvent, kind: Tab) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      if (kind === "supply") {
        await api.downloadSupplyExpensePdf(token, {
          customer_id: customerId || undefined,
          customer_name: cust?.name || "SAI PETRO",
          customer_address: cust?.address || undefined,
          report_no: "SE-2026-001",
          period_from: periodFrom,
          period_to: periodTo,
          feedstock_kg: Number(feedstock),
          feedstock_consignments: 12,
          delivery_kg: Number(delivery),
          delivery_trips: 18,
          bleaching_return_kg: Number(bleach),
          burner_fuel_kg: Number(burner),
          burner_rate: Number(burnerRate),
          processing_rate_per_kg: Number(procRate),
          gst_percent: 18,
          advance_paid: Number(advancePaid),
          advance_received_back: Number(advanceBack),
        });
        setInfo("Supply & Expense PDF downloaded.");
        toast.success("PDF ready", "Supply & Expense downloaded.");
      } else if (kind === "distillation") {
        await api.downloadDistillationPdf(token, {
          report_no: "DR-2026-001",
          period_from: periodFrom,
          period_to: periodTo,
          customer_name: cust?.name || "Job-work customer",
          total_feed_kg: Number(dFeed) + Number(bleach || 0),
          bleaching_return_kg: Number(bleach),
          first_cut_kg: Number(dFirst),
          second_cut_kg: Number(dSecond),
          bottom_cut_kg: Number(dBottom),
          boiler_fuel_kg: Number(dFuel),
          vapor_loss_kg: 5000,
          water_loss_kg: 3000,
          processing_rate_per_kg: Number(procRate),
          fuel_cost: 180000,
          power_cost: 45000,
          labour_cost: 60000,
          other_cost: 25000,
          process_days: 12,
        });
        setInfo("Distillation statement PDF downloaded.");
        toast.success("PDF ready", "Distillation statement downloaded.");
      } else if (kind === "costing") {
        await api.downloadCostingPdf(token, {
          batch_size_kg: 60000,
          purchase_lines: [
            { description: "Waste Oil", unit: "kg", quantity: 60000, rate: 45 },
            { description: "LDO / Fuel", unit: "L", quantity: 800, rate: 75 },
          ],
          opex_lines: [
            { description: "Electricity", unit: "kWh", quantity: 1200, rate: 9 },
            { description: "Labour", unit: "day", quantity: 5, rate: 2500 },
            { description: "Maintenance", unit: "ls", quantity: 1, rate: 8000 },
          ],
          option_a_yield_pct: 85,
          option_a_sell_rate: 55,
          option_b_yield_pct: 90,
          option_b_sell_rate: 48,
        });
        setInfo("Costing sheet PDF downloaded.");
        toast.success("PDF ready", "Costing sheet downloaded.");
      } else {
        const actions = momActions
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean)
          .map((line) => {
            const [action, owner, target_date] = line.split("·").map((s) => s.trim());
            return { action: action || line, owner, target_date, status: "Open" };
          });
        await api.downloadMinutesPdf(token, {
          meeting_date: momDate,
          venue: "Conference Room / Plant Site",
          objective: momObjective,
          participants: [
            { name: "Owner Admin", designation: "Owner", organization: "JV Industries" },
            { name: "Plant Supervisor", designation: "Supervisor", organization: "JV Industries" },
          ],
          discussion_points: [
            "Process capacity and batch times",
            "Safety requirements at weighbridge",
            "Market visibility for finished cuts",
          ],
          recommendations: actions.slice(0, 3),
          action_points: actions,
        });
        setInfo("Minutes of Meeting PDF downloaded.");
        toast.success("PDF ready", "Minutes of Meeting downloaded.");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "PDF failed";
      setError(msg);
      toast.error("PDF failed", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="Commercial" subtitle="Supply & Expense · Distillation · Costing · Minutes" backTo="/more" wide>
      {info && <div className="panel" style={{ padding: "1rem" }}>{info}</div>}
      {error && <div className="err">{error}</div>}
      {loading && <div className="muted">Building PDF…</div>}

      <div className="seg-tabs" role="tablist">
        {(
          [
            ["supply", "Supply & Expense"],
            ["distillation", "Distillation"],
            ["costing", "Costing"],
            ["mom", "Minutes"],
          ] as [Tab, string][]
        ).map(([id, label]) => (
          <button key={id} type="button" className={tab === id ? "seg-tab active" : "seg-tab"} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "supply" && (
        <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={(e) => void run(e, "supply")}>
          <div className="brand-mark" style={{ fontSize: "1.15rem" }}>Supply &amp; Expense Accounting</div>
          <div className="field">
            <label>Customer</label>
            <select value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.code} — {c.name}</option>
              ))}
            </select>
          </div>
          <div className="field"><label>Period from</label><input type="date" value={periodFrom} onChange={(e) => setPeriodFrom(e.target.value)} /></div>
          <div className="field"><label>Period to</label><input type="date" value={periodTo} onChange={(e) => setPeriodTo(e.target.value)} /></div>
          <div className="field"><label>Feedstock kg</label><input value={feedstock} onChange={(e) => setFeedstock(e.target.value)} inputMode="decimal" /></div>
          <div className="field"><label>Delivery kg</label><input value={delivery} onChange={(e) => setDelivery(e.target.value)} inputMode="decimal" /></div>
          <div className="field"><label>Bleaching return kg</label><input value={bleach} onChange={(e) => setBleach(e.target.value)} /></div>
          <div className="field"><label>Burner fuel kg</label><input value={burner} onChange={(e) => setBurner(e.target.value)} /></div>
          <div className="field"><label>Burner rate ₹/kg</label><input value={burnerRate} onChange={(e) => setBurnerRate(e.target.value)} /></div>
          <div className="field"><label>Processing ₹/kg</label><input value={procRate} onChange={(e) => setProcRate(e.target.value)} /></div>
          <div className="field"><label>Advance paid ₹</label><input value={advancePaid} onChange={(e) => setAdvancePaid(e.target.value)} /></div>
          <div className="field"><label>Advance received back ₹</label><input value={advanceBack} onChange={(e) => setAdvanceBack(e.target.value)} /></div>
          <p className="muted" style={{ margin: 0 }}>Advances auto-fill from Finance ledger when customer changes.</p>
          <button className="btn btn-primary" type="submit" disabled={loading}>Download PDF</button>
        </form>
      )}

      {tab === "distillation" && (
        <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={(e) => void run(e, "distillation")}>
          <div className="brand-mark" style={{ fontSize: "1.15rem" }}>Distillation Recovery Statement</div>
          <div className="field"><label>Net feed kg</label><input value={dFeed} onChange={(e) => setDFeed(e.target.value)} /></div>
          <div className="field"><label>1st cut kg</label><input value={dFirst} onChange={(e) => setDFirst(e.target.value)} /></div>
          <div className="field"><label>2nd cut kg</label><input value={dSecond} onChange={(e) => setDSecond(e.target.value)} /></div>
          <div className="field"><label>Bottom cut kg</label><input value={dBottom} onChange={(e) => setDBottom(e.target.value)} /></div>
          <div className="field"><label>Boiler fuel kg</label><input value={dFuel} onChange={(e) => setDFuel(e.target.value)} /></div>
          <button className="btn btn-primary" type="submit" disabled={loading}>Download PDF (with charts)</button>
        </form>
      )}

      {tab === "costing" && (
        <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={(e) => void run(e, "costing")}>
          <div className="brand-mark" style={{ fontSize: "1.15rem" }}>Costing Sheet</div>
          <p className="muted" style={{ margin: 0 }}>
            Uses sample purchase + opex lines and two sell-route options (Kerosene vs Waste oil). Edit later in masters if needed.
          </p>
          <button className="btn btn-primary" type="submit" disabled={loading}>Download costing PDF</button>
        </form>
      )}

      {tab === "mom" && (
        <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={(e) => void run(e, "mom")}>
          <div className="brand-mark" style={{ fontSize: "1.15rem" }}>Minutes of Meeting</div>
          <div className="field"><label>Date</label><input type="date" value={momDate} onChange={(e) => setMomDate(e.target.value)} /></div>
          <div className="field"><label>Objective</label><input value={momObjective} onChange={(e) => setMomObjective(e.target.value)} /></div>
          <div className="field">
            <label>Action points (one per line: action · owner · date)</label>
            <textarea rows={4} value={momActions} onChange={(e) => setMomActions(e.target.value)} />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading}>Download MoM PDF</button>
        </form>
      )}
    </AppShell>
  );
}
