# JV-OMS Go-Live phases (ASAP path)

Implement **one phase at a time**. Do not skip verification.

| Phase | Scope | Exit when |
|-------|--------|-----------|
| **A** | Production cutover readiness: env template, geofence API, smoke, PWA build, Capacitor sync | `verify-phase-a.ps1` → `PHASE_A_OK` |
| **B** | WhatsApp + evidence storage readiness | OTP/alert path verified (mock or live); evidence dir/cloud writable |
| **C** | Dry-run inward + outward operator paths | `python scripts/verify_phase_c.py` → `PHASE_C_OK` (+ device camera later) |
| **D** | Search/timeline + approvals/exceptions inbox | UI + API tests green |
| **E** | Customers/suppliers + exit/closure rules | Masters + blocked close without docs/OTP |
| **F** | Day-0 cutover: passwords, JWT, roles smoke | `prepare-cutover.ps1` → `CUTOVER_PREP_OK` + `ROLES_OK` |

---

## Phase A — checklist

1. Use `backend/.env.production.example` as the production template (fill real values; never commit secrets).
2. Geofence: owner sets real yard coords in **Settings** (or PUT `/api/v1/geofence/config`).
3. API healthy: `/health` → `status=ok`; production boot refuses weak JWT / DEBUG / open CORS.
4. `scripts/smoke-live.ps1` → `SMOKE_OK`.
5. `scripts/verify-phase-a.ps1` → `PHASE_A_OK`.
6. `cd web && npm run build && npx cap sync android` succeeds.

## Phase B — checklist

1. `WHATSAPP_*` filled **or** mock accepted for staging only (`/health.whatsapp`).
2. `EVIDENCE_ROOT` writable (`/health.evidence.writable`).
3. `scripts/verify-phase-b.ps1` → `PHASE_B_OK` (OTP send/verify + alert).

## Phase D — checklist

1. Search: `GET /api/v1/transactions?q=&status=&type=` returns paged hits.
2. Timeline: `GET /api/v1/transactions/{id}/timeline` ordered events.
3. Inbox: `GET /api/v1/approvals` + `GET /api/v1/exceptions`.
4. UI: **More → Search & Inbox** (and dashboard Approvals/Exceptions KPIs).
5. `python scripts/verify_phase_d.py` → `PHASE_D_OK`.

## Phase E — checklist

1. Masters: `CRUD /api/v1/customers` + `/api/v1/suppliers` (UI: Masters tabs).
2. Link: `POST /api/v1/transactions/{id}/parties`.
3. Closure: `GET /api/v1/transactions/{id}/closure-check`.
4. Exit with `complete_transaction=true` blocked (409) without docs/OTP/gate pass/party by type.
5. `python scripts/verify_phase_e.py` → `PHASE_E_OK`.

## Phase F — day-0 cutover checklist

1. `scripts/prepare-cutover.ps1` — prints JWT + checklist; runs role smoke.
2. Host `.env` from `backend/.env.production.example` (strong `JWT_SECRET`, `DEBUG=false`, explicit CORS).
3. Each seeded user changes password (`POST /api/v1/auth/change-password` or Settings / forced `/change-password`).
4. `/health` must not report `DEFAULT_SEED_PASSWORDS` as ERROR in production.
5. Owner sets real JV geofence in Settings.
6. WhatsApp: Meta credentials for live OTP, or mock only on staging (`/health.whatsapp`).

## Roles for day-1

| User ID | Role | Default (change on go-live) |
|---------|------|------------------------------|
| owner | OWNER_ADMIN | Owner@123 |
| security | SECURITY | Security@123 |
| weighbridge | WEIGHBRIDGE_OPERATOR | Weigh@123 |
| store | STORE_OPERATOR | Store@123 |

Forced password change applies while the account still uses the seed default.
