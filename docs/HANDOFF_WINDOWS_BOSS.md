# JV-OMS — Windows handoff (boss laptop)

**Stack:** React PWA (`web/`) + Capacitor Android + FastAPI (`backend/`) + **MySQL via Aiven (cloud)**.  
**Do not use** PostgreSQL / SQLite for the app database.

**Blueprint status (done / not done):** [`BLUEPRINT_STATUS.md`](./BLUEPRINT_STATUS.md)

`backend/.env` is committed with **Aiven MySQL** + **Groq API key** so you can clone and run **without installing MySQL** and **without pasting keys**.

---

## Fastest path (after clone) — no MySQL install

```powershell
cd D:\
git clone https://github.com/Harishrk21/jvindustries.git
cd jvindustries

# Window 1 — API
.\scripts\start-backend.ps1

# Window 2 — Web
.\scripts\start-web.ps1
# → http://127.0.0.1:5173   login: owner / Owner@123
```

Health check: http://127.0.0.1:8080/health

---

## 0) Prerequisites (install once)

| Software | Notes |
|----------|--------|
| **Windows 10/11** | PowerShell 5+ |
| **Git** | For clone |
| **Python 3.11+** | `python --version` (Add to PATH) |
| **Node.js 20+** | `node -v` / `npm -v` |
| **Android Studio** (optional) | Only if building APK |

**Not required:** local MySQL Server (app uses Aiven cloud DB in `.env`).

If PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 1) Clone

```powershell
cd D:\
git clone https://github.com/Harishrk21/jvindustries.git
cd jvindustries
```

Confirm folders: `backend`, `web`, `database`, `docs`, `scripts`.

---

## 2) Backend API (port 8080)

`.env` already points at Aiven. No DB setup step.

```powershell
cd D:\jvindustries
.\scripts\start-backend.ps1
```

Or manually:

```powershell
cd D:\jvindustries\backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Check health

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health | ConvertTo-Json -Depth 5
```

Expect:

- `status`: `ok`
- `whatsapp.provider`: `mock_whatsapp`
- `whatsapp.allow_mock`: `true`
- `evidence.writable`: `true`

API docs: http://127.0.0.1:8080/docs  

Tables + seed users are created on first API boot.

---

## 3) Web PWA (port 5173)

```powershell
cd D:\jvindustries
.\scripts\start-web.ps1
```

Open: http://127.0.0.1:5173

---

## 4) Seeded logins

| User ID | Password | Role |
|---------|----------|------|
| owner | Owner@123 | OWNER_ADMIN |
| supervisor | Super@123 | SUPERVISOR |
| security | Security@123 | SECURITY |
| weighbridge | Weigh@123 | WEIGHBRIDGE_OPERATOR |
| store | Store@123 | STORE_OPERATOR |
| production | Prod@123 | PRODUCTION_OPERATOR |
| canteen | Canteen@123 | CANTEEN_OPERATOR |

Full map: `docs/ROLE_LOGIN_MAP.md`

---

## 5) Optional smoke tests

With API on 8080:

```powershell
cd D:\jvindustries
.\scripts\smoke-live.ps1
.\scripts\verify-roles.ps1
```

---

## 6) Android APK (optional)

```powershell
cd D:\jvindustries\web
npm run build
npx cap sync android
npx cap open android
```

---

## 7) Troubleshooting

| Symptom | Fix |
|---------|-----|
| `DATABASE_UNAVAILABLE` / DNS fail to Aiven host | Check Aiven console — service must be **running**; try another network/DNS. Fallback: install local MySQL and switch `DATABASE_URL` (see `database/setup_mysql.sql`) |
| Port 8080 in use | Stop other uvicorn |
| OTP | Use on-screen `otp_preview` (mock WhatsApp) |
| Forced password change | Only when `APP_ENV=production` |

Test Aiven from project:

```powershell
cd D:\jvindustries\backend
.\.venv\Scripts\python ..\scripts\test-aiven-mysql.py
```

---

## 8) Related docs

| Doc | Purpose |
|-----|---------|
| `docs/BLUEPRINT_STATUS.md` | What’s done vs not done |
| `docs/ROLE_LOGIN_MAP.md` | Roles / modules |
| `docs/GO_LIVE.md` | Production cutover |
| `database/setup_mysql.sql` | **Optional** local MySQL only if Aiven unreachable |
