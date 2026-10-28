# JV-OMS Implementation Plan

## Project

**JV Industries Operations Management System (JV-OMS)**  
Production Android APK + FastAPI + PostgreSQL platform for JV Industries, India.

## Stack decision (Flutter removed)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Mobile | **Kotlin + Jetpack Compose** (native Android) | Produces installable APK/AAB; full CameraX, GPS, offline, secure storage |
| Architecture | Clean Architecture: Presentation / Domain / Data | Maintainable, testable |
| State | ViewModel + StateFlow / UiState | Idiomatic Android |
| Local DB | Room (SQLite) | Offline queue + sync |
| DI | Hilt | Standard Android DI |
| Networking | Retrofit + OkHttp | Typed REST client |
| Secure storage | EncryptedSharedPreferences / DataStore | JWT, device secrets |
| Camera | CameraX (LIVE only for operators) | Enforce capture_source |
| Backend | Python FastAPI + SQLAlchemy + Alembic | Unchanged from requirements |
| Database | PostgreSQL | Unchanged |
| Storage | S3-compatible object storage | Evidence originals |
| Messaging | Official WhatsApp Business API | OTP + notifications |
| AI | Provider-agnostic service interfaces | Mock until credentials exist |

**Deliverable for testing:** signed/debug **APK** installable on Android phones.

---

## Working method

1. Docs first (this plan + architecture set) — **current step**
2. Phase 1 foundation only until stable and tests pass
3. Then Phases 2–11 sequentially; never skip rules for convenience

---

## Phase overview

### PHASE 1 — Foundation (start after docs)
- Android project (Gradle, Compose, Hilt, Room, Retrofit)
- FastAPI project skeleton
- PostgreSQL + Alembic migrations
- Users, roles, permissions, devices
- JWT auth + secure config
- Transaction model + Transaction ID generator (`JV-YYYY-NNNNNN`)
- Audit trail foundation (append-only)
- GPS/geofence service abstraction
- Dashboard shell (role-aware)
- Basic unit/API tests
- Debug APK build path documented

### PHASE 2 — Vehicle / Gate
- Vehicle entry/exit, ANPR interface, gate pass, GPS enforcement

### PHASE 3 — Weighbridge
- Tare / Gross / Net (server-authoritative), density, calculated litres

### PHASE 4 — Documents
- Invoice + E-Way Bill live capture, OCR/QR interfaces, vehicle mismatch rules

### PHASE 5 — Storage & Stock
- Product master, Tank/Barrel/IBC, stock engine

### PHASE 6 — Job Work & Loss & OTP
- Batches, production loss, customer OTP (WhatsApp abstraction)

### PHASE 7 — WhatsApp / PDF / Notifications
- Official API, PDFs, management alerts

### PHASE 8 — Equipment
- Repair out, return, disposal + approvals

### PHASE 9 — Canteen
- Purchase, OCR confirm, stock

### PHASE 10 — Reports
- Daily/monthly/custom, PDF/Excel, share

### PHASE 11 — Offline / Hardening / Production
- Sync, conflict policy, security tests, deployment

### Status
**Phases 1–11 complete** (stack: React PWA + Capacitor, FastAPI, MySQL/Aiven — see `STACK_CHANGE_FROM_FLUTTER.md`).  
Go-live cutover: `docs/GO_LIVE.md` + `scripts/smoke-live.ps1`.

---

## Non-negotiables

- One **Transaction ID** links all related records
- Live camera only for normal operators; Owner gallery = `OWNER_GALLERY_UPLOAD`
- Server recalculates net, litres, loss %, stock
- Audit append-only; no silent overwrite
- No fake OCR/ANPR claiming to work without configured services — use clearly marked **MOCK** implementations
- Do not invent business rules; flag ambiguities

---

## Ambiguities to resolve later (do not invent)

1. Exact geofence polygon vs circle defaults for JV premises (config by Owner)
2. Which transaction types require customer OTP by default
3. Exact WhatsApp template names (Meta Business)
4. Preferred AI provider for ANPR/OCR in production
5. Whether weighbridge TRUWEIGH serial/API will be available in Phase 3 or later

---

## Exit criteria for Phase 1

- Backend boots; migrations apply; auth login returns JWT
- Roles/permissions seed; unauthorized API rejected
- Transaction ID generation works
- Audit log written on auth/device register
- Android app builds debug APK; login + empty dashboard shell
- Geofence service interface + configurable radius (unit-tested)
- Tests green for Phase 1 scope
