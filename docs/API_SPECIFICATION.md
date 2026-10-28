# JV-OMS API Specification (v1)

Base path: `/api/v1`  
Auth: `Authorization: Bearer <JWT>` unless noted  
Errors: structured `{ "code", "message", "details?" }` — never raw stack traces to clients  
Pagination: `page`, `page_size` + `total`  
Filtering: query params per resource

## Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | User ID + password/PIN → JWT + user/roles |
| POST | `/auth/logout` | Invalidate session/refresh if used |
| POST | `/auth/refresh` | Refresh token (Phase 1 policy) |
| GET | `/auth/me` | Current user profile + permissions |

## Users / devices / masters (Phase 1+)

| Method | Path | Notes |
|--------|------|-------|
| CRUD | `/users` | Owner admin |
| POST | `/devices/register` | Bind device after login |
| GET/PATCH | `/devices/me` | Current device |
| CRUD | `/customers`, `/suppliers`, `/products` | Masters |
| CRUD | `/vehicles`, `/drivers`, `/transporters` | Masters |

## Transactions

| Method | Path | Description |
|--------|------|-------------|
| POST | `/transactions` | Create DRAFT / start; returns `transaction_id` |
| GET | `/transactions` | Search/filter |
| GET | `/transactions/{id}` | Full detail + timeline |
| GET | `/transactions/by-code/{transaction_id}` | Lookup by JV-… |
| POST | `/transactions/{id}/events` | Attempt state transition (validated) |
| GET | `/transactions/{id}/timeline` | Ordered events |

### Create body (sketch)

```json
{
  "client_transaction_id": "uuid",
  "type": "MATERIAL_LOADING_OUTWARD",
  "device_id": "uuid",
  "gps": { "lat": 0, "lon": 0, "accuracy_m": 5, "timestamp": "ISO" }
}
```

Server generates `transaction_id` if not yet assigned at first persist.

## Domain modules (later phases)

| Prefix | Scope |
|--------|-------|
| `/gate-passes` | Generate/list/PDF |
| `/invoices`, `/eway-bills` | Upload + OCR confirm |
| `/weighments` | Tare/Gross; server net |
| `/density` | Confirm density/temp; server litres |
| `/storage`, `/stock` | Locations + movements |
| `/job-work`, `/production-loss` | Batches + approvals |
| `/equipment` | Repair/return/disposal |
| `/canteen` | Purchase + stock |
| `/otp`, `/whatsapp` | Customer confirm + delivery status |
| `/reports` | Generate/export |
| `/commercial` | Supply/distillation/costing/MoM PDFs |
| `/finance` | Advances, settlements, GST reconcile |
| `/approvals`, `/exceptions` | Supervisor/owner flows |
| `/audit` | Append-only query |
| `/config/geofence` | Owner-configurable |

## Photos / evidence

| Method | Path | Description |
|--------|------|-------------|
| POST | `/photos` | Multipart + metadata; hash verified |
| GET | `/photos/{id}` | Metadata |
| GET | `/photos/{id}/url` | Signed URL |

Required metadata: `transaction_id`, `file_type`, `capture_source`, `device_id`, GPS fields.

## Offline sync (Phase 11)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sync/policy` | Conflict / idempotency rules |
| POST | `/sync/push` | Push offline drafts (`client_transaction_id` required) |

Outcomes per draft: `CREATED` \| `IDEMPOTENT` \| `CONFLICT` \| `ERROR`.  
Server never overwrites transactions past DRAFT/ENTRY_STARTED.

## Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/summary` | Counts: vehicles in/out, pending OTP, exceptions, etc. |

## Calculations (server authoritative)

On commit of weighments/density/loss/stock:

- `net_kg = gross_kg - tare_kg` (reject if gross < tare)
- `calculated_litres = net_kg / density` when density required
- Production loss % and excess vs product `loss_limit_percent`
- Stock balances from movements only

Clients may send proposed values; server recalculates and rejects mismatch outside tolerance (tolerance config).

## Authorization

Every route checks JWT → role → permission code.  
Missing permission → `403` with friendly message.

## Versioning

Breaking changes → `/api/v2`. Additive fields allowed in v1 with care.
