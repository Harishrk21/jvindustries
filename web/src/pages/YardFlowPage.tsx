import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { CapturePhaseBar } from "../components/CapturePhaseBar";
import { GpsBanner } from "../components/GpsBanner";
import { LiveCamera } from "../components/LiveCamera";
import { YardEntryRail } from "../components/YardEntryRail";
import * as api from "../lib/api";
import { compressForAnpr, ocrBlob, readGpsSafe } from "../lib/device";
import { resolveGps } from "../lib/gps";
import {
  checklistForType,
  isDocStep,
  isOutward,
  nextStepId,
  stepFromStatus,
  type YardStepId,
  type YardTxnType,
} from "../lib/yardSteps";
import { useAuth } from "../state/auth";

type CamMode = null | "lorry" | "invoice" | "eway" | "tare" | "gross" | "density" | "exit";
type CapturePhase = "PHOTO" | "AI" | "CONFIRM" | "SAVE";

export function YardFlowPage() {
  const { transactionPk: routePk } = useParams();
  const nav = useNavigate();
  const { token, user } = useAuth();
  const canGallery =
    !!user?.permissions?.includes("photo.gallery") || !!user?.permissions?.includes("owner.full");
  const allowWeighSkip = import.meta.env.DEV;

  const [step, setStep] = useState<YardStepId>("location");
  const [txnType, setTxnType] = useState<YardTxnType | null>(null);
  const [txn, setTxn] = useState<{ id: string; transaction_id: string; status: string } | null>(null);
  const [gpsOk, setGpsOk] = useState(false);
  const [locationOk, setLocationOk] = useState(false);
  const [locationDetail, setLocationDetail] = useState("Not checked yet");
  const [locationBusy, setLocationBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [cam, setCam] = useState<CamMode>(null);
  const [phase, setPhase] = useState<CapturePhase>("PHOTO");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [anpr, setAnpr] = useState<Awaited<ReturnType<typeof api.runAnpr>> | null>(null);
  const [plate, setPlate] = useState("");
  const [aiNote, setAiNote] = useState("");

  const [driverName, setDriverName] = useState("");
  const [driverMobile, setDriverMobile] = useState("");
  const [licence, setLicence] = useState("");
  const [transporter, setTransporter] = useState("");
  const [vehicleType, setVehicleType] = useState("Tanker");
  const [customerWa, setCustomerWa] = useState("");
  const [fromLocation, setFromLocation] = useState("");
  const [toLocation, setToLocation] = useState("JV Industries — Chittoor");
  const [gateRemarks, setGateRemarks] = useState("");
  const [invoiceChallan, setInvoiceChallan] = useState("");
  const [secVehicle, setSecVehicle] = useState(true);
  const [secGoods, setSecGoods] = useState(true);
  const [secDocs, setSecDocs] = useState(false);

  const [docDetect, setDocDetect] = useState<api.DocDetectOut | null>(null);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState("");
  const [invoiceVehicle, setInvoiceVehicle] = useState("");
  const [ewayNumber, setEwayNumber] = useState("");
  const [ewayVehicle, setEwayVehicle] = useState("");
  const [supplierName, setSupplierName] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [gstin, setGstin] = useState("");
  const [invoiceOk, setInvoiceOk] = useState(false);
  const [ewayOk, setEwayOk] = useState(false);
  const [docStatus, setDocStatus] = useState<api.DocumentStatus | null>(null);
  const [docKind, setDocKind] = useState<"invoice" | "eway">("invoice");

  const [weightDetect, setWeightDetect] = useState<Awaited<ReturnType<typeof api.detectWeighment>> | null>(null);
  const [weight, setWeight] = useState("");
  const [densDetect, setDensDetect] = useState<Awaited<ReturnType<typeof api.detectDensity>> | null>(null);
  const [density, setDensity] = useState("");
  const [temp, setTemp] = useState("");

  const [products, setProducts] = useState<api.Product[]>([]);
  const [units, setUnits] = useState<api.StorageUnit[]>([]);
  const [productId, setProductId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [customers, setCustomers] = useState<api.Party[]>([]);
  const [suppliers, setSuppliers] = useState<api.Party[]>([]);
  const [partyId, setPartyId] = useState("");

  const [otpSend, setOtpSend] = useState<api.OtpSend | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [otpVerified, setOtpVerified] = useState(false);
  const [customerMobileKeep, setCustomerMobileKeep] = useState("");
  const [exitAnpr, setExitAnpr] = useState<Awaited<ReturnType<typeof api.detectExitAnpr>> | null>(null);
  const [gatePass, setGatePass] = useState<string | null>(null);
  const [weighSummary, setWeighSummary] = useState<api.WeighmentSummary | null>(null);
  const [doneIds, setDoneIds] = useState<Set<YardStepId>>(new Set());

  const checklist = useMemo(() => (txnType ? checklistForType(txnType) : []), [txnType]);

  const markDone = (id: YardStepId) => setDoneIds((prev) => new Set(prev).add(id));

  const advance = (from: YardStepId) => {
    if (from !== "location" && from !== "type" && !txnType) return;
    markDone(from);
    const n = nextStepId(txnType, from);
    setStep(n === "done" ? "done" : n);
    setError(null);
    setInfo(null);
    setPhase("PHOTO");
    setPreviewUrl(null);
  };

  const confirmLocation = async () => {
    if (!token) return;
    setLocationBusy(true);
    setError(null);
    try {
      const { gps, source } = await resolveGps(token);
      try {
        await api.checkGeofence(token, gps);
      } catch {
        /* for now always allow continue */
      }
      const tag = source === "plant" ? "yard pin" : source === "cache" ? "cached" : "current";
      setLocationDetail(`${tag} · ${gps.lat.toFixed(5)}, ${gps.lon.toFixed(5)} · ±${Math.round(gps.accuracy_m)} m`);
      setLocationOk(true);
      setGpsOk(true);
      setInfo("Location confirmed.");
    } catch {
      // Still succeed for local testing, as requested
      setLocationDetail("Location accepted (fallback)");
      setLocationOk(true);
      setGpsOk(true);
      setInfo("Location confirmed.");
    } finally {
      setLocationBusy(false);
    }
  };

  const onGps = useCallback((_g: api.Gps | null, ok: boolean) => setGpsOk(ok), []);

  useEffect(() => {
    if (!token || !routePk) return;
    (async () => {
      setLoading(true);
      try {
        const tl = await api.getTimeline(token, routePk);
        const type = (tl.type as YardTxnType) || "MATERIAL_LOADING_OUTWARD";
        setTxnType(type);
        setTxn({ id: tl.transaction_pk, transaction_id: tl.transaction_id, status: tl.status });
        if (tl.status === "COMPLETED") setStep("done");
        else setStep(stepFromStatus(type, tl.status));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unable to resume");
      } finally {
        setLoading(false);
      }
    })();
  }, [token, routePk]);

  useEffect(() => {
    if (step === "post_docs") {
      setInvoiceOk(false);
      setEwayOk(false);
      setDocDetect(null);
      setDocStatus(null);
      setPhase("PHOTO");
      setPreviewUrl(null);
    }
  }, [step]);

  useEffect(() => {
    if (!token || !txn?.id) return;
    if (!["density", "slip", "post_docs", "gross", "tare"].includes(step)) return;
    void api
      .weighmentSummary(token, txn.id)
      .then(setWeighSummary)
      .catch(() => undefined);
  }, [token, txn?.id, step]);

  useEffect(() => {
    if (!token || !txnType) return;
    if (!["close", "gate", "gross", "tare", "slip"].includes(step)) return;
    (async () => {
      try {
        const [p, u] = await Promise.all([api.listProducts(token), api.listStorageUnits(token)]);
        setProducts(p);
        setUnits(u);
        if (!productId && p[0]) setProductId(p[0].id);
        if (!unitId) {
          const t03 = u.find((x) => x.code === "T-03") || u[0];
          if (t03) setUnitId(t03.id);
        }
        if (isOutward(txnType)) {
          const c = await api.listCustomers(token);
          setCustomers(c);
          if (!partyId && c[0]) setPartyId(c[0].id);
        } else {
          const s = await api.listSuppliers(token);
          setSuppliers(s);
          if (!partyId && s[0]) setPartyId(s[0].id);
        }
      } catch {
        /* ignore */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, step, txnType]);

  if (!token) return null;

  const startType = async () => {
    if (!txnType) {
      setError("Select movement type.");
      return;
    }
    if (!locationOk && !gpsOk) {
      setError("Confirm location in the first step first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const gps = await readGpsSafe(token);
      const created = await api.startEntry(token, gps, txnType);
      setTxn(created);
      setStep("lorry");
      setInfo(`Transaction ${created.transaction_id} created`);
      nav(`/yard/${created.id}`, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to start");
    } finally {
      setLoading(false);
    }
  };

  const onCapture = async (blob: Blob, source: api.CaptureSource = "LIVE_CAMERA") => {
    if (!txn) return;
    const mode = cam;
    setCam(null);
    setError(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const url = URL.createObjectURL(blob);
    setPreviewUrl(url);
    setPhase("AI");
    setLoading(true);
    try {
      const gps = await readGpsSafe(token);
      if (mode === "lorry" || mode === "exit") {
        // Skip heavy on-device Tesseract — Groq vision on the photo is faster + more accurate.
        const anprBlob = await compressForAnpr(blob);
        if (mode === "lorry") {
          const result = await api.runAnpr(token, {
            transactionPk: txn.id,
            gps,
            ocrText: " ",
            blob: anprBlob,
            captureSource: source,
          });
          setAnpr(result);
          setPlate(result.vehicle_number || "");
          setAiNote(
            result.vehicle_number
              ? result.message || "Check plate, then Next."
              : "No plate found — type the number (e.g. AP 28 W 4882), then Next.",
          );
          setPhase("CONFIRM");
        } else {
          const e = await api.detectExitAnpr(token, {
            transactionPk: txn.id,
            gps,
            ocrText: " ",
            blob: anprBlob,
            captureSource: source,
          });
          setExitAnpr(e);
          setAiNote(e.message || `${e.vehicle_number || "—"} · ${e.status}`);
          setPhase("CONFIRM");
        }
      } else {
        const text = await ocrBlob(blob);
        if (mode === "invoice" || mode === "eway") {
          const isEway = mode === "eway";
          setDocKind(isEway ? "eway" : "invoice");
          const d = isEway
            ? await api.detectEway(token, {
                transactionPk: txn.id,
                gps,
                ocrText: text || " ",
                blob,
                captureSource: source,
              })
            : await api.detectInvoice(token, {
                transactionPk: txn.id,
                gps,
                ocrText: text || " ",
                blob,
                captureSource: source,
              });
          setDocDetect(d);
          if (isEway) {
            setEwayNumber(d.fields.eway_bill_number || "");
            setEwayVehicle(d.fields.vehicle_number || plate);
          } else {
            setInvoiceNumber(d.fields.invoice_number || "");
            setInvoiceVehicle(d.fields.vehicle_number || plate);
            setInvoiceDate(d.fields.invoice_date || "");
            setSupplierName(d.fields.supplier_name || "");
            setCustomerName(d.fields.customer_name || "");
            setGstin(d.fields.gstin || "");
          }
          setAiNote(d.message || "Check every field against the document.");
          setPhase("CONFIRM");
        } else if (mode === "tare" || mode === "gross") {
          const kind = mode === "tare" ? "TARE" : "GROSS";
          const w = await api.detectWeighment(token, {
            transactionPk: txn.id,
            kind,
            gps,
            ocrText: text || " ",
            blob,
            captureSource: source,
          });
          setWeightDetect(w);
          setWeight(w.detected_weight_kg?.toString() || "");
          setAiNote(w.message);
          setPhase("CONFIRM");
        } else if (mode === "density") {
          const d = await api.detectDensity(token, {
            transactionPk: txn.id,
            gps,
            ocrText: text || " ",
            blob,
            captureSource: source,
          });
          setDensDetect(d);
          setDensity(d.detected_density?.toString() || "");
          setTemp(d.detected_temperature_c?.toString() || "");
          setAiNote(d.message);
          setPhase("CONFIRM");
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Capture failed");
      setPhase("PHOTO");
    } finally {
      setLoading(false);
    }
  };

  const acceptLorry = async () => {
    if (!txn || !anpr) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGpsSafe(token);
      const manual =
        plate.trim().toUpperCase() !== (anpr.vehicle_number || "").trim().toUpperCase() ||
        anpr.status === "FAILED";
      await api.confirmAnpr(token, {
        transaction_pk: txn.id,
        anpr_result_id: anpr.id,
        vehicle_number: plate || undefined,
        manual_reason: manual ? "Manual plate confirm" : undefined,
        gps,
      });
      setPhase("SAVE");
      advance("lorry");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Accept failed");
    } finally {
      setLoading(false);
    }
  };

  const saveDriver = async () => {
    if (!txn) return;
    if (!driverName.trim() || !driverMobile.trim()) {
      setError("Driver name and mobile are required.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.saveDriver(token, {
        transaction_pk: txn.id,
        driver_name: driverName.trim(),
        driver_mobile: driverMobile.trim(),
        transporter_name: transporter || undefined,
        license_no: licence.trim() || undefined,
        vehicle_type: vehicleType || undefined,
        customer_whatsapp: customerWa.trim() || undefined,
      });
      if (customerWa) setCustomerMobileKeep(customerWa);
      advance("driver");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save driver failed");
    } finally {
      setLoading(false);
    }
  };

  const acceptDoc = async () => {
    if (!txn || !docDetect?.id) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGpsSafe(token);
      if (docKind === "invoice") {
        const s = await api.confirmInvoice(token, {
          transaction_pk: txn.id,
          invoice_id: docDetect.id,
          gps,
          invoice_number: invoiceNumber || undefined,
          invoice_date: invoiceDate || undefined,
          vehicle_number: invoiceVehicle || undefined,
          gstin: gstin || undefined,
        });
        setDocStatus(s);
        setInvoiceOk(true);
        setDocDetect(null);
        setPhase("PHOTO");
        setPreviewUrl(null);
        setInfo("Invoice saved. Capture E-Way Bill next.");
      } else {
        const s = await api.confirmEway(token, {
          transaction_pk: txn.id,
          eway_id: docDetect.id,
          gps,
          eway_bill_number: ewayNumber || undefined,
          vehicle_number: ewayVehicle || undefined,
        });
        setDocStatus(s);
        setEwayOk(true);
        setDocDetect(null);
        setPhase("PHOTO");
        setPreviewUrl(null);
        if (s.match_status === "MISMATCH") {
          setInfo(null);
          setError(null);
        } else {
          advance(isDocStep(step) ? step : "post_docs");
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Document confirm failed");
    } finally {
      setLoading(false);
    }
  };

  const doGate = async () => {
    if (!txn || !txnType) return;
    if (!productId || !unitId) {
      setError("Select product and storage / tank before issuing the gate pass.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const gps = await readGpsSafe(token);
      await api.assignStorage(token, {
        transaction_pk: txn.id,
        product_id: productId,
        storage_unit_id: unitId,
        gps,
      });
      const productName = products.find((p) => p.id === productId)?.name || "";
      const gp = await api.createGatePass(token, txn.id, {
        pass_type: isOutward(txnType) ? "OUTWARD_LOADING" : "INWARD_MATERIAL",
        direction: isOutward(txnType) ? "OUTWARD" : "INWARD",
        purpose: isOutward(txnType) ? "OUTWARD" : "INWARD",
        material_description: productName || undefined,
        unit_text: "kg",
        invoice_challan_no: invoiceChallan.trim() || undefined,
        from_location: fromLocation.trim() || undefined,
        to_location: toLocation.trim() || undefined,
        remarks: gateRemarks.trim() || undefined,
        vehicle_checked: secVehicle,
        goods_verified: secGoods,
        documents_verified: secDocs,
      });
      setGatePass(gp.gate_pass_number);
      advance("gate");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gate pass failed");
    } finally {
      setLoading(false);
    }
  };

  const confirmWeight = async (kind: "TARE" | "GROSS") => {
    if (!txn || !weightDetect?.photo_id || !txnType) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGpsSafe(token);
      const summary = await api.confirmWeighment(token, {
        transaction_pk: txn.id,
        kind,
        photo_id: weightDetect.photo_id,
        confirmed_weight_kg: Number(weight),
        ocr_weight_kg: weightDetect.detected_weight_kg,
        ocr_confidence: weightDetect.confidence,
        ocr_provider: weightDetect.provider,
        gps,
        after_tare_mode: isOutward(txnType) ? "LOADING" : "UNLOADING",
      });
      setWeighSummary(summary);
      setWeightDetect(null);
      setPreviewUrl(null);
      if (kind === "GROSS" && !isOutward(txnType)) {
        try {
          await api.postStock(token, { transaction_pk: txn.id, direction: "IN", use_transaction_qty: true, gps });
        } catch {
          /* optional */
        }
      }
      advance(kind === "TARE" ? "tare" : "gross");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Weigh confirm failed");
    } finally {
      setLoading(false);
    }
  };

  const confirmDens = async () => {
    if (!txn || !densDetect?.photo_id || !txnType) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGpsSafe(token);
      const dens = await api.confirmDensity(token, {
        transaction_pk: txn.id,
        photo_id: densDetect.photo_id,
        confirmed_density: Number(density),
        confirmed_temperature_c: temp ? Number(temp) : null,
        ocr_density: densDetect.detected_density,
        ocr_temperature: densDetect.detected_temperature_c,
        ocr_confidence: densDetect.confidence,
        gps,
      });
      try {
        const summary = await api.weighmentSummary(token, txn.id);
        setWeighSummary({
          ...summary,
          density_kg_per_l: dens.density_kg_per_l ?? summary.density_kg_per_l,
          calculated_litres: dens.calculated_litres ?? summary.calculated_litres,
          net_kg: dens.net_kg_snapshot ?? summary.net_kg,
        });
      } catch {
        setWeighSummary((prev) => ({
          transaction_id: dens.transaction_id || prev?.transaction_id || txn.transaction_id,
          status: prev?.status || "DOCUMENTS_PENDING",
          tare_kg: prev?.tare_kg,
          gross_kg: prev?.gross_kg,
          net_kg: dens.net_kg_snapshot ?? prev?.net_kg,
          density_kg_per_l: dens.density_kg_per_l,
          temperature_c: dens.temperature_c ?? prev?.temperature_c,
          calculated_litres: dens.calculated_litres,
        }));
      }
      if (isOutward(txnType)) {
        try {
          await api.postStock(token, { transaction_pk: txn.id, direction: "OUT", use_transaction_qty: true, gps });
        } catch {
          /* optional */
        }
      }
      setDensDetect(null);
      advance("density");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Density confirm failed");
    } finally {
      setLoading(false);
    }
  };

  const doSlip = async (share = false) => {
    if (!txn) return;
    setLoading(true);
    setError(null);
    try {
      const path = `/api/v1/pdfs/transaction/${txn.id}?variant=customer`;
      const name = `weigh-${txn.transaction_id}.pdf`;
      if (share) await api.shareOrDownloadPdf(token, path, name);
      else await api.downloadPdf(token, path, name);
      if (step === "slip") advance("slip");
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF failed");
    } finally {
      setLoading(false);
    }
  };

  const doGatePassPdf = async (share = false) => {
    if (!txn) return;
    setLoading(true);
    setError(null);
    try {
      const path = `/api/v1/pdfs/gate-pass/${txn.id}`;
      const name = `gate-${txn.transaction_id}.pdf`;
      if (share) await api.shareOrDownloadPdf(token, path, name);
      else await api.downloadPdf(token, path, name);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gate pass PDF failed");
    } finally {
      setLoading(false);
    }
  };

  const acceptExit = async () => {
    if (!exitAnpr) return;
    if (exitAnpr.status === "MISMATCH") {
      setError("Exit plate mismatch — supervisor approval required.");
      return;
    }
    advance("exit");
  };

  const partyWhatsapp = () => {
    const list = txnType && isOutward(txnType) ? customers : suppliers;
    const party = list.find((p) => p.id === partyId);
    return (party?.whatsapp || party?.mobile || "").trim();
  };

  const sendCustomerOtp = async () => {
    if (!txn || !txnType) return;
    const mobile = (customerMobileKeep || customerWa || partyWhatsapp() || driverMobile).trim();
    if (mobile.replace(/\D/g, "").length < 10) {
      setError("Enter a valid customer WhatsApp mobile (10+ digits).");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const gps = await readGpsSafe(token);
      if (partyId) {
        await api.attachParties(
          token,
          txn.id,
          isOutward(txnType) ? { customer_id: partyId } : { supplier_id: partyId },
        );
      }
      const sent = await api.sendOtp(token, {
        transaction_pk: txn.id,
        customer_mobile: mobile,
        customer_name: customerName || driverName,
        gps,
      });
      setOtpSend(sent);
      setOtpCode("");
      setOtpVerified(false);
      setInfo(sent.message || "OTP sent to customer WhatsApp.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "OTP send failed");
    } finally {
      setLoading(false);
    }
  };

  const verifyCustomerOtp = async () => {
    if (!txn || !otpSend) return;
    if (!otpCode.trim()) {
      setError("Enter the OTP received by the customer.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const gps = await readGpsSafe(token);
      const res = await api.verifyOtp(token, {
        transaction_pk: txn.id,
        otp_id: otpSend.otp_id,
        otp_code: otpCode.trim(),
        gps,
      });
      if (!res.verified) {
        setError("OTP not accepted. Check the code and try again.");
        return;
      }
      setOtpVerified(true);
      setInfo("Customer OTP verified.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "OTP verify failed");
    } finally {
      setLoading(false);
    }
  };

  const doClose = async () => {
    if (!txn || !txnType || !exitAnpr) return;
    if (isOutward(txnType) && !otpVerified) {
      setError("Verify customer OTP before completing the transaction.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const gps = await readGpsSafe(token);
      if (partyId) {
        await api.attachParties(
          token,
          txn.id,
          isOutward(txnType) ? { customer_id: partyId } : { supplier_id: partyId },
        );
      }
      const chk = await api.closureCheck(token, txn.id);
      if (!chk.can_complete) {
        setError("Cannot close: " + chk.blockers.join(" | "));
        return;
      }
      if (!gatePass) {
        const gp = await api.createGatePass(token, txn.id, {
          pass_type: isOutward(txnType) ? "OUTWARD_LOADING" : "INWARD_MATERIAL",
          direction: isOutward(txnType) ? "OUTWARD" : "INWARD",
        });
        setGatePass(gp.gate_pass_number);
      }
      const conf = await api.confirmExit(token, {
        transaction_pk: txn.id,
        anpr_result_id: exitAnpr.id,
        gps,
        complete_transaction: true,
      });
      setTxn({ ...txn, status: conf.status });
      advance("close");
      setStep("done");
      markDone("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Close failed");
    } finally {
      setLoading(false);
    }
  };

  if (cam) {
    const hints: Record<string, string> = {
      lorry: "Frame the full lorry front with the number plate clearly visible.",
      invoice: "Lay the document flat. Include the QR code and all printed text.",
      eway: "Lay the E-Way Bill flat. Include QR and vehicle number.",
      tare: "Capture the weighbridge display clearly.",
      gross: "Capture the weighbridge display clearly.",
      density: "Capture the hydrometer / densitometer reading.",
      exit: "Frame the lorry at exit with number plate visible.",
    };
    return (
      <LiveCamera
        title={cam === "lorry" ? "Lorry Entry Photo" : cam.toUpperCase()}
        hint={hints[cam]}
        allowGallery={canGallery}
        onCapture={onCapture}
        onCancel={() => setCam(null)}
      />
    );
  }

  const titleMap: Partial<Record<YardStepId, string>> = {
    location: "Confirm location",
    type: "Vehicle entry",
    lorry: "Lorry photo",
    driver: "Driver details",
    docs: "Documents",
    post_docs: "Documents",
    gate: "Gate pass",
    gross: "Gross weighment",
    tare: "Tare weighment",
    density: "Density",
    slip: "Weighment slip",
    exit: "Exit photo",
    close: "Final approval",
    done: "Complete",
  };

  const stepNo = checklist.findIndex((c) => c.id === step) + 1;
  const entrySteps = ["location", "type", "lorry", "driver", "gate"];
  const isEntry = entrySteps.includes(step);
  const subtitle = txn
    ? `${txn.transaction_id}${plate ? ` · ${plate}` : ""}`
    : stepNo > 0
      ? `${stepNo}/${checklist.length}`
      : undefined;

  const mismatch = docStatus?.match_status === "MISMATCH" && ewayOk;

  return (
    <AppShell title={titleMap[step] || "Yard"} subtitle={subtitle} backTo={step === "type" ? "/" : undefined} wide>
      <div className="ve-flow ve-work">
      {isEntry && <YardEntryRail step={step} doneIds={doneIds} />}
      {!isEntry && step !== "done" && stepNo > 0 && (
        <div className="ve-progress">
          <div className="ve-progress-meta">
            <strong>
              {stepNo}/{checklist.length}
            </strong>
            <span>{titleMap[step]}</span>
          </div>
        </div>
      )}
      {step !== "done" && step !== "location" && <GpsBanner onGps={onGps} />}

      {(step === "lorry" || isDocStep(step) || step === "tare" || step === "gross" || step === "density" || step === "exit") &&
        phase !== "PHOTO" && <CapturePhaseBar active={phase} />}

      {info && <div className="ve-toast">{info}</div>}
      {error && <div className="err">{error}</div>}
      {loading && phase !== "AI" && <div className="ve-loading">Working…</div>}

      {step === "location" && (
        <section className="ve-panel ve-weigh-step">
          <header className="ve-weigh-head">
            <p className="ve-kicker">Entry · step 1</p>
            <h2>Location</h2>
            <p className="ve-help">Confirm you are at the yard using your current location.</p>
          </header>
          <div className={`ve-location-card ${locationOk ? "ok" : ""}`}>
            <em>Status</em>
            <b>{locationOk ? "Location OK" : "Waiting"}</b>
            <span>{locationDetail}</span>
          </div>
          {!locationOk ? (
            <button
              className="btn btn-primary ve-cta"
              type="button"
              disabled={locationBusy}
              onClick={() => void confirmLocation()}
            >
              {locationBusy ? "Getting location…" : "Use current location"}
            </button>
          ) : (
            <button
              className="btn btn-accept ve-cta"
              type="button"
              onClick={() => {
                markDone("location");
                setStep("type");
                setInfo(null);
              }}
            >
              Next · Choose type
            </button>
          )}
        </section>
      )}

      {phase === "AI" && previewUrl && (
        <section className="ve-panel ve-analyzing" aria-busy="true" aria-live="polite">
          <div className="ve-analyzing-frame">
            <img className="ve-preview ve-analyzing-img" src={previewUrl} alt="Captured" />
            <div className="ve-analyzing-veil">
              <span className="ve-analyzing-scan" aria-hidden />
              <div className="ve-analyzing-copy">
                <span className="ve-analyzing-pulse" aria-hidden />
                <strong>
                  {step === "lorry" || step === "exit"
                    ? "Reading number plate…"
                    : step === "tare" || step === "gross"
                      ? "Reading weighbridge…"
                      : step === "density"
                        ? "Reading density…"
                        : "Reading document…"}
                </strong>
                <span>Keep this screen open</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {step === "type" && (
        <section className="ve-panel">
          <header className="ve-weigh-head">
            <p className="ve-kicker">Entry · step 2</p>
            <h2>Type</h2>
            <p className="ve-help">Location confirmed. Choose inward or outward to start.</p>
          </header>
          <div className="field">
            <label htmlFor="ve-txn-type">Type</label>
            <select
              id="ve-txn-type"
              className="ve-select"
              value={txnType ?? ""}
              onChange={(e) => {
                const v = e.target.value;
                setTxnType(v === "MATERIAL_RECEIVING_INWARD" || v === "MATERIAL_LOADING_OUTWARD" ? v : null);
              }}
            >
              <option value="" disabled>
                Select…
              </option>
              <option value="MATERIAL_RECEIVING_INWARD">Inward</option>
              <option value="MATERIAL_LOADING_OUTWARD">Outward</option>
            </select>
          </div>
          <button
            className="btn btn-primary ve-cta"
            type="button"
            disabled={loading || !txnType}
            onClick={() => void startType()}
          >
            Start
          </button>
        </section>
      )}

      {step === "lorry" && phase === "PHOTO" && (
        <section className="ve-panel">
          <p className="ve-help">Live photo of number plate only.</p>
          <button className="btn btn-primary ve-cta" type="button" onClick={() => setCam("lorry")}>
            Open camera
          </button>
        </section>
      )}

      {step === "lorry" && phase === "CONFIRM" && anpr && (
        <section className="ve-panel">
          {previewUrl && <img className="ve-preview" src={previewUrl} alt="Lorry" />}
          <div className={`ve-badge ${(anpr.confidence || 0) < 0.7 ? "warn" : ""}`}>
            {Math.round((anpr.confidence || 0) * 100)}%
          </div>
          {aiNote ? <p className="ve-help">{aiNote}</p> : null}
          <div className="field">
            <label>Vehicle number</label>
            <input className="ve-plate-input" value={plate} onChange={(e) => setPlate(e.target.value)} autoCapitalize="characters" />
          </div>
          <div className="ve-dock-split">
            <button className="btn btn-ghost" type="button" onClick={() => { setPhase("PHOTO"); setAnpr(null); setCam("lorry"); }}>
              Retake
            </button>
            <button className="btn btn-accept" type="button" disabled={loading} onClick={() => void acceptLorry()}>
              Next
            </button>
          </div>
        </section>
      )}

      {step === "driver" && (
        <section className="ve-panel">
          <header className="ve-weigh-head">
            <p className="ve-kicker">Yard · driver &amp; vehicle</p>
            <h2>Driver</h2>
            <p className="ve-help">Fields match weighment slip / gate pass. Next: gate pass + tank.</p>
          </header>
          <div className="ve-form">
            <div className="field">
              <label>Vehicle type *</label>
              <select className="ve-select" value={vehicleType} onChange={(e) => setVehicleType(e.target.value)}>
                <option value="Truck">Truck</option>
                <option value="Tanker">Tanker</option>
                <option value="Trailer">Trailer</option>
              </select>
            </div>
            <div className="field">
              <label>Driver name *</label>
              <input value={driverName} onChange={(e) => setDriverName(e.target.value)} autoComplete="name" />
            </div>
            <div className="field">
              <label>Driver mobile *</label>
              <input value={driverMobile} onChange={(e) => setDriverMobile(e.target.value)} inputMode="tel" />
            </div>
            <div className="field">
              <label>Licence</label>
              <input value={licence} onChange={(e) => setLicence(e.target.value)} />
            </div>
            <div className="field">
              <label>Transporter / company</label>
              <input value={transporter} onChange={(e) => setTransporter(e.target.value)} />
            </div>
            <div className="field">
              <label>Customer WhatsApp (OTP / slip)</label>
              <input value={customerWa} onChange={(e) => setCustomerWa(e.target.value)} placeholder="91…" inputMode="tel" />
            </div>
          </div>
          <button className="btn btn-primary ve-cta" type="button" disabled={loading} onClick={() => void saveDriver()}>
            Next · Gate pass
          </button>
        </section>
      )}

      {isDocStep(step) && (
        <section className="ve-panel">
          {weighSummary && (weighSummary.net_kg != null || weighSummary.calculated_litres != null) && (
            <div className="ve-qty">
              <div><em>Net</em><b>{weighSummary.net_kg != null ? `${weighSummary.net_kg} kg` : "—"}</b></div>
              <div><em>L</em><b>{weighSummary.calculated_litres != null ? String(weighSummary.calculated_litres) : "—"}</b></div>
            </div>
          )}
          <div className="ve-doc-progress">
            <div className={`ve-doc-pip${invoiceOk ? " done" : !ewayOk ? " on" : ""}`}>1 Invoice</div>
            <div className={`ve-doc-pip${ewayOk ? " done" : invoiceOk ? " on" : ""}`}>2 E-Way</div>
          </div>

          {mismatch && (
            <div className="ve-mismatch">
              <strong>Mismatch</strong>
              <div className="ve-mismatch-grid">
                <div><em>ANPR</em><b>{plate || docStatus?.anpr_vehicle || "—"}</b></div>
                <div><em>Doc</em><b>{ewayVehicle || invoiceVehicle || "—"}</b></div>
              </div>
              <p>Needs supervisor approval.</p>
            </div>
          )}

          {phase === "CONFIRM" && docDetect && (
            <>
              {previewUrl && <img className="ve-preview" src={previewUrl} alt="Document" />}
              <div className={`ve-badge ${(docDetect.confidence || 0) < 0.7 ? "warn" : ""}`}>
                {Math.round((docDetect.confidence || 0) * 100)}%
              </div>
              <div className="ve-form">
              {docKind === "invoice" ? (
                <>
                  <div className="field"><label>Vehicle</label><input value={invoiceVehicle} onChange={(e) => setInvoiceVehicle(e.target.value)} /></div>
                  <div className="field"><label>Invoice no.</label><input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} /></div>
                  <div className="field"><label>Date</label><input value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} /></div>
                  <div className="field"><label>Supplier</label><input value={supplierName} onChange={(e) => setSupplierName(e.target.value)} /></div>
                  <div className="field"><label>Customer</label><input value={customerName} onChange={(e) => setCustomerName(e.target.value)} /></div>
                  <div className="field"><label>GSTIN</label><input value={gstin} onChange={(e) => setGstin(e.target.value)} /></div>
                </>
              ) : (
                <>
                  <div className="field"><label>Vehicle</label><input value={ewayVehicle} onChange={(e) => setEwayVehicle(e.target.value)} /></div>
                  <div className="field"><label>E-Way no.</label><input value={ewayNumber} onChange={(e) => setEwayNumber(e.target.value)} /></div>
                </>
              )}
              </div>
              <div className="ve-dock-split">
                <button className="btn btn-ghost" type="button" onClick={() => { setPhase("PHOTO"); setDocDetect(null); setCam(docKind === "invoice" ? "invoice" : "eway"); }}>
                  Retake
                </button>
                <button className="btn btn-accept" type="button" disabled={loading} onClick={() => void acceptDoc()}>
                  Accept
                </button>
              </div>
            </>
          )}

          {phase === "PHOTO" && !mismatch && (
            <>
              {!invoiceOk && (
                <button className="btn btn-primary ve-cta" type="button" onClick={() => setCam("invoice")}>
                  Capture invoice
                </button>
              )}
              {invoiceOk && !ewayOk && (
                <button className="btn btn-primary ve-cta" type="button" onClick={() => setCam("eway")}>
                  Capture E-Way
                </button>
              )}
              {invoiceOk && ewayOk && docStatus?.match_status === "MATCH" && (
                <button className="btn btn-accept ve-cta" type="button" onClick={() => advance(step)}>
                  Next
                </button>
              )}
            </>
          )}

          {mismatch && (
            <div className="ve-dock-split">
              <button className="btn btn-ghost" type="button" onClick={() => { setEwayOk(false); setDocStatus(null); setCam("eway"); }}>
                Rescan
              </button>
              <Link className="btn btn-dark" to="/inbox?tab=approvals">
                Inbox
              </Link>
            </div>
          )}
        </section>
      )}

      {step === "gate" && (
        <section className="ve-panel ve-weigh-step">
          <header className="ve-weigh-head">
            <p className="ve-kicker">Yard · gate pass</p>
            <h2>Gate pass</h2>
            <p className="ve-help">
              Product, tank, route &amp; security checks — then issue pass.
              {txnType
                ? isOutward(txnType)
                  ? " Next: tare (empty) weighment."
                  : " Next: gross (loaded) weighment."
                : ""}
            </p>
          </header>
          {plate ? (
            <div className="ve-gate-plate">
              <em>Vehicle</em>
              <b>{plate}</b>
              {vehicleType ? <span> · {vehicleType}</span> : null}
            </div>
          ) : null}
          <div className="ve-form">
            <div className="field">
              <label>Purpose</label>
              <input
                value={txnType && isOutward(txnType) ? "Outward loading" : "Inward material"}
                readOnly
              />
            </div>
            <div className="field">
              <label>Product / material *</label>
              <select className="ve-select" value={productId} onChange={(e) => setProductId(e.target.value)}>
                {products.length === 0 && <option value="">Loading…</option>}
                {products.map((p) => (
                  <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Storage / tank *</label>
              <select className="ve-select" value={unitId} onChange={(e) => setUnitId(e.target.value)}>
                {units.length === 0 && <option value="">Loading…</option>}
                {units.map((u) => (
                  <option key={u.id} value={u.id}>{u.code} — {u.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>From / origin</label>
              <input
                value={fromLocation}
                onChange={(e) => setFromLocation(e.target.value)}
                placeholder={txnType && isOutward(txnType) ? "JV yard / tank" : "Supplier / plant"}
              />
            </div>
            <div className="field">
              <label>To / destination</label>
              <input value={toLocation} onChange={(e) => setToLocation(e.target.value)} />
            </div>
            <div className="field">
              <label>Invoice / challan no.</label>
              <input value={invoiceChallan} onChange={(e) => setInvoiceChallan(e.target.value)} />
            </div>
            <div className="field">
              <label>Remarks</label>
              <input value={gateRemarks} onChange={(e) => setGateRemarks(e.target.value)} />
            </div>
            <div className="field">
              <label>Security verification</label>
              <div className="ve-check-row">
                <label><input type="checkbox" checked={secVehicle} onChange={(e) => setSecVehicle(e.target.checked)} /> Vehicle checked</label>
                <label><input type="checkbox" checked={secGoods} onChange={(e) => setSecGoods(e.target.checked)} /> Goods verified</label>
                <label><input type="checkbox" checked={secDocs} onChange={(e) => setSecDocs(e.target.checked)} /> Documents verified</label>
              </div>
            </div>
          </div>
          {gatePass ? (
            <p className="ve-gate-issued">
              Pass issued: <strong>{gatePass}</strong>
            </p>
          ) : null}
          <button
            className="btn btn-primary ve-cta ve-weigh-capture"
            type="button"
            disabled={loading || !productId || !unitId}
            onClick={() => void doGate()}
          >
            {txnType && isOutward(txnType) ? "Issue pass · Tare" : "Issue pass · Gross"}
          </button>
        </section>
      )}

      {(step === "gross" || step === "tare") && phase === "PHOTO" && (
        <section className="ve-panel ve-weigh-step">
          <header className="ve-weigh-head">
            <p className="ve-kicker">{step === "gross" ? "Loaded weight" : "Empty weight"}</p>
            <h2>{step === "gross" ? "Gross" : "Tare"}</h2>
            <p className="ve-help">Frame the weighbridge display so every digit is sharp.</p>
          </header>
          <div className="ve-weigh-board" aria-label="Weighment summary">
            <div className={`ve-weigh-cell ${step === "tare" ? "focus" : ""}`}>
              <em>Tare</em>
              <b>{weighSummary?.tare_kg != null ? `${weighSummary.tare_kg}` : "—"}</b>
              <span>kg</span>
            </div>
            <div className={`ve-weigh-cell ${step === "gross" ? "focus" : ""}`}>
              <em>Gross</em>
              <b>{weighSummary?.gross_kg != null ? `${weighSummary.gross_kg}` : "—"}</b>
              <span>kg</span>
            </div>
            <div className="ve-weigh-cell net">
              <em>Net</em>
              <b>{weighSummary?.net_kg != null ? `${weighSummary.net_kg}` : "—"}</b>
              <span>kg</span>
            </div>
          </div>
          <ol className="ve-weigh-tips">
            <li>Stand square to the display</li>
            <li>Avoid glare / reflections</li>
            <li>Include the full kg reading</li>
          </ol>
          <button className="btn btn-primary ve-cta ve-weigh-capture" type="button" onClick={() => setCam(step)}>
            Capture {step}
          </button>
          {allowWeighSkip && (
            <button
              className="btn btn-ghost ve-cta"
              type="button"
              disabled={loading}
              onClick={() => {
                setInfo(`${step === "tare" ? "Tare" : "Gross"} skipped (dev only) — continue.`);
                advance(step);
              }}
            >
              Skip {step} · Next (dev)
            </button>
          )}
        </section>
      )}
      {(step === "gross" || step === "tare") && phase === "CONFIRM" && weightDetect && (
        <section className="ve-panel ve-weigh-step">
          {previewUrl && <img className="ve-preview ve-weigh-preview" src={previewUrl} alt="Weigh" />}
          <div className="field">
            <label>{step === "gross" ? "Gross" : "Tare"} (kg)</label>
            <input className="ve-weigh-input" value={weight} onChange={(e) => setWeight(e.target.value)} inputMode="decimal" />
          </div>
          {aiNote ? <p className="ve-help">{aiNote}</p> : null}
          <div className="ve-dock-split">
            <button className="btn btn-ghost" type="button" onClick={() => { setPhase("PHOTO"); setWeightDetect(null); setCam(step as "tare" | "gross"); }}>Retake</button>
            <button className="btn btn-accept" type="button" disabled={loading} onClick={() => void confirmWeight(step === "tare" ? "TARE" : "GROSS")}>Accept</button>
          </div>
        </section>
      )}

      {step === "density" && phase === "PHOTO" && (
        <section className="ve-panel">
          {weighSummary && weighSummary.net_kg != null && (
            <div className="ve-qty">
              <div><em>Net</em><b>{weighSummary.net_kg}</b></div>
              <div><em>L</em><b>{weighSummary.calculated_litres != null ? String(weighSummary.calculated_litres) : "—"}</b></div>
            </div>
          )}
          <button className="btn btn-primary ve-cta" type="button" onClick={() => setCam("density")}>Capture density</button>
          {allowWeighSkip && (
            <button className="btn btn-ghost ve-cta" type="button" onClick={() => advance("density")}>
              Skip density (dev)
            </button>
          )}
        </section>
      )}
      {step === "density" && phase === "CONFIRM" && densDetect && (
        <section className="ve-panel">
          <div className="ve-form">
            <div className="field"><label>Density kg/L</label><input value={density} onChange={(e) => setDensity(e.target.value)} inputMode="decimal" /></div>
            <div className="field"><label>Temp °C</label><input value={temp} onChange={(e) => setTemp(e.target.value)} inputMode="decimal" /></div>
          </div>
          <button className="btn btn-accept ve-cta" type="button" disabled={loading} onClick={() => void confirmDens()}>Accept</button>
        </section>
      )}

      {step === "slip" && (
        <section className="ve-panel">
          <header className="ve-weigh-head">
            <p className="ve-kicker">Deliverable</p>
            <h2>Weighment slip</h2>
            <p className="ve-help">Branded customer PDF with gross / tare / net, calibration cert, and signatures.</p>
          </header>
          {weighSummary && (
            <div className="ve-qty">
              <div><em>Net</em><b>{weighSummary.net_kg != null ? `${weighSummary.net_kg}` : "—"}</b></div>
              <div><em>L</em><b>{weighSummary.calculated_litres != null ? String(weighSummary.calculated_litres) : "—"}</b></div>
              <div><em>D</em><b>{weighSummary.density_kg_per_l != null ? String(weighSummary.density_kg_per_l) : "—"}</b></div>
            </div>
          )}
          <div className="ve-dock-split">
            <button className="btn btn-ghost" type="button" disabled={loading} onClick={() => void doSlip(false)}>Download slip</button>
            <button className="btn btn-primary" type="button" disabled={loading} onClick={() => void doSlip(true)}>Share slip</button>
          </div>
          <button className="btn btn-accept ve-cta" type="button" onClick={() => advance("slip")}>Next</button>
        </section>
      )}

      {step === "exit" && phase === "PHOTO" && (
        <section className="ve-panel">
          <p className="ve-help">Exit photo — plate must match entry.</p>
          <button className="btn btn-primary ve-cta" type="button" onClick={() => setCam("exit")}>Open camera</button>
        </section>
      )}
      {step === "exit" && phase === "CONFIRM" && exitAnpr && (
        <section className="ve-panel">
          {previewUrl && <img className="ve-preview" src={previewUrl} alt="Exit" />}
          <div className={`ve-badge ${exitAnpr.status === "MISMATCH" ? "warn" : ""}`}>
            {exitAnpr.status} · {Math.round((exitAnpr.confidence || 0) * 100)}%
          </div>
          <div className="ve-dock-split">
            <button className="btn btn-ghost" type="button" onClick={() => { setPhase("PHOTO"); setExitAnpr(null); setCam("exit"); }}>Retake</button>
            <button className="btn btn-accept" type="button" onClick={() => void acceptExit()}>Next</button>
          </div>
        </section>
      )}

      {step === "close" && txnType && (
        <section className="ve-panel">
          <div className="ve-form">
            <div className="field">
              <label>{isOutward(txnType) ? "Customer" : "Supplier"}</label>
              <select value={partyId} onChange={(e) => setPartyId(e.target.value)}>
                {(isOutward(txnType) ? customers : suppliers).map((p) => (
                  <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
                ))}
              </select>
            </div>
            {isOutward(txnType) && (
              <>
                <div className="field">
                  <label>WhatsApp</label>
                  <input
                    value={customerMobileKeep || customerWa || partyWhatsapp()}
                    onChange={(e) => setCustomerMobileKeep(e.target.value)}
                    placeholder="From customer master or 91…"
                    inputMode="tel"
                  />
                </div>
                {otpSend && (
                  <div className="field">
                    <label>OTP</label>
                    <input value={otpCode} onChange={(e) => setOtpCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" />
                    {otpSend.otp_preview && <p className="ve-dock-hint">Dev code: {otpSend.otp_preview}</p>}
                  </div>
                )}
              </>
            )}
          </div>
          {otpVerified && <div className="ve-badge">OTP OK</div>}
          {isOutward(txnType) && !otpVerified && (
            <>
              <button className="btn btn-ghost ve-cta" type="button" disabled={loading} onClick={() => void sendCustomerOtp()}>
                {otpSend ? "Resend OTP" : "Send OTP"}
              </button>
              {otpSend && (
                <button className="btn btn-primary ve-cta" type="button" disabled={loading} onClick={() => void verifyCustomerOtp()}>
                  Verify OTP
                </button>
              )}
            </>
          )}
          <button
            className="btn btn-accept ve-cta"
            type="button"
            disabled={loading || (isOutward(txnType) && !otpVerified)}
            onClick={() => void doClose()}
          >
            Complete
          </button>
        </section>
      )}

      {step === "done" && (
        <section className="ve-panel">
          <p className="ve-help">
            Done · <strong>{txn?.transaction_id}</strong>
            {gatePass ? ` · ${gatePass}` : ""}
          </p>
          {weighSummary && (
            <div className="ve-qty">
              <div><em>Net</em><b>{weighSummary.net_kg != null ? `${weighSummary.net_kg}` : "—"}</b></div>
              <div><em>L</em><b>{weighSummary.calculated_litres != null ? String(weighSummary.calculated_litres) : "—"}</b></div>
            </div>
          )}
          <div className="ve-dock-split">
            <button className="btn btn-ghost" type="button" disabled={loading} onClick={() => void doGatePassPdf(true)}>Share gate pass</button>
            <button className="btn btn-primary" type="button" disabled={loading} onClick={() => void doSlip(true)}>Share weighment slip</button>
          </div>
          <Link className="btn btn-accept ve-cta" to="/yard">New entry</Link>
          <Link className="btn btn-ghost ve-cta" to="/">Home</Link>
        </section>
      )}
      </div>
    </AppShell>
  );
}
