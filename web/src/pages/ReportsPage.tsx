import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { useAuth } from "../state/auth";
import { AppShell } from "../components/AppShell";

type View = "operations" | api.OpsReportKind;

const OPS_TABS: { id: View; label: string }[] = [
  { id: "operations", label: "Operations" },
  { id: "stock", label: "Month stock" },
  { id: "tank", label: "Tank-wise" },
  { id: "customer", label: "Customer" },
  { id: "jobwork", label: "Job-work" },
  { id: "audit", label: "Audit" },
];

export function ReportsPage() {
  const { token } = useAuth();
  const [view, setView] = useState<View>("operations");
  const [period, setPeriod] = useState<"daily" | "monthly" | "custom">("monthly");
  const [dateFrom, setDateFrom] = useState("2026-10-01");
  const [dateTo, setDateTo] = useState("2026-10-28");
  const [summary, setSummary] = useState<api.ReportSummary | null>(null);
  const [ops, setOps] = useState<api.OpsReport | null>(null);
  const [exports, setExports] = useState<api.ReportExportMeta[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const periodParams = () =>
    period === "custom" ? { period, date_from: dateFrom, date_to: dateTo } : { period };

  const load = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const params = periodParams();
      if (view === "operations") {
        const [s, e] = await Promise.all([api.reportSummary(token, params), api.listReportExports(token)]);
        setSummary(s);
        setOps(null);
        setExports(e);
      } else {
        const [o, e] = await Promise.all([
          api.opsReport(token, view, view === "tank" ? { period: "monthly" } : params),
          api.listReportExports(token),
        ]);
        setOps(o);
        setSummary(null);
        setExports(e);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, period, view]);

  if (!token) return null;

  const doExport = async (format: "pdf" | "xlsx" | "csv") => {
    setLoading(true);
    setError(null);
    try {
      const params = { ...periodParams(), format };
      if (view === "operations") {
        await api.exportReport(token, params);
      } else {
        await api.exportOpsReport(token, view, view === "tank" ? { period: "monthly", format } : params);
      }
      setInfo(`${format.toUpperCase()} downloaded.`);
      setExports(await api.listReportExports(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="Reports" subtitle="Operations · stock · tank · customer · job-work · audit" backTo="/more" wide>
      {info && (
        <div className="panel" style={{ padding: "1rem" }}>
          {info}
        </div>
      )}
      {error && <div className="err">{error}</div>}
      {loading && <div className="muted">Working…</div>}

      <div className="seg-tabs" role="tablist">
        {OPS_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={view === t.id ? "seg-tab active" : "seg-tab"}
            onClick={() => setView(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="panel stack" style={{ padding: "1.25rem" }}>
        {view !== "tank" && (
          <>
            <div className="field">
              <label>Period</label>
              <select value={period} onChange={(e) => setPeriod(e.target.value as typeof period)}>
                <option value="daily">Daily (today)</option>
                <option value="monthly">Monthly (this month)</option>
                <option value="custom">Custom range</option>
              </select>
            </div>
            {period === "custom" && (
              <>
                <div className="field">
                  <label>From</label>
                  <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
                </div>
                <div className="field">
                  <label>To</label>
                  <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
                </div>
                <button className="btn btn-ghost" type="button" onClick={() => void load()}>
                  Apply range
                </button>
              </>
            )}
          </>
        )}

        {view === "operations" && summary && (
          <>
            <div className="muted">
              {summary.title} · {summary.date_from} → {summary.date_to}
            </div>
            <div className="grid-cards">
              <div className="stat-card">
                <div className="muted">Transactions</div>
                <strong style={{ fontSize: "1.4rem" }}>{summary.summary.transactions ?? 0}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Net kg</div>
                <strong style={{ fontSize: "1.4rem" }}>{summary.summary.net_kg_total ?? 0}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Litres</div>
                <strong style={{ fontSize: "1.4rem" }}>{summary.summary.litres_total ?? 0}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Rows</div>
                <strong style={{ fontSize: "1.4rem" }}>{summary.row_count}</strong>
              </div>
            </div>
          </>
        )}

        {ops && (
          <>
            <div className="muted">
              {ops.title} · {ops.date_from} → {ops.date_to} · {ops.row_count} rows
            </div>
            <div className="grid-cards">
              {Object.entries(ops.summary).slice(0, 4).map(([k, v]) => (
                <div className="stat-card" key={k}>
                  <div className="muted">{k.replace(/_/g, " ")}</div>
                  <strong style={{ fontSize: "1.2rem" }}>{String(v)}</strong>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="action-grid">
          <button className="action-tile" type="button" onClick={() => void doExport("pdf")}>
            Export PDF
            <span>Share-ready</span>
          </button>
          <button className="action-tile" type="button" onClick={() => void doExport("xlsx")}>
            Export Excel
            <span>.xlsx</span>
          </button>
          <button className="action-tile" type="button" onClick={() => void doExport("csv")}>
            Export CSV
            <span>Raw rows</span>
          </button>
        </div>
      </div>

      {view === "operations" && summary && summary.sample_rows.length > 0 && (
        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Sample rows
          </div>
          {summary.sample_rows.slice(0, 8).map((r) => (
            <div key={r.transaction_id} className="muted">
              {r.transaction_id} · {r.type} · {r.status} · {r.vehicle_number}
            </div>
          ))}
        </div>
      )}

      {ops && ops.rows.length > 0 && (
        <div className="panel stack" style={{ padding: "1.25rem", overflowX: "auto" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Data
          </div>
          <table className="report-table">
            <thead>
              <tr>
                {ops.columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ops.rows.slice(0, 40).map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {ops.rows.length > 40 && <div className="muted">Showing first 40 of {ops.rows.length} — export for full file.</div>}
        </div>
      )}

      {ops && ops.rows.length === 0 && (
        <div className="panel" style={{ padding: "1.25rem" }}>
          <div className="muted">No rows for this period yet.</div>
        </div>
      )}

      <div className="panel stack" style={{ padding: "1.25rem" }}>
        <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
          Recent exports
        </div>
        {exports.length === 0 && <div className="muted">No exports yet.</div>}
        {exports.slice(0, 10).map((e) => (
          <div key={e.id} className="muted">
            {e.file_name} · {e.row_count} rows · {e.format}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
