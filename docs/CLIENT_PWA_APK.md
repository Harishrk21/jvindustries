# JV-OMS client: PWA + Android APK

One UI codebase (`/web`) serves both:

1. **PWA** — install from Chrome/Edge (“Add to Home Screen”)
2. **Android APK** — Capacitor wraps the same build

The older Kotlin `/mobile` project is legacy; new work targets `/web`.

## Stack

- React 18 + TypeScript + Vite
- vite-plugin-pwa (service worker + manifest)
- Capacitor 6 (Camera, Geolocation)
- Tesseract.js OCR in browser / on-device path
- FastAPI backend + **MySQL only**

## Develop (PWA)

```powershell
# Terminal 1 — API (MySQL must be ready)
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Terminal 2 — web
cd web
npm install
npm run dev
```

Open http://127.0.0.1:5173 — Vite proxies `/api` → `:8080`.

## Install as PWA

1. Open the site in Chrome (HTTPS or localhost)
2. Menu → **Install app** / Add to Home screen
3. Launches standalone like a native app

## Build Android APK

```powershell
cd web
npm run build
npx cap add android   # first time only
npx cap sync android
npx cap open android
```

In Android Studio: Build → Build APK(s).  
For a physical phone, set API base to your PC LAN IP via `VITE_API_BASE=http://192.168.x.x:8080` before `npm run build`.

## Offline drafts (Phase 11)

- Screen: **Offline queue** (`/offline`) — stores drafts in `localStorage`.
- Sync: `POST /api/v1/sync/push` when online; conflicts stay on device until discarded.
- Service worker caches the shell; API calls still need network for sync.

## Production checklist

See `docs/PHASE11_PRODUCTION.md` and **`docs/GO_LIVE.md`** (cutover + `scripts/smoke-live.ps1`).

## MySQL

See `database/setup_mysql.sql` and `scripts/setup-mysql.ps1`.
