# Phase 11 — Offline / Hardening / Production

## What shipped

| Area | Detail |
|------|--------|
| Sync API | `GET /api/v1/sync/policy`, `POST /api/v1/sync/push` |
| Conflict policy | Idempotent on same `client_transaction_id`; CONFLICT if type mismatch or status past DRAFT/ENTRY_STARTED |
| Client queue | PWA `localStorage` queue + Offline page (`/offline`) |
| Production guards | Weak JWT / DEBUG / open CORS fail closed when `APP_ENV=production` |
| Health | `/health` returns `readiness[]` warnings/errors |

## Conflict policy (operators)

1. Queue drafts offline with a stable UUID (`client_transaction_id`).
2. When online, **Sync now** pushes the queue.
3. **CREATED** / **IDEMPOTENT** → draft removed from device queue.
4. **CONFLICT** → kept on device with message; discard and start a new draft (new UUID). Server never silently overwrites progressed work.

## Production env checklist

Set before go-live:

```env
APP_ENV=production
DEBUG=false
JWT_SECRET=<≥32 char random>
CORS_ORIGINS=https://your-pwa-origin.example
DATABASE_URL=mysql+pymysql://...@aiven-host:port/jvoms?charset=utf8mb4
MYSQL_SSL_REQUIRED=true
MYSQL_SSL_CA=/path/to/aiven-ca.pem
```

Optional: WhatsApp / object storage keys only if those features are enabled.

Startup calls `assert_production_ready()` — weak secret, `DEBUG=true`, or `CORS_ORIGINS=*` will **refuse to boot** in production.

## Deploy steps (short)

1. Migrate/create MySQL schema (`alembic upgrade head` or app `create_all` + seed).
2. Set production env; confirm `/health` → `status=ok` and empty ERROR readiness.
3. Build web: `cd web && npm ci && npm run build` (set `VITE_API_BASE` for APK/LAN).
4. Serve PWA (HTTPS) + run API behind reverse proxy (TLS).
5. Android: `npx cap sync android` → Build APK (see `CLIENT_PWA_APK.md`).
6. Smoke: login → Offline queue → Sync → create one live vehicle entry with GPS.

## Verify

```powershell
cd backend
.\.venv\Scripts\activate
pytest tests/test_sync_policy.py tests/test_production_readiness.py tests/test_phase11_sync_security.py -q
curl http://127.0.0.1:8080/health
```

Live: login as owner → **Offline queue** → Save offline → Sync now → confirm `JV-…` on server.
