import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { LiveCamera } from "../components/LiveCamera";
import * as api from "../lib/api";
import { ocrBlob, readGps } from "../lib/device";
import { useAuth } from "../state/auth";
import { AppShell } from "../components/AppShell";

type Mode = "idle" | "camera-invoice" | "camera-eway" | "confirm-invoice" | "confirm-eway";

export function DocumentsPage() {
  const { transactionPk: routePk } = useParams();
  const { token, user } = useAuth();
  const [pk, setPk] = useState(routePk || "");
  const [status, setStatus] = useState<api.DocumentStatus | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [detect, setDetect] = useState<api.DocDetectOut | null>(null);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceVehicle, setInvoiceVehicle] = useState("");
  const [gstin, setGstin] = useState("");
  const [ewayNumber, setEwayNumber] = useState("");
  const [ewayVehicle, setEwayVehicle] = useState("");
  const [approvalNote, setApprovalNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const canApprove = Boolean(
    user?.permissions?.includes("approval.act") || user?.permissions?.includes("owner.full"),
  );

  const load = async (id: string) => {
    if (!token || !id) return;
    setLoading(true);
    setError(null);
    try {
      setStatus(await api.documentStatus(token, id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load documents");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (routePk) load(routePk);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routePk, token]);

  if (!token) return null;

  const onOpen = (e: FormEvent) => {
    e.preventDefault();
    if (pk.trim()) load(pk.trim());
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
      if (mode === "camera-eway") {
        const d = await api.detectEway(token, {
          transactionPk: pk,
          gps,
          ocrText: text || " ",
          blob,
          captureSource: source,
        });
        setDetect(d);
        setEwayNumber(d.fields.eway_bill_number || "");
        setEwayVehicle(d.fields.vehicle_number || "");
        setInfo(d.message);
        setMode("confirm-eway");
      } else {
        const d = await api.detectInvoice(token, {
          transactionPk: pk,
          gps,
          ocrText: text || " ",
          blob,
          captureSource: source,
        });
        setDetect(d);
        setInvoiceNumber(d.fields.invoice_number || "");
        setInvoiceVehicle(d.fields.vehicle_number || "");
        setGstin(d.fields.gstin || "");
        setInfo(d.message);
        setMode("confirm-invoice");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Capture failed");
      setMode("idle");
    } finally {
      setLoading(false);
    }
  };

  const confirmInv = async () => {
    if (!detect?.id) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const s = await api.confirmInvoice(token, {
        transaction_pk: pk,
        invoice_id: detect.id,
        gps,
        invoice_number: invoiceNumber || undefined,
        vehicle_number: invoiceVehicle || undefined,
        gstin: gstin || undefined,
      });
      setStatus(s);
      setMode("idle");
      setInfo("Invoice confirmed. Capture E-Way Bill next if still pending.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirm failed");
    } finally {
      setLoading(false);
    }
  };

  const confirmEwb = async () => {
    if (!detect?.id) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const s = await api.confirmEway(token, {
        transaction_pk: pk,
        eway_id: detect.id,
        gps,
        eway_bill_number: ewayNumber || undefined,
        vehicle_number: ewayVehicle || undefined,
      });
      setStatus(s);
      setMode("idle");
      setInfo(
        s.match_status === "MATCH"
          ? "Documents verified — vehicles MATCH."
          : s.match_status === "MISMATCH"
            ? "Vehicle mismatch — owner/supervisor approval required."
            : "E-Way confirmed.",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirm failed");
    } finally {
      setLoading(false);
    }
  };

  const onApprove = async () => {
    if (!status?.verification_id || !approvalNote.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const s = await api.approveMismatch(token, {
        transaction_pk: pk,
        verification_id: status.verification_id,
        approval_note: approvalNote.trim(),
        gps,
      });
      setStatus(s);
      setInfo("Mismatch approved. Documents verified.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval failed");
    } finally {
      setLoading(false);
    }
  };

  if (mode.startsWith("camera-")) {
    return (
      <LiveCamera
        title={mode === "camera-eway" ? "Capture E-Way Bill" : "Capture Invoice"}
        onCapture={onCapture}
        onCancel={() => setMode("idle")}
        allowGallery={canGallery}
      />
    );
  }

  return (
    <AppShell title="Documents" subtitle="Live invoice · E-Way · vehicle match" backTo="/more" wide>
        {!routePk && (
          <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={onOpen}>
            <div className="field">
              <label>Transaction UUID</label>
              <input value={pk} onChange={(e) => setPk(e.target.value)} placeholder="From vehicle entry / weighment" />
            </div>
            <button className="btn btn-primary" type="submit">
              Open documents
            </button>
          </form>
        )}

        {info && (
          <div className="panel" style={{ padding: "1rem" }}>
            {info}
          </div>
        )}
        {error && <div className="err">{error}</div>}
        {loading && <div className="muted">Working…</div>}

        {status && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div>
              <strong>{status.transaction_id}</strong>
              <div className="muted">{status.status}</div>
            </div>
            <div className="grid-cards">
              <div className="stat-card">
                <div className="muted">ANPR</div>
                <strong>{status.anpr_vehicle ?? "—"}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Invoice</div>
                <strong>{status.invoice_vehicle ?? (status.invoice_confirmed ? "OK" : "—")}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">E-Way</div>
                <strong>{status.eway_vehicle ?? (status.eway_confirmed ? "OK" : "—")}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Match</div>
                <strong>{status.match_status ?? "—"}</strong>
              </div>
            </div>
            {status.mismatch_reason && (
              <div className="err" style={{ margin: 0 }}>
                {status.mismatch_reason}
              </div>
            )}
            <div className="action-grid">
              <button className="action-tile" type="button" onClick={() => setMode("camera-invoice")}>
                Capture Invoice
                <span>{status.invoice_confirmed ? "Recapture" : "Live photo + OCR"}</span>
              </button>
              <button className="action-tile" type="button" onClick={() => setMode("camera-eway")}>
                Capture E-Way
                <span>{status.eway_confirmed ? "Recapture" : "Live photo + OCR"}</span>
              </button>
              <button className="action-tile" type="button" onClick={() => load(pk)}>
                Refresh
                <span>Reload status</span>
              </button>
            </div>
            {status.match_status === "MISMATCH" && canApprove && (
              <div className="stack" style={{ marginTop: "0.5rem" }}>
                <div className="field">
                  <label>Approval note (required)</label>
                  <input
                    value={approvalNote}
                    onChange={(e) => setApprovalNote(e.target.value)}
                    placeholder="Why override vehicle mismatch"
                  />
                </div>
                <button className="btn btn-primary" type="button" onClick={onApprove} disabled={!approvalNote.trim()}>
                  Approve mismatch
                </button>
              </div>
            )}
          </div>
        )}

        {mode === "confirm-invoice" && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div className="brand-mark" style={{ fontSize: "1.4rem" }}>
              Confirm invoice
            </div>
            <div className="muted">{detect?.message}</div>
            <div className="field">
              <label>Invoice number</label>
              <input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} />
            </div>
            <div className="field">
              <label>Vehicle on invoice</label>
              <input value={invoiceVehicle} onChange={(e) => setInvoiceVehicle(e.target.value)} />
            </div>
            <div className="field">
              <label>GSTIN</label>
              <input value={gstin} onChange={(e) => setGstin(e.target.value)} />
            </div>
            <button className="btn btn-primary" type="button" onClick={confirmInv}>
              Confirm invoice
            </button>
          </div>
        )}

        {mode === "confirm-eway" && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div className="brand-mark" style={{ fontSize: "1.4rem" }}>
              Confirm E-Way Bill
            </div>
            <div className="muted">{detect?.message}</div>
            <div className="field">
              <label>E-Way Bill number</label>
              <input value={ewayNumber} onChange={(e) => setEwayNumber(e.target.value)} />
            </div>
            <div className="field">
              <label>Vehicle on E-Way</label>
              <input value={ewayVehicle} onChange={(e) => setEwayVehicle(e.target.value)} />
            </div>
            <button className="btn btn-primary" type="button" onClick={confirmEwb}>
              Confirm E-Way
            </button>
          </div>
        )}
      </AppShell>
  );
}
