# JV-OMS Transaction State Machine

## Principle

Do **not** use a boolean `completed`.  
All allowed actions are gated by **status** + **transaction type** + **role**.

## States

| State | Meaning |
|-------|---------|
| DRAFT | Local/server draft before formal entry |
| ENTRY_STARTED | Vehicle entry begun |
| VEHICLE_VERIFIED | ANPR/manual vehicle confirmed |
| AWAITING_TARE | Ready for tare |
| TARE_COMPLETED | Tare locked |
| LOADING | Outward loading in progress |
| UNLOADING | Inward unloading in progress |
| GROSS_COMPLETED | Gross locked; net computable |
| DENSITY_PENDING | Density required but not confirmed |
| DOCUMENTS_PENDING | Invoice/EWB still required (esp. outward) |
| DOCUMENTS_VERIFIED | Docs OCR-confirmed + vehicle match or exception |
| CUSTOMER_CONFIRMATION_PENDING | OTP sent |
| CUSTOMER_CONFIRMED | OTP accepted |
| APPROVAL_PENDING | Supervisor/owner decision needed |
| APPROVED | Approvals satisfied |
| EXIT_PENDING | Ready for exit capture |
| EXIT_COMPLETED | Exit photo/ANPR done |
| COMPLETED | Closure checklist passed |
| EXCEPTION | Held in exception workflow |
| REJECTED | Explicit reject |
| CANCELLED | Cancelled with reason + audit |

## Transaction types

- MATERIAL_RECEIVING_INWARD
- MATERIAL_LOADING_OUTWARD
- JOB_WORK
- EQUIPMENT_REPAIR_OUT
- EQUIPMENT_REPAIR_RETURN
- EQUIPMENT_TRANSFER
- EQUIPMENT_DISPOSAL
- CANTEEN_PURCHASE
- OTHER_MOVEMENT

## Material receiving (inward) — happy path

Loaded truck arrives → **gross first**, unload, then **empty tare**.

```
DRAFT → ENTRY_STARTED → VEHICLE_VERIFIED
  → AWAITING_TARE
  → UNLOADING          # after loaded GROSS (gross_kg set; net not yet)
  → TARE_COMPLETED → GROSS_COMPLETED → DENSITY_PENDING
  → DOCUMENTS_PENDING → DOCUMENTS_VERIFIED
  → EXIT_PENDING → EXIT_COMPLETED → COMPLETED
```

UI captures invoice/E-Way **after density**; **closure** still requires docs verified.

## Material loading (outward) — empty lorry rule

```
DRAFT → ENTRY_STARTED → VEHICLE_VERIFIED
  → AWAITING_TARE → TARE_COMPLETED → LOADING → GROSS_COMPLETED
  → DENSITY_PENDING? → …
  → DOCUMENTS_PENDING   # invoice/EWB NOT required at empty entry
  → DOCUMENTS_VERIFIED
  → CUSTOMER_CONFIRMATION_PENDING → CUSTOMER_CONFIRMED
  → APPROVAL_PENDING? → APPROVED
  → EXIT_PENDING → EXIT_COMPLETED → COMPLETED
```

**Hard rule:** No `COMPLETED` / final outward closure while `DOCUMENTS_PENDING` unless Owner-authorized exception recorded.

## Guards (examples)

| From | To | Requires |
|------|-----|----------|
| * | critical ops | GPS inside geofence + accuracy threshold |
| any | GROSS_COMPLETED | tare exists; gross ≥ tare; live photo |
| GROSS_COMPLETED | COMPLETED | net server-ok; docs/OTP/approvals per type |
| DOCUMENTS_PENDING | DOCUMENTS_VERIFIED | invoice+EWB confirmed OR owner exception |
| mismatch detected | APPROVAL_PENDING / EXCEPTION | supervisor/owner |
| excess loss | APPROVAL_PENDING | loss approval |
| * | CANCELLED | reason + privileged role |

## Terminal states

`COMPLETED`, `REJECTED`, `CANCELLED` — further mutations only via controlled correction events (new audit rows; never silent overwrite).

## Event log

Every transition writes `transaction_events`:

- from_status, to_status
- actor_user_id, device_id
- reason (if override)
- gps snapshot
- timestamp

## Final closure checklist (material loading)

Before `COMPLETED`:

- [ ] GPS verified
- [ ] Vehicle verified
- [ ] Driver recorded
- [ ] Tare completed
- [ ] Product selected
- [ ] Storage selected
- [ ] Loading completed
- [ ] Gross completed
- [ ] Net calculated (server)
- [ ] Density if applicable
- [ ] Invoice + E-Way Bill (or Owner exception)
- [ ] OCR confirmed
- [ ] Vehicle documents match (or approved mismatch)
- [ ] Customer OTP if required
- [ ] Gate pass generated
- [ ] Exit photo + exit ANPR
- [ ] Stock updated
- [ ] PDF generated
- [ ] Audit complete
