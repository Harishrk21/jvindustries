import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { LiveCamera } from "../components/LiveCamera";
import * as api from "../lib/api";
import { ocrBlob, readGps } from "../lib/device";
import { useAuth } from "../state/auth";
import { AppShell } from "../components/AppShell";

type Mode = "idle" | "camera-tare" | "camera-gross" | "camera-density" | "confirm-weight" | "confirm-density";

export function WeighmentPage() {
  const { transactionPk: routePk } = useParams();
  const { token, user } = useAuth();
  const [pk, setPk] = useState(routePk || "");
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof api.weighmentSummary>> | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [kind, setKind] = useState<"TARE" | "GROSS">("TARE");
  const [detect, setDetect] = useState<Awaited<ReturnType<typeof api.detectWeighment>> | null>(null);
  const [densDetect, setDensDetect] = useState<Awaited<ReturnType<typeof api.detectDensity>> | null>(null);
  const [weight, setWeight] = useState("");
  const [density, setDensity] = useState("");
  const [temp, setTemp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async (id: string) => {
    if (!token || !id) return;
    setLoading(true);
    setError(null);
    try {
      setSummary(await api.weighmentSummary(token, id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load summary");
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
      if (mode === "camera-density") {
        const d = await api.detectDensity(token, {
          transactionPk: pk,
          gps,
          ocrText: text || " ",
          blob,
          captureSource: source,
        });
        setDensDetect(d);
        setDensity(d.detected_density?.toString() || "");
        setTemp(d.detected_temperature_c?.toString() || "");
        setInfo(d.message);
        setMode("confirm-density");
      } else {
        const k = mode === "camera-gross" ? "GROSS" : "TARE";
        const w = await api.detectWeighment(token, {
          transactionPk: pk,
          kind: k,
          gps,
          ocrText: text || " ",
          blob,
          captureSource: source,
        });
        setKind(k);
        setDetect(w);
        setWeight(w.detected_weight_kg?.toString() || "");
        setInfo(w.message);
        setMode("confirm-weight");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Capture failed");
      setMode("idle");
    } finally {
      setLoading(false);
    }
  };

  const confirmWeight = async () => {
    if (!detect?.photo_id) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const summaryRes = await api.confirmWeighment(token, {
        transaction_pk: pk,
        kind,
        photo_id: detect.photo_id,
        confirmed_weight_kg: Number(weight),
        ocr_weight_kg: detect.detected_weight_kg,
        ocr_confidence: detect.confidence,
        ocr_provider: detect.provider,
        gps,
        after_tare_mode: "LOADING",
      });
      setSummary(summaryRes as Awaited<ReturnType<typeof api.weighmentSummary>>);
      setMode("idle");
      setInfo(`${kind} confirmed. Net is calculated only by the server.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirm failed");
    } finally {
      setLoading(false);
    }
  };

  const confirmDens = async () => {
    if (!densDetect?.photo_id) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      await api.confirmDensity(token, {
        transaction_pk: pk,
        photo_id: densDetect.photo_id,
        confirmed_density: Number(density),
        confirmed_temperature_c: temp ? Number(temp) : null,
        ocr_density: densDetect.detected_density,
        ocr_temperature: densDetect.detected_temperature_c,
        ocr_confidence: densDetect.confidence,
        gps,
      });
      await load(pk);
      setMode("idle");
      setInfo("Density confirmed. Calculated litres are server-authoritative.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Density confirm failed");
    } finally {
      setLoading(false);
    }
  };

  if (mode.startsWith("camera-")) {
    return (
      <LiveCamera
        title={`Capture live ${mode.replace("camera-", "").toUpperCase()}`}
        onCapture={onCapture}
        onCancel={() => setMode("idle")}
        allowGallery={canGallery}
      />
    );
  }

  return (
    <AppShell title="Weighbridge" subtitle="Live TRUWEIGH evidence · server net & litres" backTo="/more" wide>
        {!routePk && (
          <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={onOpen}>
            <div className="field">
              <label>Transaction UUID</label>
              <input value={pk} onChange={(e) => setPk(e.target.value)} placeholder="From vehicle entry screen" />
            </div>
            <button className="btn btn-primary" type="submit">
              Open weighment
            </button>
          </form>
        )}

        {info && <div className="panel" style={{ padding: "1rem" }}>{info}</div>}
        {error && <div className="err">{error}</div>}
        {loading && <div className="muted">Working…</div>}

        {summary && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div>
              <strong>{summary.transaction_id}</strong>
              <div className="muted">{summary.status}</div>
            </div>
            <div className="grid-cards">
              <div className="stat-card">
                <div className="muted">Tare</div>
                <strong style={{ fontSize: "1.5rem" }}>{summary.tare_kg ?? "—"}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Gross</div>
                <strong style={{ fontSize: "1.5rem" }}>{summary.gross_kg ?? "—"}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Net (server)</div>
                <strong style={{ fontSize: "1.5rem" }}>{summary.net_kg ?? "—"}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">{summary.calculated_quantity_label}</div>
                <strong style={{ fontSize: "1.5rem" }}>{summary.calculated_litres ?? "—"} L</strong>
              </div>
            </div>
            <div className="action-grid">
              <button className="action-tile" type="button" onClick={() => setMode("camera-tare")}>
                Capture TARE
                <span>Live display photo</span>
              </button>
              <button className="action-tile" type="button" onClick={() => setMode("camera-gross")}>
                Capture GROSS
                <span>Live display photo</span>
              </button>
              <button className="action-tile" type="button" onClick={() => setMode("camera-density")}>
                Capture DENSITY
                <span>Hydrometer evidence</span>
              </button>
              <button className="action-tile" type="button" onClick={() => load(pk)}>
                Refresh
                <span>Reload server values</span>
              </button>
            </div>
          </div>
        )}

        {mode === "confirm-weight" && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div className="brand-mark" style={{ fontSize: "1.4rem" }}>
              Confirm {kind}
            </div>
            <div>OCR: {detect?.detected_weight_kg ?? "—"} kg</div>
            <div className="field">
              <label>Confirmed weight (kg)</label>
              <input value={weight} onChange={(e) => setWeight(e.target.value)} />
            </div>
            <button className="btn btn-primary" type="button" onClick={confirmWeight}>
              Confirm {kind}
            </button>
          </div>
        )}

        {mode === "confirm-density" && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div className="brand-mark" style={{ fontSize: "1.4rem" }}>
              Confirm density
            </div>
            <div className="field">
              <label>Density kg/L</label>
              <input value={density} onChange={(e) => setDensity(e.target.value)} />
            </div>
            <div className="field">
              <label>Temperature °C</label>
              <input value={temp} onChange={(e) => setTemp(e.target.value)} />
            </div>
            <button className="btn btn-primary" type="button" onClick={confirmDens}>
              Confirm density
            </button>
          </div>
        )}
      </AppShell>
  );
}
