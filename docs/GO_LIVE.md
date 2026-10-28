# JV-OMS Go-Live (post Phase 11)

Phases **1–11** are implemented. This pack is the production cutover checklist.

**Phased ASAP path:** see `docs/GO_LIVE_PHASES.md` (A→E).  
Phase A verify: `scripts/verify-phase-a.ps1`

## Pre-flight

| Check | Action |
|-------|--------|
| MySQL (Aiven) | `DATABASE_URL` + `MYSQL_SSL_REQUIRED=true` + CA file |
| Secrets | `APP_ENV=production`, `DEBUG=false`, `JWT_SECRET` ≥32 random chars |
| CORS | Explicit PWA/APK origins only (no `*`) |
| Geofence | Real JV lat/lon/radius (not Chennai demo defaults) |
| WhatsApp | Optional — `WHATSAPP_ALLOW_MOCK=true` accepted (on-screen OTP). Meta later. |
| Evidence | `EVIDENCE_ROOT` writable or S3 keys set |

Copy `backend/.env.example` → `.env` and fill production values. Startup **refuses** weak JWT / DEBUG / open CORS in production.

## Deploy API

```powershell
cd backend
.\.venv\Scripts\activate
# alembic upgrade head   # preferred when migration chain is used
uvicorn app.main:app --host 0.0.0.0 --port 8080
# Put nginx/Caddy TLS in front; do not expose DEBUG
```

Confirm: `GET /health` → `status=ok` and no `ERROR` items in `readiness`.

## Deploy PWA

```powershell
cd web
npm ci
# VITE_API_BASE=https://api.your-domain.example
npm run build
# Serve dist/ over HTTPS (same origin or CORS-listed)
```

## Android APK (Capacitor)

```powershell
cd web
npm run build
npx cap add android   # once
npx cap sync android
npx cap open android  # Build → Build APK(s)
```

Set `VITE_API_BASE` to the reachable API (HTTPS or LAN IP for debug) **before** `npm run build`.

## Smoke after deploy

```powershell
cd scripts
.\smoke-live.ps1 -BaseUrl https://api.your-domain.example
# or local:
.\smoke-live.ps1 -BaseUrl http://127.0.0.1:8080
```

Expect `SMOKE_OK` and no failed steps.

## Day-0 cutover (passwords + roles)

```powershell
cd scripts
.\prepare-cutover.ps1 -BaseUrl http://127.0.0.1:8080
# expect CUTOVER_PREP_OK and ROLES_OK
```

Paste the printed `JWT_SECRET` into the production host `.env`.  
Login once per role and complete **Change password** (seed users are flagged until rotated).

## Day-1 operator path

1. Login (owner / security / weighbridge / store as needed)
2. Vehicle entry (live camera + GPS)
3. Weighment → documents → stock as required
4. Offline queue: save draft → sync
5. One PDF download + one report export

## Still config (do not invent)

- Real geofence coords (Settings) — not Chennai demo
- WhatsApp Meta template names + token
- Production OCR/ANPR provider keys
- TRUWEIGH serial/API if hardware is online
