import { useEffect, useState } from "react";
import { LiveCamera } from "../components/LiveCamera";
import * as api from "../lib/api";
import { ocrBlob, readGps } from "../lib/device";
import { useAuth } from "../state/auth";
import { AppShell } from "../components/AppShell";

type Mode = "idle" | "camera" | "confirm";

export function CanteenPage() {
  const { token, user } = useAuth();
  const [balances, setBalances] = useState<api.CanteenBalance[]>([]);
  const [pk, setPk] = useState("");
  const [txnCode, setTxnCode] = useState("");
  const [mode, setMode] = useState<Mode>("idle");
  const [detect, setDetect] = useState<api.CanteenDetect | null>(null);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [supplier, setSupplier] = useState("");
  const [lines, setLines] = useState<api.CanteenLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    if (!token) return;
    setBalances(await api.canteenBalances(token));
  };

  useEffect(() => {
    if (!token) return;
    refresh().catch((e) => setError(e instanceof Error ? e.message : "Load failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!token) return null;

  const start = async () => {
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const s = await api.startCanteenPurchase(token, gps);
      setPk(s.id);
      setTxnCode(s.transaction_id);
      setInfo(`Purchase ${s.transaction_id} started — capture invoice.`);
      setMode("camera");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Start failed");
    } finally {
      setLoading(false);
    }
  };

  const canGallery =
    !!user?.permissions?.includes("photo.gallery") || !!user?.permissions?.includes("owner.full");

  const onCapture = async (blob: Blob, source: api.CaptureSource = "LIVE_CAMERA") => {
    if (!pk) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const text = await ocrBlob(blob);
      const d = await api.detectCanteenPurchase(token, {
        transactionPk: pk,
        gps,
        ocrText: text || " ",
        blob,
        captureSource: source,
      });
      setDetect(d);
      setInvoiceNumber(d.invoice_number || "");
      setSupplier(d.supplier_name || "");
      setLines(d.lines);
      setInfo(d.message);
      setMode("confirm");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Capture failed");
      setMode("idle");
    } finally {
      setLoading(false);
    }
  };

  const confirm = async () => {
    if (!detect || !pk) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const c = await api.confirmCanteenPurchase(token, {
        purchase_id: detect.purchase_id,
        transaction_pk: pk,
        gps,
        invoice_number: invoiceNumber || undefined,
        supplier_name: supplier || undefined,
        lines,
      });
      setInfo(`Confirmed ${c.transaction_id}. Stock posted. Photo retained.`);
      setMode("idle");
      setDetect(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirm failed");
    } finally {
      setLoading(false);
    }
  };

  const updateLineQty = (idx: number, qty: string) => {
    setLines((prev) => prev.map((ln, i) => (i === idx ? { ...ln, quantity: Number(qty) || 0 } : ln)));
  };

  if (mode === "camera") {
    return (
      <LiveCamera
        title="Capture canteen invoice"
        onCapture={onCapture}
        onCancel={() => setMode("idle")}
        allowGallery={canGallery}
      />
    );
  }

  return (
    <AppShell title="Canteen" subtitle="Purchase OCR · confirm · stock" backTo="/more" wide>
        {info && (
          <div className="panel" style={{ padding: "1rem" }}>
            {info}
          </div>
        )}
        {error && <div className="err">{error}</div>}
        {loading && <div className="muted">Working…</div>}

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Stock balances
          </div>
          <div className="grid-cards">
            {balances.map((b) => (
              <div className="stat-card" key={b.item_id}>
                <div className="muted">{b.item_name}</div>
                <strong style={{ fontSize: "1.35rem" }}>
                  {b.quantity.toLocaleString()} {b.unit}
                </strong>
              </div>
            ))}
          </div>
          <button className="btn btn-primary" type="button" onClick={start}>
            New purchase (live camera)
          </button>
          {txnCode && <div className="muted">Active: {txnCode}</div>}
        </div>

        {mode === "confirm" && detect && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
              Confirm OCR lines
            </div>
            <div className="field">
              <label>Invoice number</label>
              <input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} />
            </div>
            <div className="field">
              <label>Supplier</label>
              <input value={supplier} onChange={(e) => setSupplier(e.target.value)} />
            </div>
            {lines.map((ln, idx) => (
              <div className="field" key={`${ln.item_code}-${idx}`}>
                <label>
                  {ln.item_name} ({ln.item_code}) — {ln.unit}
                </label>
                <input
                  value={String(ln.quantity)}
                  onChange={(e) => updateLineQty(idx, e.target.value)}
                />
              </div>
            ))}
            <button className="btn btn-primary" type="button" onClick={confirm} disabled={!lines.length}>
              Confirm & post stock
            </button>
          </div>
        )}
      </AppShell>
  );
}
