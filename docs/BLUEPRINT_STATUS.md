# JV-OMS — Complete blueprint status (handoff)

Plant docs covered: Gate Pass, Weighment Slip, Supply & Expense, Distillation recovery, Costing / MoM, and the **10-step software flowchart** (Login → Exit).

Legend: **DONE** · **PARTIAL** · **MOCK** · **NOT DONE** (deferred)

---

## A) Flowchart — 10 steps

| # | Blueprint | Status | Notes |
|---|-----------|--------|-------|
| 1 | Login & access (roles, GPS, device, live camera, dashboard) | **DONE / PARTIAL** | Roles + JWT + role-filtered UI **DONE**. GPS/camera enforced on yard steps. Device register exists; login does not force bind. |
| 2 | Select transaction type | **PARTIAL** | YardFlow: **Inward / Outward**. Job Work, Equipment, Canteen = **separate apps/pages**. |
| 3 | Vehicle entry (photo, ANPR, driver, transporter, GPS, entry GP) | **DONE** | ANPR = OCR / optional Groq vision (not dedicated plate camera hardware). |
| 4 | Document capture (Invoice + E-Way) | **DONE (order differs)** | Happy path = **after weigh/density** (safer). Blueprint showed docs earlier. |
| 5 | Weighbridge empty / tare | **DONE** | Outward: tare → load → gross. Inward: **gross → tare** (Phase A plant rule). |
| 6 | Product & storage selection | **DONE (order differs)** | Selected at **gate** with gate pass, before weigh. |
| 7 | Loading / unloading (gross, net, density, litres) | **DONE** | Server-authoritative net + litres. |
| 8 | Documents after loading | **DONE** | Primary path. |
| 9 | Customer OTP (WhatsApp) | **MOCK DONE** | Mock WhatsApp + on-screen OTP. Meta live **NOT DONE**. |
| 10 | Exit gate pass + close | **DONE** | Exit photo + closure (docs/OTP/party rules). |

---

## B) Modules A–H (flowchart middle)

| Module | Status | Where in app |
|--------|--------|--------------|
| A Material Receiving (Inward) | **DONE** | Yard → Inward |
| B Material Loading (Outward) | **DONE** | Yard → Outward |
| C Job Work + production loss | **DONE** | Job Work & OTP page |
| D Storage management | **DONE** | Storage & Stock + Masters |
| E Equipment movement | **DONE** | Equipment page |
| F Canteen purchase & stock | **DONE** | Canteen page |
| G Reports & analytics | **DONE** | Reports (+ ops exports) |
| H Security & access control | **DONE** | Roles/permissions + nav hide |

---

## C) Plant PDF / statement blueprints

| Document | Status |
|----------|--------|
| Vehicle Goods Movement Gate Pass | **DONE** (branded PDF; Diguvamasampalli address + GSTIN `37AARFJ6100D1ZI`) |
| Weighment Slip + calibration block / QR intent | **DONE** (slip + active calibration master; QR link to cert is layout/service — refine hosting later) |
| Supply & Expense Accounting Statement | **DONE** (Commercial PDF; period inputs / settlement link) |
| Distillation Recovery / Supply & Delivery Statement | **DONE** (Commercial PDF + charts) |
| Costing Sheet | **DONE** (Commercial PDF) |
| Minutes of Meeting | **DONE** (Commercial PDF) |
| Advances / settlement / GST reconcile | **DONE** (Finance module) |

Commercial numbers are **entered or settlement-assisted**, not fully auto-built from every yard trip line (deeper auto-ledger = future).

---

## D) Implementation phases (codebase)

| Track | Status |
|-------|--------|
| Phases 1–11 (platform) | **DONE** (PWA+Capacitor stack; see IMPLEMENTATION_PLAN) |
| Plant gap A–F (yard fields → finance) | **DONE** |
| Go-live A–E verify scripts | **DONE** on this machine |
| Go-live F cutover (JWT, roles, password change) | **DONE** |
| Toast UX + Modules UI redesign | **DONE** |

---

## E) Explicitly NOT DONE / deferred (boss may finish)

1. **Meta WhatsApp Business** live templates/token (mock path accepted now).  
2. **TRUWEIGH** serial / weighbridge hardware API.  
3. **Dedicated hardware ANPR** camera (current: OCR/Groq assist).  
4. **Unified Yard type picker** for Job Work / Equipment / Canteen (pages exist separately).  
5. **Full auto Supply schedule** from every weighment into commercial PDF.  
6. **Exact plant GPS pin** (approx Chittoor set; Owner can edit in Settings).  
7. **Production hardening**: rotate seed passwords, `APP_ENV=production`, CORS lockdown, strong secrets for public deploy.  
8. Update/fix **older phase2/phase4 unit tests** that still expect early-docs / loose exit.

---

## F) What works well today (happy path)

1. Login as role → see only allowed modules.  
2. Outward/Inward yard flow with live evidence, weigh, density, docs, mock OTP, exit.  
3. Gate pass + weighment PDFs.  
4. Stock, job work, equipment, canteen, reports, commercial, finance.  
5. Offline queue / sync policy.  
6. Health shows mock WhatsApp OK + writable evidence.

---

## G) Seed company identity (PDFs)

- **JV INDUSTRIES**  
- S.No. 821/A, Diguvamasampalli (V), Tiruttani Road, Chittoor, Andhra Pradesh – 517 503  
- GSTIN: **37AARFJ6100D1ZI**  
- Tel: +91 94443 36500  

Party masters in DB use **demo** GSTINs for tests — replace with real customers/suppliers in Masters.

---

## H) Quick “is it broken?” checklist

| Check | Command / URL |
|-------|----------------|
| API up | http://127.0.0.1:8080/health |
| Login | owner / Owner@123 |
| Yard | Menu → Gate / Home → Vehicle entry |
| PDF | After a trip → gate pass / weighment download |
| OTP | Send OTP → use preview code on screen |
| Finance | Modules → Finance |

If MySQL is down, API returns database unavailable — start MySQL first (`docs/HANDOFF_WINDOWS_BOSS.md`).
