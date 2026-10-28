import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import * as api from "../lib/api";
import { useAuth } from "../state/auth";

type Tab = "products" | "storage" | "customers" | "suppliers" | "calibration" | "users";

export function MastersPage() {
  const { token, user } = useAuth();
  const canMaster = !!user?.permissions?.includes("master.manage") || !!user?.permissions?.includes("owner.full");
  const canUsers = !!user?.permissions?.includes("user.manage") || !!user?.permissions?.includes("owner.full");
  const [tab, setTab] = useState<Tab>("products");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [products, setProducts] = useState<api.Product[]>([]);
  const [units, setUnits] = useState<api.StorageUnit[]>([]);
  const [customers, setCustomers] = useState<api.Party[]>([]);
  const [suppliers, setSuppliers] = useState<api.Party[]>([]);
  const [cals, setCals] = useState<api.Calibration[]>([]);
  const [users, setUsers] = useState<api.AdminUser[]>([]);
  const [roles, setRoles] = useState<string[]>([]);

  const [pCode, setPCode] = useState("");
  const [pName, setPName] = useState("");
  const [pHsn, setPHsn] = useState("");
  const [pUnit, setPUnit] = useState("KG");
  const [pDensity, setPDensity] = useState("");
  const [pLoss, setPLoss] = useState("2");

  const [sCode, setSCode] = useState("");
  const [sName, setSName] = useState("");
  const [sKind, setSKind] = useState("TANK");
  const [sCap, setSCap] = useState("");
  const [sCapUnit, setSCapUnit] = useState("L");
  const [sLoc, setSLoc] = useState("");
  const [sProductId, setSProductId] = useState("");

  const [cCode, setCCode] = useState("");
  const [cName, setCName] = useState("");
  const [cMobile, setCMobile] = useState("");
  const [cWa, setCWa] = useState("");
  const [cGstin, setCGstin] = useState("");
  const [cAddr, setCAddr] = useState("");

  const [supCode, setSupCode] = useState("");
  const [supName, setSupName] = useState("");
  const [supMobile, setSupMobile] = useState("");
  const [supWa, setSupWa] = useState("");
  const [supGstin, setSupGstin] = useState("");
  const [supAddr, setSupAddr] = useState("");

  const [calNo, setCalNo] = useState("");
  const [calVerify, setCalVerify] = useState("");
  const [calDue, setCalDue] = useState("");
  const [calOfficer, setCalOfficer] = useState("");
  const [calTitle, setCalTitle] = useState("");
  const [calMake, setCalMake] = useState("TRUWEIGH SYSTEM");
  const [calMax, setCalMax] = useState("60000");
  const [calMin, setCalMin] = useState("200");
  const [calClass, setCalClass] = useState("Class III");
  const [calE, setCalE] = useState("10");
  const [calD, setCalD] = useState("10");
  const [calSeals, setCalSeals] = useState("2");
  const [calSealsNote, setCalSealsNote] = useState("Indicator & JB");
  const [calLoc, setCalLoc] = useState("JV Industries Weighbridge — Chittoor");

  const [uCode, setUCode] = useState("");
  const [uName, setUName] = useState("");
  const [uPass, setUPass] = useState("");
  const [uRole, setURole] = useState("SECURITY");

  const refresh = async () => {
    if (!token) return;
    setError(null);
    try {
      const [p, s, cust, sup, cal] = await Promise.all([
        api.listProducts(token),
        api.listStorageUnits(token),
        api.listCustomers(token),
        api.listSuppliers(token),
        api.listCalibrations(token).catch(() => [] as api.Calibration[]),
      ]);
      setProducts(p);
      setUnits(s);
      setCustomers(cust);
      setSuppliers(sup);
      setCals(cal);
      if (!sProductId && p[0]) setSProductId(p[0].id);
      if (canUsers) {
        const [us, rs] = await Promise.all([api.listUsers(token), api.listRoleCodes(token)]);
        setUsers(us);
        setRoles(rs);
        if (rs.length && !rs.includes(uRole)) setURole(rs[0]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load masters");
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!token) return null;

  const onProduct = async (e: FormEvent) => {
    e.preventDefault();
    if (!canMaster) return;
    setError(null);
    try {
      await api.createProduct(token, {
        code: pCode,
        name: pName,
        hsn: pHsn || undefined,
        unit: pUnit,
        density_default: pDensity ? Number(pDensity) : undefined,
        loss_limit_percent: Number(pLoss) || 0,
      });
      setPCode("");
      setPName("");
      setPHsn("");
      setPDensity("");
      setInfo("Product created.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create product failed");
    }
  };

  const onStorage = async (e: FormEvent) => {
    e.preventDefault();
    if (!canMaster) return;
    setError(null);
    try {
      await api.createStorageUnit(token, {
        code: sCode,
        name: sName,
        kind: sKind,
        capacity: sCap ? Number(sCap) : undefined,
        capacity_unit: sCapUnit || "L",
        product_id: sProductId || undefined,
        location_label: sLoc || undefined,
      });
      setSCode("");
      setSName("");
      setSCap("");
      setSLoc("");
      setInfo("Storage unit created.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create storage failed");
    }
  };

  const onCustomer = async (e: FormEvent) => {
    e.preventDefault();
    if (!canMaster) return;
    setError(null);
    try {
      await api.createCustomer(token, {
        code: cCode,
        name: cName,
        mobile: cMobile || undefined,
        whatsapp: cWa || cMobile || undefined,
        gstin: cGstin || undefined,
        address: cAddr || undefined,
      });
      setCCode("");
      setCName("");
      setCMobile("");
      setCWa("");
      setCGstin("");
      setCAddr("");
      setInfo("Customer created.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create customer failed");
    }
  };

  const onSupplier = async (e: FormEvent) => {
    e.preventDefault();
    if (!canMaster) return;
    setError(null);
    try {
      await api.createSupplier(token, {
        code: supCode,
        name: supName,
        mobile: supMobile || undefined,
        whatsapp: supWa || supMobile || undefined,
        gstin: supGstin || undefined,
        address: supAddr || undefined,
      });
      setSupCode("");
      setSupName("");
      setSupMobile("");
      setSupWa("");
      setSupGstin("");
      setSupAddr("");
      setInfo("Supplier created.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create supplier failed");
    }
  };

  const onCalibration = async (e: FormEvent) => {
    e.preventDefault();
    if (!canMaster) return;
    setError(null);
    try {
      await api.createCalibration(token, {
        certificate_no: calNo,
        verification_date: calVerify || undefined,
        next_due_date: calDue || undefined,
        officer_name: calOfficer || undefined,
        officer_title: calTitle || undefined,
        make_model: calMake || undefined,
        max_capacity_kg: calMax ? Number(calMax) : undefined,
        min_capacity_kg: calMin ? Number(calMin) : undefined,
        accuracy_class: calClass || undefined,
        e_value_kg: calE ? Number(calE) : undefined,
        d_value_kg: calD ? Number(calD) : undefined,
        seals_count: calSeals ? Number(calSeals) : undefined,
        seals_note: calSealsNote || undefined,
        location_label: calLoc || undefined,
        is_active: true,
      });
      setCalNo("");
      setInfo("Calibration certificate saved (set as active).");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create calibration failed");
    }
  };

  const onUser = async (e: FormEvent) => {
    e.preventDefault();
    if (!canUsers) return;
    setError(null);
    try {
      await api.createUser(token, {
        user_code: uCode,
        full_name: uName,
        password: uPass,
        role_codes: [uRole],
      });
      setUCode("");
      setUName("");
      setUPass("");
      setInfo("User created.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create user failed");
    }
  };

  const tabs: Tab[] = ["products", "storage", "customers", "suppliers", "calibration", "users"];

  return (
    <AppShell title="Masters" subtitle="Products · storage · parties · calibration · users" backTo="/more" wide>
      {info && (
        <div className="panel" style={{ padding: "1rem" }}>
          {info}
        </div>
      )}
      {error && <div className="err">{error}</div>}

      <div className="seg-tabs" role="tablist">
        {tabs.map((t) => (
          <button
            key={t}
            type="button"
            className={tab === t ? "seg-tab active" : "seg-tab"}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "products" && (
        <section className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.2rem" }}>
            Products
          </div>
          {!canMaster && <div className="muted">View only — need master.manage to add.</div>}
          {canMaster && (
            <form className="stack" onSubmit={onProduct}>
              <div className="field"><label>Code *</label><input value={pCode} onChange={(e) => setPCode(e.target.value)} required /></div>
              <div className="field"><label>Name *</label><input value={pName} onChange={(e) => setPName(e.target.value)} required /></div>
              <div className="field"><label>HSN</label><input value={pHsn} onChange={(e) => setPHsn(e.target.value)} /></div>
              <div className="field"><label>Unit</label>
                <select value={pUnit} onChange={(e) => setPUnit(e.target.value)}>
                  <option value="KG">KG</option>
                  <option value="L">L</option>
                </select>
              </div>
              <div className="field"><label>Default density (kg/L)</label><input value={pDensity} onChange={(e) => setPDensity(e.target.value)} inputMode="decimal" placeholder="0.845" /></div>
              <div className="field"><label>Loss limit %</label><input value={pLoss} onChange={(e) => setPLoss(e.target.value)} /></div>
              <button className="btn btn-primary" type="submit">Add product</button>
            </form>
          )}
          <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {products.map((p) => (
              <li key={p.id}>
                <strong>{p.code}</strong> — {p.name} ({p.unit})
                {p.hsn ? ` · HSN ${p.hsn}` : ""}
                {p.density_default != null ? ` · d=${p.density_default}` : ""}
                {` · loss≤${p.loss_limit_percent}%`}
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "storage" && (
        <section className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.2rem" }}>Storage (Tank / Barrel / IBC)</div>
          {canMaster && (
            <form className="stack" onSubmit={onStorage}>
              <div className="field"><label>Code *</label><input value={sCode} onChange={(e) => setSCode(e.target.value)} required /></div>
              <div className="field"><label>Name *</label><input value={sName} onChange={(e) => setSName(e.target.value)} required /></div>
              <div className="field"><label>Kind</label>
                <select value={sKind} onChange={(e) => setSKind(e.target.value)}>
                  <option value="TANK">TANK</option>
                  <option value="BARREL">BARREL</option>
                  <option value="IBC">IBC</option>
                </select>
              </div>
              <div className="field"><label>Capacity</label><input value={sCap} onChange={(e) => setSCap(e.target.value)} inputMode="decimal" /></div>
              <div className="field"><label>Capacity unit</label>
                <select value={sCapUnit} onChange={(e) => setSCapUnit(e.target.value)}>
                  <option value="L">L</option>
                  <option value="KG">KG</option>
                </select>
              </div>
              <div className="field"><label>Default product</label>
                <select value={sProductId} onChange={(e) => setSProductId(e.target.value)}>
                  <option value="">—</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
                  ))}
                </select>
              </div>
              <div className="field"><label>Location</label><input value={sLoc} onChange={(e) => setSLoc(e.target.value)} placeholder="Main yard" /></div>
              <button className="btn btn-primary" type="submit">Add unit</button>
            </form>
          )}
          <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {units.map((u) => (
              <li key={u.id}>
                <strong>{u.code}</strong> — {u.name} ({u.kind})
                {u.capacity != null ? ` · ${u.capacity} ${u.capacity_unit}` : ""}
                {u.location_label ? ` · ${u.location_label}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "customers" && (
        <section className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.2rem" }}>Customers</div>
          {canMaster && (
            <form className="stack" onSubmit={onCustomer}>
              <div className="field"><label>Code *</label><input value={cCode} onChange={(e) => setCCode(e.target.value)} required /></div>
              <div className="field"><label>Name *</label><input value={cName} onChange={(e) => setCName(e.target.value)} required /></div>
              <div className="field"><label>Mobile</label><input value={cMobile} onChange={(e) => setCMobile(e.target.value)} inputMode="tel" /></div>
              <div className="field"><label>WhatsApp (OTP)</label><input value={cWa} onChange={(e) => setCWa(e.target.value)} inputMode="tel" placeholder="defaults to mobile" /></div>
              <div className="field"><label>GSTIN</label><input value={cGstin} onChange={(e) => setCGstin(e.target.value)} /></div>
              <div className="field"><label>Address</label><input value={cAddr} onChange={(e) => setCAddr(e.target.value)} /></div>
              <button className="btn btn-primary" type="submit">Add customer</button>
            </form>
          )}
          <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {customers.map((c) => (
              <li key={c.id}>
                <strong>{c.code}</strong> — {c.name}
                {c.mobile ? ` · ${c.mobile}` : ""}
                {c.whatsapp ? ` · WA ${c.whatsapp}` : ""}
                {c.gstin ? ` · ${c.gstin}` : ""}
                {c.address ? ` · ${c.address}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "suppliers" && (
        <section className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.2rem" }}>Suppliers</div>
          {canMaster && (
            <form className="stack" onSubmit={onSupplier}>
              <div className="field"><label>Code *</label><input value={supCode} onChange={(e) => setSupCode(e.target.value)} required /></div>
              <div className="field"><label>Name *</label><input value={supName} onChange={(e) => setSupName(e.target.value)} required /></div>
              <div className="field"><label>Mobile</label><input value={supMobile} onChange={(e) => setSupMobile(e.target.value)} inputMode="tel" /></div>
              <div className="field"><label>WhatsApp</label><input value={supWa} onChange={(e) => setSupWa(e.target.value)} inputMode="tel" /></div>
              <div className="field"><label>GSTIN</label><input value={supGstin} onChange={(e) => setSupGstin(e.target.value)} /></div>
              <div className="field"><label>Address</label><input value={supAddr} onChange={(e) => setSupAddr(e.target.value)} /></div>
              <button className="btn btn-primary" type="submit">Add supplier</button>
            </form>
          )}
          <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {suppliers.map((s) => (
              <li key={s.id}>
                <strong>{s.code}</strong> — {s.name}
                {s.mobile ? ` · ${s.mobile}` : ""}
                {s.gstin ? ` · ${s.gstin}` : ""}
                {s.address ? ` · ${s.address}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "calibration" && (
        <section className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.2rem" }}>Weighbridge calibration</div>
          <p className="muted" style={{ margin: 0 }}>
            Legal Metrology certificate used on weighment slips. Creating a new active cert deactivates the previous one.
          </p>
          {canMaster && (
            <form className="stack" onSubmit={onCalibration}>
              <div className="field"><label>Certificate no. *</label><input value={calNo} onChange={(e) => setCalNo(e.target.value)} required /></div>
              <div className="field"><label>Verification date</label><input type="date" value={calVerify} onChange={(e) => setCalVerify(e.target.value)} /></div>
              <div className="field"><label>Next due date</label><input type="date" value={calDue} onChange={(e) => setCalDue(e.target.value)} /></div>
              <div className="field"><label>Officer name</label><input value={calOfficer} onChange={(e) => setCalOfficer(e.target.value)} /></div>
              <div className="field"><label>Officer title</label><input value={calTitle} onChange={(e) => setCalTitle(e.target.value)} /></div>
              <div className="field"><label>Make / model</label><input value={calMake} onChange={(e) => setCalMake(e.target.value)} /></div>
              <div className="field"><label>Max capacity (kg)</label><input value={calMax} onChange={(e) => setCalMax(e.target.value)} inputMode="decimal" /></div>
              <div className="field"><label>Min capacity (kg)</label><input value={calMin} onChange={(e) => setCalMin(e.target.value)} inputMode="decimal" /></div>
              <div className="field"><label>Accuracy class</label><input value={calClass} onChange={(e) => setCalClass(e.target.value)} /></div>
              <div className="field"><label>e-value (kg)</label><input value={calE} onChange={(e) => setCalE(e.target.value)} inputMode="decimal" /></div>
              <div className="field"><label>d-value (kg)</label><input value={calD} onChange={(e) => setCalD(e.target.value)} inputMode="decimal" /></div>
              <div className="field"><label>Seals count</label><input value={calSeals} onChange={(e) => setCalSeals(e.target.value)} inputMode="numeric" /></div>
              <div className="field"><label>Seals note</label><input value={calSealsNote} onChange={(e) => setCalSealsNote(e.target.value)} /></div>
              <div className="field"><label>Location</label><input value={calLoc} onChange={(e) => setCalLoc(e.target.value)} /></div>
              <button className="btn btn-primary" type="submit">Save as active certificate</button>
            </form>
          )}
          <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {cals.map((c) => (
              <li key={c.id}>
                <strong>{c.certificate_no}</strong>
                {c.is_active ? " · ACTIVE" : ""}
                {c.make_model ? ` · ${c.make_model}` : ""}
                {c.next_due_date ? ` · due ${c.next_due_date}` : ""}
              </li>
            ))}
            {cals.length === 0 && <li>No certificates yet.</li>}
          </ul>
        </section>
      )}

      {tab === "users" && (
        <section className="panel stack" style={{ padding: "1.25rem" }}>
          <div className="brand-mark" style={{ fontSize: "1.2rem" }}>Users</div>
          {!canUsers && <div className="err">Need user.manage permission.</div>}
          {canUsers && (
            <form className="stack" onSubmit={onUser}>
              <div className="field"><label>User ID</label><input value={uCode} onChange={(e) => setUCode(e.target.value)} required /></div>
              <div className="field"><label>Full name</label><input value={uName} onChange={(e) => setUName(e.target.value)} required /></div>
              <div className="field"><label>Password</label><input type="password" value={uPass} onChange={(e) => setUPass(e.target.value)} required /></div>
              <div className="field"><label>Role</label>
                <select value={uRole} onChange={(e) => setURole(e.target.value)}>
                  {roles.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
              <button className="btn btn-primary" type="submit">Add user</button>
            </form>
          )}
          <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {users.map((u) => (
              <li key={u.id}>
                <strong>{u.user_code}</strong> — {u.full_name} [{u.roles.join(", ")}]
                {u.is_active ? "" : " (inactive)"}
              </li>
            ))}
          </ul>
        </section>
      )}
    </AppShell>
  );
}
