# Phase B — Master data (locked)

Supports yard, slips, and later commercial PDFs with clean lookups.

## Masters

| Master | Key fields | Used by |
|--------|------------|---------|
| **Products** | code, name, HSN, unit (KG/L), default density, loss % | Gate, stock, job-work |
| **Storage** | code, name, kind (TANK/BARREL/IBC), capacity + unit, product, location | Gate assign, stock |
| **Customers** | code, name, mobile, WhatsApp, GSTIN, address | Outward close / OTP / statements |
| **Suppliers** | same as customers | Inward close / statements |
| **Calibration** | cert no., verify/due dates, officer, make/model, capacities, class, e/d, seals | Weighment slip PDF |
| **Users** | already present | RBAC |

## Seeded defaults
- Product `FUEL_OIL`, tank `T-03`, barrel `B-01`, IBC `IBC-01`
- Customers `CUST-ABC`, `SAI-PETRO`; supplier `SUP-XYZ`
- Active calibration `CTR72521126R0563` (TRUWEIGH / Class III)

## APIs
- `GET/POST /api/v1/calibration`
- `GET /api/v1/calibration/active`
- Party create accepts `whatsapp` + `address`
- Customer weighment PDF includes active calibration block

## UI
Masters → tabs: products · storage · customers · suppliers · **calibration** · users

## Smoke checklist
1. Login as `owner` / `Owner@123`
2. Masters → see seeded products/tanks/parties/calibration ACTIVE
3. Create a customer with WhatsApp + address
4. Yard outward close → WhatsApp prefilled from customer
5. `GET /api/v1/calibration/active` returns cert no.
