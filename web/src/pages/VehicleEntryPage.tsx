import { useState } from "react";
import { Link } from "react-router-dom";
import { LiveCamera } from "../components/LiveCamera";
import * as api from "../lib/api";
import { ocrBlob, readGps } from "../lib/device";
import { useAuth } from "../state/auth";
import { AppShell } from "../components/AppShell";

type Step = "start" | "camera" | "confirm" | "driver" | "gate" | "done";

export function VehicleEntryPage() {
  const { token, user } = useAuth();
  const [step, setStep] = useState<Step>("start");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [txn, setTxn] = useState<{ id: string; transaction_id: string; status: string } | null>(null);
  const [anpr, setAnpr] = useState<Awaited<ReturnType<typeof api.runAnpr>> | null>(null);
  const [plate, setPlate] = useState("");
  const [reason, setReason] = useState("");
  const [driverName, setDriverName] = useState("");
  const [driverMobile, setDriverMobile] = useState("");
  const [transporter, setTransporter] = useState("");
  const [gatePass, setGatePass] = useState<string | null>(null);

  if (!token) return null;

  const start = async () => {
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const created = await api.startEntry(token, gps);
      setTxn(created);
      setInfo("GPS verified. Capture a live vehicle photograph.");
      setStep("camera");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to start entry");
    } finally {
      setLoading(false);
    }
  };

  const canGallery =
    !!user?.permissions?.includes("photo.gallery") || !!user?.permissions?.includes("owner.full");

  const onCapture = async (blob: Blob, source: api.CaptureSource = "LIVE_CAMERA") => {
    if (!txn) return;
    setLoading(true);
    setError(null);
    setInfo(source === "OWNER_GALLERY_UPLOAD" ? "Running OCR on gallery photograph…" : "Running OCR on live photograph…");
    try {
      const gps = await readGps();
      const text = await ocrBlob(blob);
      const result = await api.runAnpr(token, {
        transactionPk: txn.id,
        gps,
        ocrText: text || " ",
        blob,
        captureSource: source,
      });
      setAnpr(result);
      setPlate(result.vehicle_number || "");
      setInfo(result.message || "Confirm detected plate.");
      setStep("confirm");
    } catch (e) {
      setError(e instanceof Error ? e.message : "ANPR failed");
      setStep("camera");
    } finally {
      setLoading(false);
    }
  };

  const confirm = async () => {
    if (!txn || !anpr) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const manual =
        plate.trim().toUpperCase() !== (anpr.vehicle_number || "").trim().toUpperCase() || anpr.status === "FAILED";
      await api.confirmAnpr(token, {
        transaction_pk: txn.id,
        anpr_result_id: anpr.id,
        vehicle_number: plate || undefined,
        manual_reason: manual ? reason || undefined : undefined,
        gps,
      });
      setStep("driver");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirm failed");
    } finally {
      setLoading(false);
    }
  };

  const saveDriver = async () => {
    if (!txn) return;
    setLoading(true);
    setError(null);
    try {
      await api.saveDriver(token, {
        transaction_pk: txn.id,
        driver_name: driverName,
        driver_mobile: driverMobile,
        transporter_name: transporter || undefined,
      });
      setStep("gate");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Driver save failed");
    } finally {
      setLoading(false);
    }
  };

  const makeGatePass = async () => {
    if (!txn) return;
    setLoading(true);
    setError(null);
    try {
      const gp = await api.createGatePass(token, txn.id);
      setGatePass(gp.gate_pass_number);
      setStep("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gate pass failed");
    } finally {
      setLoading(false);
    }
  };

  if (step === "camera") {
    return (
      <LiveCamera
        onCapture={onCapture}
        onCancel={() => setStep("start")}
        title="Capture live vehicle photo"
        allowGallery={canGallery}
      />
    );
  }

  return (
    <AppShell
      title="Vehicle Entry"
      subtitle={txn ? `${txn.transaction_id} · ${txn.status}` : "New inbound / loading movement"}
      backTo="/"
      wide
    >
        {info && <div className="panel" style={{ padding: "1rem" }}>{info}</div>}
        {error && <div className="err">{error}</div>}
        {loading && <div className="muted">Working…</div>}

        {step === "start" && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <p className="muted" style={{ margin: 0 }}>
              Starts a real transaction with device GPS geofence checks and live-camera evidence only.
            </p>
            <button className="btn btn-primary" type="button" disabled={loading} onClick={start}>
              Start entry
            </button>
          </div>
        )}

        {step === "confirm" && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div className="brand-mark" style={{ fontSize: "1.4rem" }}>
              Detected data
            </div>
            <div>Plate: {anpr?.vehicle_number || "—"}</div>
            <div>Confidence: {Math.round((anpr?.confidence || 0) * 100)}%</div>
            <div className="muted">Provider: {anpr?.provider}</div>
            <div className="field">
              <label>Confirm / manual plate</label>
              <input value={plate} onChange={(e) => setPlate(e.target.value)} />
            </div>
            <div className="field">
              <label>Manual reason (required if override / OCR fail)</label>
              <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
            </div>
            <button className="btn btn-primary" type="button" disabled={loading} onClick={confirm}>
              Confirm
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => setStep("camera")}>
              Retake
            </button>
          </div>
        )}

        {step === "driver" && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div className="field">
              <label>Driver name</label>
              <input value={driverName} onChange={(e) => setDriverName(e.target.value)} />
            </div>
            <div className="field">
              <label>Driver mobile</label>
              <input value={driverMobile} onChange={(e) => setDriverMobile(e.target.value)} />
            </div>
            <div className="field">
              <label>Transporter</label>
              <input value={transporter} onChange={(e) => setTransporter(e.target.value)} />
            </div>
            <button className="btn btn-primary" type="button" disabled={loading} onClick={saveDriver}>
              Save driver
            </button>
          </div>
        )}

        {step === "gate" && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <p className="muted" style={{ margin: 0 }}>
              Generate an inward gate pass linked to this Transaction ID.
            </p>
            <button className="btn btn-primary" type="button" disabled={loading} onClick={makeGatePass}>
              Generate gate pass
            </button>
            {txn && (
              <Link className="btn btn-dark" to={`/weighment/${txn.id}`}>
                Continue to weighment
              </Link>
            )}
          </div>
        )}

        {step === "done" && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div className="brand-mark" style={{ fontSize: "1.6rem" }}>
              Gate pass ready
            </div>
            <div>{gatePass}</div>
            <div className="muted">{txn?.transaction_id}</div>
            {txn && (
              <Link className="btn btn-primary" to={`/weighment/${txn.id}`}>
                Open weighment
              </Link>
            )}
            <Link className="btn btn-ghost" to="/">
              Dashboard
            </Link>
          </div>
        )}
      </AppShell>
  );
}
