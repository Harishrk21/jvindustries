# JV Industries Operations Management System (JV-OMS)

Production **PWA + Android APK** client with **FastAPI** backend and **MySQL 8** database.

> Flutter is not used. PostgreSQL is not used. App data is **MySQL only**.

## Boss / new laptop — start here

1. **Windows setup + MySQL queries:** [`docs/HANDOFF_WINDOWS_BOSS.md`](docs/HANDOFF_WINDOWS_BOSS.md)  
2. **Blueprint done vs not done:** [`docs/BLUEPRINT_STATUS.md`](docs/BLUEPRINT_STATUS.md)  
3. **Logins / roles:** [`docs/ROLE_LOGIN_MAP.md`](docs/ROLE_LOGIN_MAP.md)

---

## Architecture

| Layer | Technology |
|-------|------------|
| Web / PWA | React + TypeScript + Vite + PWA |
| Android APK | Same web app via **Capacitor** |
| API | Python FastAPI |
| Database | **MySQL 8** |
| Evidence | Local `evidence_store/` |
| OTP | Mock WhatsApp (Meta optional later) |

```
/web        ← PWA + Capacitor
/backend    ← FastAPI
/database   ← MySQL SQL
/docs       ← plans + handoff
/scripts    ← Windows helpers + verify
```

---

## Fast path (Windows)

### 1) MySQL

```powershell
.\scripts\setup-mysql.ps1 -RootPassword "YOUR_MYSQL_ROOT_PASSWORD"
```

Creates DB `jvoms` (+ `jvoms_test`) and user `jvoms` / `JvOms@2026`.  
SQL source: `database/setup_mysql.sql`

### 2) API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Or: `.\scripts\start-backend.ps1`  
Health: http://127.0.0.1:8080/health

`backend/.env` is included in this handoff clone for convenience.

### 3) Web

```powershell
cd web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Or: `.\scripts\start-web.ps1`  
App: http://127.0.0.1:5173  
Login: `owner` / `Owner@123`

---

## Default logins

| User | Password | Role |
|------|----------|------|
| owner | Owner@123 | Full admin |
| supervisor | Super@123 | Approvals / ops |
| security | Security@123 | Gate |
| weighbridge | Weigh@123 | Scale |
| store | Store@123 | Docs / stock |
| production | Prod@123 | Job work |
| canteen | Canteen@123 | Canteen |

---

## Design principles

Industrial JV branding, camera-first yard workflows, GPS geofence, live evidence for operators, server-authoritative net/litres, one Transaction ID spine.
