import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { readGps } from "../lib/device";
import { useAuth } from "../state/auth";
import { AppShell } from "../components/AppShell";

export function EquipmentPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<api.Equipment[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [vendor, setVendor] = useState("ABC Motors");
  const [reason, setReason] = useState("Seal leak");
  const [destination, setDestination] = useState("Plant-2 store");
  const [disposalId, setDisposalId] = useState("");
  const [approvalNote, setApprovalNote] = useState("");
  const [last, setLast] = useState<api.EquipmentAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    if (!token) return;
    const list = await api.listEquipment(token);
    setItems(list);
    if (!selectedId && list[0]) setSelectedId(list[0].id);
  };

  useEffect(() => {
    if (!token) return;
    refresh().catch((e) => setError(e instanceof Error ? e.message : "Load failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!token) return null;

  const selected = items.find((e) => e.id === selectedId) || null;

  const run = async (fn: () => Promise<api.EquipmentAction>, okMsg: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fn();
      setLast(res);
      if (res.disposal?.id) setDisposalId(res.disposal.id);
      setInfo(okMsg);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="Equipment" subtitle="Repair · return · transfer · disposal" backTo="/more" wide>
        {info && (
          <div className="panel" style={{ padding: "1rem" }}>
            {info}
          </div>
        )}
        {error && <div className="err">{error}</div>}
        {loading && <div className="muted">Working…</div>}

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="field">
            <label>Equipment</label>
            <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
              {items.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.code} — {e.name} [{e.status}]
                </option>
              ))}
            </select>
          </div>
          {selected && (
            <div className="muted">
              {selected.category} · {selected.location_label || "—"} · {selected.status}
            </div>
          )}
        </div>

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Repair out
          </div>
          <div className="field">
            <label>Vendor</label>
            <input value={vendor} onChange={(e) => setVendor(e.target.value)} />
          </div>
          <div className="field">
            <label>Reason</label>
            <input value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
          <button
            className="btn btn-primary"
            type="button"
            disabled={!selectedId}
            onClick={() =>
              run(async () => {
                const gps = await readGps();
                return api.repairOut(token, {
                  equipment_id: selectedId,
                  vendor_name: vendor,
                  reason,
                  gps,
                });
              }, "Repair out recorded — status OUT_FOR_REPAIR")
            }
          >
            Send for repair
          </button>
          <button
            className="btn btn-ghost"
            type="button"
            disabled={!selectedId}
            onClick={() =>
              run(async () => {
                const gps = await readGps();
                return api.repairReturn(token, {
                  equipment_id: selectedId,
                  repair_id: last?.repair?.id,
                  note: "Returned to yard",
                  gps,
                });
              }, "Returned to IN_YARD")
            }
          >
            Record return
          </button>
        </div>

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Transfer
          </div>
          <div className="field">
            <label>Destination</label>
            <input value={destination} onChange={(e) => setDestination(e.target.value)} />
          </div>
          <button
            className="btn btn-primary"
            type="button"
            disabled={!selectedId}
            onClick={() =>
              run(async () => {
                const gps = await readGps();
                return api.transferEquipment(token, {
                  equipment_id: selectedId,
                  destination,
                  reason: `Transfer to ${destination}`,
                  gps,
                });
              }, "Transferred")
            }
          >
            Transfer out
          </button>
        </div>

        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Disposal (needs approval)
          </div>
          <button
            className="btn btn-primary"
            type="button"
            disabled={!selectedId}
            onClick={() =>
              run(async () => {
                const gps = await readGps();
                return api.requestDisposal(token, {
                  equipment_id: selectedId,
                  reason: "Beyond economical repair",
                  gps,
                });
              }, "Disposal pending approval")
            }
          >
            Request disposal
          </button>
          <div className="field">
            <label>Disposal id</label>
            <input value={disposalId} onChange={(e) => setDisposalId(e.target.value)} />
          </div>
          <div className="field">
            <label>Approval note</label>
            <input value={approvalNote} onChange={(e) => setApprovalNote(e.target.value)} />
          </div>
          <button
            className="btn btn-primary"
            type="button"
            disabled={!disposalId || !approvalNote.trim()}
            onClick={() =>
              run(async () => {
                const gps = await readGps();
                return api.decideDisposal(token, {
                  disposal_id: disposalId,
                  approve: true,
                  approval_note: approvalNote.trim(),
                  gps,
                });
              }, "Disposal approved — DISPOSED")
            }
          >
            Approve disposal
          </button>
        </div>

        {last && (
          <div className="panel" style={{ padding: "1rem" }}>
            <strong>{last.transaction_id}</strong>
            <div className="muted">
              {last.equipment.code} → {last.equipment.status} · txn {last.transaction_status}
            </div>
          </div>
        )}
      </AppShell>
  );
}
