import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import * as api from "../lib/api";
import { readGps } from "../lib/device";
import { useAuth } from "../state/auth";
import { AppShell } from "../components/AppShell";

export function StockPage() {
  const { transactionPk: routePk } = useParams();
  const { token } = useAuth();
  const [pk, setPk] = useState(routePk || "");
  const [balances, setBalances] = useState<api.StockBalance[]>([]);
  const [products, setProducts] = useState<api.Product[]>([]);
  const [units, setUnits] = useState<api.StorageUnit[]>([]);
  const [txn, setTxn] = useState<api.TxnStock | null>(null);
  const [productId, setProductId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [qty, setQty] = useState("");
  const [useServerQty, setUseServerQty] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refreshMasters = async () => {
    if (!token) return;
    const [b, p, u] = await Promise.all([
      api.stockBalances(token),
      api.listProducts(token),
      api.listStorageUnits(token),
    ]);
    setBalances(b);
    setProducts(p);
    setUnits(u);
    if (!productId && p[0]) setProductId(p[0].id);
    if (!unitId) {
      const t03 = u.find((x) => x.code === "T-03") || u[0];
      if (t03) setUnitId(t03.id);
    }
  };

  const loadTxn = async (id: string) => {
    if (!token || !id) return;
    setLoading(true);
    setError(null);
    try {
      await refreshMasters();
      setTxn(await api.txnStock(token, id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load stock");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) return;
    refreshMasters().catch((e) => setError(e instanceof Error ? e.message : "Failed to load stock"));
    if (routePk) loadTxn(routePk);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routePk, token]);

  if (!token) return null;

  const onOpen = (e: FormEvent) => {
    e.preventDefault();
    if (pk.trim()) loadTxn(pk.trim());
  };

  const onAssign = async () => {
    if (!pk || !productId || !unitId) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const s = await api.assignStorage(token, {
        transaction_pk: pk,
        product_id: productId,
        storage_unit_id: unitId,
        gps,
      });
      setTxn(s);
      setInfo(`Assigned ${s.product_code} → ${s.storage_code}`);
      await refreshMasters();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Assign failed");
    } finally {
      setLoading(false);
    }
  };

  const onPost = async (direction: "IN" | "OUT") => {
    if (!pk) return;
    setLoading(true);
    setError(null);
    try {
      const gps = await readGps();
      const s = await api.postStock(token, {
        transaction_pk: pk,
        direction,
        use_transaction_qty: useServerQty,
        quantity: useServerQty ? undefined : Number(qty),
        unit: useServerQty ? undefined : "L",
        gps,
      });
      setTxn(s);
      setInfo(`Stock ${direction} posted. Balance updates from ledger only.`);
      await refreshMasters();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Post failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="Storage & Stock" subtitle="Tanks · barrels · IBC · ledger balances" backTo="/more" wide>
        <div className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.25rem" }}>
            Balances
          </div>
          {balances.length === 0 && <div className="muted">No movements yet.</div>}
          <div className="grid-cards">
            {balances.map((b) => (
              <div className="stat-card" key={`${b.storage_unit_id}-${b.product_id}`}>
                <div className="muted">
                  {b.storage_kind} {b.storage_code}
                </div>
                <strong style={{ fontSize: "1.35rem" }}>
                  {b.quantity.toLocaleString()} {b.unit}
                </strong>
                <div className="muted">{b.product_name}</div>
              </div>
            ))}
          </div>
        </div>

        {!routePk && (
          <form className="panel stack" style={{ padding: "1.25rem" }} onSubmit={onOpen}>
            <div className="field">
              <label>Transaction UUID</label>
              <input value={pk} onChange={(e) => setPk(e.target.value)} placeholder="After documents verified" />
            </div>
            <button className="btn btn-primary" type="submit">
              Open transaction stock
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

        {txn && (
          <div className="panel stack" style={{ padding: "1.25rem" }}>
            <div>
              <strong>{txn.transaction_id}</strong>
              <div className="muted">{txn.status}</div>
            </div>
            <div className="grid-cards">
              <div className="stat-card">
                <div className="muted">Product</div>
                <strong>{txn.product_code ?? "—"}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Storage</div>
                <strong>{txn.storage_code ?? "—"}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Net kg</div>
                <strong>{txn.net_kg ?? "—"}</strong>
              </div>
              <div className="stat-card">
                <div className="muted">Litres</div>
                <strong>{txn.calculated_litres ?? "—"}</strong>
              </div>
            </div>

            <div className="field">
              <label>Product</label>
              <select value={productId} onChange={(e) => setProductId(e.target.value)}>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} — {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Storage unit</label>
              <select value={unitId} onChange={(e) => setUnitId(e.target.value)}>
                {units.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.kind} {u.code} — {u.name}
                  </option>
                ))}
              </select>
            </div>
            <button className="btn btn-primary" type="button" onClick={onAssign}>
              Assign product + storage
            </button>

            <label className="muted" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <input type="checkbox" checked={useServerQty} onChange={(e) => setUseServerQty(e.target.checked)} />
              Use server net / litres
            </label>
            {!useServerQty && (
              <div className="field">
                <label>Quantity (manual)</label>
                <input value={qty} onChange={(e) => setQty(e.target.value)} />
              </div>
            )}

            <div className="action-grid">
              <button className="action-tile" type="button" onClick={() => onPost("IN")} disabled={txn.stock_posted}>
                Post IN
                <span>Receiving</span>
              </button>
              <button className="action-tile" type="button" onClick={() => onPost("OUT")} disabled={txn.stock_posted}>
                Post OUT
                <span>Loading</span>
              </button>
              <button className="action-tile" type="button" onClick={() => loadTxn(pk)}>
                Refresh
                <span>Reload ledger</span>
              </button>
            </div>
            {txn.stock_posted && <div className="muted">Stock already posted for this transaction.</div>}
          </div>
        )}
      </AppShell>
  );
}
