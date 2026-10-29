# JV Industries Operations Management System (JV-OMS)

Production **PWA + Android APK** client with **FastAPI** backend and **MySQL 8** database.

> Flutter is not used. PostgreSQL is not used. App data is **MySQL only**.

## Boss / new laptop — start here

1. **Windows run steps:** [`docs/HANDOFF_WINDOWS_BOSS.md`](docs/HANDOFF_WINDOWS_BOSS.md)  
2. **Blueprint done vs not done:** [`docs/BLUEPRINT_STATUS.md`](docs/BLUEPRINT_STATUS.md)  
3. **Logins / roles:** [`docs/ROLE_LOGIN_MAP.md`](docs/ROLE_LOGIN_MAP.md)

`backend/.env` includes **Aiven MySQL** + **Groq key** — no local MySQL install and no key pasting required.

---

## Architecture

| Layer | Technology |
|-------|------------|
| Web / PWA | React + TypeScript + Vite + PWA |
| Android APK | Same web app via **Capacitor** |
| API | Python FastAPI |
| Database | **MySQL (Aiven cloud)** |
| Evidence | Local `evidence_store/` |
| OTP | Mock WhatsApp (Meta optional later) |

```
/web        ← PWA + Capacitor
/backend    ← FastAPI
/database   ← optional local MySQL SQL (fallback only)
/docs       ← plans + handoff
/scripts    ← Windows helpers + verify
```

---

## Fast path (Windows) — clone and run

Needs: **Git + Python 3.11+ + Node 20+** only.

```powershell
git clone https://github.com/Harishrk21/jvindustries.git
cd jvindustries
.\scripts\start-backend.ps1   # window 1 → http://127.0.0.1:8080/health
.\scripts\start-web.ps1       # window 2 → http://127.0.0.1:5173
```

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
