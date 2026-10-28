# JV-OMS — Windows handoff (boss laptop)

**Stack:** React PWA (`web/`) + Capacitor Android + FastAPI (`backend/`) + **MySQL 8 only**.  
**Do not use** PostgreSQL / SQLite for the app database.

**Blueprint status (done / not done):** [`BLUEPRINT_STATUS.md`](./BLUEPRINT_STATUS.md)

This repo includes `backend/.env` for local development (shared intentionally for handoff). Treat secrets carefully; rotate JWT / Groq / DB password before public hosting.

### Fastest path (after clone)

```powershell
# 1) MySQL once
.\scripts\setup-mysql.ps1 -RootPassword "YOUR_MYSQL_ROOT_PASSWORD"

# 2) API (new PowerShell window)
.\scripts\start-backend.ps1

# 3) Web (another window)
.\scripts\start-web.ps1
# → http://127.0.0.1:5173   login: owner / Owner@123
```

---

## 0) Prerequisites (install once)

| Software | Notes |
|----------|--------|
| **Windows 10/11** | PowerShell 5+ |
| **MySQL Server 8.0** | Include `mysql.exe` on PATH or default install path |
| **Python 3.11+** | `python --version` |
| **Node.js 20+** | `node -v` / `npm -v` |
| **Git** | For clone/push |
| **Android Studio** (optional) | Only if building APK |

Default MySQL client path used by scripts:

`C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`

---

## 1) Clone / open project

```powershell
cd D:\
git clone <YOUR_REPO_URL> mobile-app-jv
cd mobile-app-jv
```

Confirm folders: `backend`, `web`, `database`, `docs`, `scripts`.

---

## 2) MySQL — create database + user

### Option A — PowerShell script (recommended)

```powershell
cd D:\mobile-app-jv
.\scripts\setup-mysql.ps1 -RootPassword "YOUR_MYSQL_ROOT_PASSWORD"
```

### Option B — manual SQL (as MySQL root)

Open **MySQL Command Line Client** or:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```

Paste:

```sql
CREATE DATABASE IF NOT EXISTS jvoms
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS jvoms_test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'jvoms'@'localhost' IDENTIFIED BY 'JvOms@2026';
CREATE USER IF NOT EXISTS 'jvoms'@'%' IDENTIFIED BY 'JvOms@2026';

GRANT ALL PRIVILEGES ON jvoms.* TO 'jvoms'@'localhost';
GRANT ALL PRIVILEGES ON jvoms.* TO 'jvoms'@'%';
GRANT ALL PRIVILEGES ON jvoms_test.* TO 'jvoms'@'localhost';
GRANT ALL PRIVILEGES ON jvoms_test.* TO 'jvoms'@'%';
FLUSH PRIVILEGES;
```

Or from file:

```powershell
Get-Content .\database\setup_mysql.sql -Raw |
  & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p --default-character-set=utf8mb4
```

### Verify connection

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u jvoms -p"JvOms@2026" -e "SHOW DATABASES; SELECT 1 AS ok;"
```

Or:

```powershell
Get-Content .\database\check_mysql.sql -Raw |
  & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u jvoms -p"JvOms@2026" jvoms
```

**App connection string** (already in `backend/.env`):

```text
mysql+pymysql://jvoms:JvOms%402026@127.0.0.1:3306/jvoms?charset=utf8mb4
```

(`@` in password is URL-encoded as `%40`.)

---

## 3) Backend API (port 8080)

```powershell
cd D:\mobile-app-jv\backend

python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt

# Start API (creates tables + seeds roles/users on boot)
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Shortcut:

```powershell
cd D:\mobile-app-jv
.\scripts\start-backend.ps1
```

### Check health

Browser or:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health | ConvertTo-Json -Depth 5
```

Expect:

- `status`: `ok`
- `whatsapp.provider`: `mock_whatsapp` (accepted)
- `whatsapp.allow_mock`: `true`
- `evidence.writable`: `true`

API docs: http://127.0.0.1:8080/docs

Tables are created automatically via SQLAlchemy `create_all` + seed on startup. **No Alembic migrate required for first boot.**

---

## 4) Web PWA (port 5173)

```powershell
cd D:\mobile-app-jv\web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open: http://127.0.0.1:5173

Shortcut:

```powershell
cd D:\mobile-app-jv
.\scripts\start-web.ps1
```

---

## 5) Seeded logins (development)

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

## 6) Smoke / verify (optional)

With API running on 8080:

```powershell
cd D:\mobile-app-jv
.\scripts\smoke-live.ps1
.\scripts\verify-phase-a.ps1
.\scripts\verify-phase-b.ps1
.\scripts\verify-roles.ps1
.\backend\.venv\Scripts\python .\scripts\verify_phase_c.py
.\backend\.venv\Scripts\python .\scripts\verify_phase_e.py
```

Unit tests (uses `jvoms_test` if configured in pytest; otherwise test DB URL in conftest):

```powershell
cd D:\mobile-app-jv\backend
.\.venv\Scripts\python -m pytest tests/test_phase_e_commercial.py tests/test_phase_f_finance.py -q
```

---

## 7) Android APK (optional)

```powershell
cd D:\mobile-app-jv\web
npm run build
npx cap sync android
npx cap open android
```

Build APK in Android Studio. Details: `docs/CLIENT_PWA_APK.md`

---

## 8) What boss can change without coding

| Item | Where |
|------|--------|
| Yard GPS pin | Login as **owner** → Settings → Geofence |
| Passwords | Settings → Change password |
| WhatsApp Meta later | Fill `WHATSAPP_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID` in `.env`, set `WHATSAPP_ALLOW_MOCK=false` only when live |
| Enforce GPS on site | `.env` → `GPS_ENFORCE=true` |
| Groq vision key | `.env` → `GROQ_API_KEY=` (get from https://console.groq.com — not shipped in git; GitHub blocks live keys) |

---

## 9) Troubleshooting

| Symptom | Fix |
|---------|-----|
| `DATABASE_UNAVAILABLE` | Start MySQL service; check `DATABASE_URL` password encoding |
| Access denied for `jvoms` | Re-run `database/setup_mysql.sql` as root |
| Port 8080 in use | Stop other uvicorn / change port |
| Weak JWT warning | Already set strong secret in shipped `.env` |
| OTP | Use on-screen `otp_preview` (mock WhatsApp) |
| Forced password change | Only in `APP_ENV=production`; development keeps seed passwords |

Windows MySQL service:

```powershell
Get-Service -Name "*mysql*"
# Start-Service MySQL80   # name may vary
```

---

## 10) Related docs

| Doc | Purpose |
|-----|---------|
| `docs/BLUEPRINT_STATUS.md` | What’s done vs not done vs blueprint |
| `docs/ROLE_LOGIN_MAP.md` | Roles / modules |
| `docs/GO_LIVE.md` / `GO_LIVE_PHASES.md` | Cutover |
| `docs/IMPLEMENTATION_PLAN.md` | Original plan |
| `docs/PHASE_A_*.md` … `PHASE_F_*.md` | Plant gap phases |
