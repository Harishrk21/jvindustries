# JV-OMS Test Plan

## Strategy

| Layer | Types |
|-------|-------|
| Backend | Unit, integration, API, DB, permission |
| Android | Unit (ViewModel/use case), instrumented where needed, offline queue |
| Business | Calculations + state machine + stock/OTP rules |
| Security | Authz, gallery restriction, token expiry, audit immutability |

Prefer automated tests for every critical business rule. Mocks clearly labeled for AI/WhatsApp when credentials absent.

## Phase 1 tests (must pass before Phase 2)

### Backend
- Login success/failure; lockout policy hooks
- JWT required on protected routes
- Role seed + permission denial (403)
- Device registration binds to user
- Transaction create assigns unique `JV-YYYY-NNNNNN`
- Audit log append on login + device register + transaction create
- Geofence service: inside/outside + accuracy fail
- Config loads from env; secrets not in code

### Android
- App builds debug APK
- Login screen → token stored encrypted
- Role-based dashboard routes visible/hidden
- Geofence use-case unit tests with fake location provider

## Sample business fixtures (later phases)

### Weighment / density — JV-2026-001258
- Vehicle TN 09 AB 1234, Customer ABC Industries, Fuel Oil, Tank T-03
- Tare 11,820; Gross 45,110; Net 33,290
- Density 0.845 @ 30°C → litres 39,396.45
- Assert server net/litres, PDF fields, OTP payload, audit chain

### Job work
- In 100,000; Out 97,500; Loss 2.50%; Allowed 2.00% → Excess 0.50% → APPROVAL REQUIRED

### Stock
- T-03: Open 100,000 + Recv 200,000 − Load 150,000 = Close 150,000

### Canteen
- OCR extract Rice/Dal/Oil → confirm → stock + original image retained

## Security tests
- Non-owner cannot upload gallery evidence
- Cannot escalate role via API body
- Expired JWT rejected
- Audit UPDATE/DELETE denied for app roles
- GPS spoof resistance: accuracy threshold + server validation (document residual risk)

## Phase 11 — Offline / hardening
- `tests/test_sync_policy.py` — IDEMPOTENT vs CONFLICT decisions
- `tests/test_production_readiness.py` — production refuses weak JWT / DEBUG / open CORS
- `tests/test_phase11_sync_security.py` — sync push create/replay/conflict; `/health` readiness; bad JWT → 401
- Manual: Offline queue → Save offline → Sync now → CREATED; replay → IDEMPOTENT; type clash → CONFLICT

## Regression rule

After each phase: run prior phase suites; do not delete tests to greenwash builds.

## Manual device testing (APK)
1. Install debug APK on physical Android phone
2. Login as each role; confirm navigation matrix
3. Toggle airplane mode for offline draft (Phase 11 full; Phase 1 smoke)
4. Confirm live camera opens for evidence screens (from Phase 2+)
