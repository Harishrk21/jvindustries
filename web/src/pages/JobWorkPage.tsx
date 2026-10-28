import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { readGps } from "../lib/device";
import { useAuth } from "../state/auth";
import { AppShell } from "../components/AppShell";

export function JobWorkPage() {
  const { token } = useAuth();
  const [products, setProducts] = useState<api.Product[]>([]);
  const [productId, setProductId] = useState("");
  const [batchCode, setBatchCode] = useState(`JW-${Date.now().toString().slice(-6)}`);
  const [customerName, setCustomerName] = useState("ABC Industries");
  const [mobile, setMobile] = useState("9876543210");
  const [qtyIn, setQtyIn] = useState("100000");
  const [qtyOut, setQtyOut] = useState("97500");
  const [batch, setBatch] = useState<api.JobWorkBatch | null>(null);
  const [otp, setOtp] = useState<api.OtpSend | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [approvalNote, setApprovalNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    api
      .listProducts(token)
      .then((p) => {
        setProducts(p);
        if (p[0]) setProductId(p[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load products"));
  }, [token]);

  if (!token) return null;

  const createBatch = async () => {
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const b = await api.createJobWorkBatch(token, {
        batch_code: batchCode,
        product_id: productId || undefined,
        customer_name: customerName,
        customer_mobile: mobile,
        unit: "KG",
        gps,
      });
      setBatch(b);
      setInfo(`Batch ${b.batch_code} created on ${b.transaction_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setLoading(false);
    }
  };

  const setQty = async () => {
    if (!batch) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const b = await api.setJobWorkQty(token, {
        batch_id: batch.id,
        qty_in: Number(qtyIn),
        qty_out: Number(qtyOut),
        gps,
      });
      setBatch(b);
      if (b.loss?.requires_approval) {
        setInfo(
          `Loss ${b.loss.loss_percent}% exceeds limit ${b.loss.loss_limit_percent}% (excess ${b.loss.excess_percent}%). Approval required.`,
        );
      } else {
        setInfo(`Loss within limit. Batch ${b.status}.`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Quantity update failed");
    } finally {
      setLoading(false);
    }
  };

  const approve = async () => {
    if (!batch?.loss?.id || !approvalNote.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const b = await api.approveLoss(token, {
        loss_id: batch.loss.id,
        approval_note: approvalNote.trim(),
        gps,
      });
      setBatch(b);
      setInfo("Excess loss approved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setLoading(false);
    }
  };

  const sendCustomerOtp = async () => {
    if (!batch) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const s = await api.sendOtp(token, {
        transaction_pk: batch.transaction_pk,
        customer_mobile: mobile,
        customer_name: customerName,
        gps,
      });
      setOtp(s);
      if (s.otp_preview) setOtpCode(s.otp_preview);
      setInfo(s.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "OTP send failed");
    } finally {
      setLoading(false);
    }
  };

  const verifyCustomerOtp = async () => {
    if (!batch || !otp) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const v = await api.verifyOtp(token, {
        transaction_pk: batch.transaction_pk,
        otp_id: otp.otp_id,
        otp_code: otpCode,
        gps,
      });
      setInfo(`OTP verified. Transaction → ${v.transaction_status}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "OTP verify failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="Job Work & OTP" subtitle="Batches · loss limits · WhatsApp OTP" backTo="/more" wide>
        {info && (
          <div className="panel" style={{ padding: "1rem" }}>
            {info}
          </div>
        )}
        {error && <div className="err">{error}</div>}
        {loading && <div className="muted">Working…</div>}

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Create batch
          </div>
          <div className="field">
            <label>Batch code</label>
            <input value={batchCode} onChange={(e) => setBatchCode(e.target.value)} />
          </div>
          <div className="field">
            <label>Product</label>
            <select value={productId} onChange={(e) => setProductId(e.target.value)}>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} — limit {p.loss_limit_percent}%
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Customer</label>
            <input value={customerName} onChange={(e) => setCustomerName(e.target.value)} />
          </div>
          <div className="field">
            <label>WhatsApp mobile</label>
            <input value={mobile} onChange={(e) => setMobile(e.target.value)} />
          </div>
          <button className="btn btn-primary" type="button" onClick={createBatch}>
            Start job-work batch
          </button>
        </div>

        {batch && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div>
              <strong>{batch.batch_code}</strong>
              <div className="muted">
                {batch.transaction_id} · {batch.status}
              </div>
            </div>
            <div className="field">
              <label>Qty in</label>
              <input value={qtyIn} onChange={(e) => setQtyIn(e.target.value)} />
            </div>
            <div className="field">
              <label>Qty out</label>
              <input value={qtyOut} onChange={(e) => setQtyOut(e.target.value)} />
            </div>
            <button className="btn btn-primary" type="button" onClick={setQty}>
              Calculate loss (server)
            </button>

            {batch.loss && (
              <div className="grid-cards">
                <div className="stat-card">
                  <div className="muted">Loss qty</div>
                  <strong>{batch.loss.loss_qty}</strong>
                </div>
                <div className="stat-card">
                  <div className="muted">Loss %</div>
                  <strong>{batch.loss.loss_percent}%</strong>
                </div>
                <div className="stat-card">
                  <div className="muted">Limit</div>
                  <strong>{batch.loss.loss_limit_percent}%</strong>
                </div>
                <div className="stat-card">
                  <div className="muted">Excess</div>
                  <strong>{batch.loss.excess_percent}%</strong>
                </div>
              </div>
            )}

            {batch.loss?.requires_approval && !batch.loss.approved && (
              <div className="stack">
                <div className="field">
                  <label>Approval note</label>
                  <input value={approvalNote} onChange={(e) => setApprovalNote(e.target.value)} />
                </div>
                <button className="btn btn-primary" type="button" onClick={approve}>
                  Approve excess loss
                </button>
              </div>
            )}
          </div>
        )}

        {batch && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
              Customer WhatsApp OTP
            </div>
            <div className="muted">
              Official WhatsApp when credentials are set; otherwise mock delivery + on-screen code so the flow always works.
            </div>
            <button className="btn btn-primary" type="button" onClick={sendCustomerOtp}>
              Send OTP
            </button>
            {otp && (
              <>
                <div className="muted">
                  Channel {otp.channel} · {otp.whatsapp_delivery_status}
                  {otp.otp_preview ? ` · preview ${otp.otp_preview}` : ""}
                </div>
                <div className="field">
                  <label>Enter OTP</label>
                  <input value={otpCode} onChange={(e) => setOtpCode(e.target.value)} />
                </div>
                <button className="btn btn-primary" type="button" onClick={verifyCustomerOtp}>
                  Verify OTP
                </button>
              </>
            )}
          </div>
        )}
      </AppShell>
  );
}
