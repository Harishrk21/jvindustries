# JV-OMS Database ERD (PostgreSQL)

## Core identity

```
users ──┬── role_permissions ◄── roles
        │         ▲
        │         └── permissions
        ├── devices
        └── audit_logs (append-only)
```

## Transaction spine (ONE Transaction ID)

```
transactions (unique transaction_id e.g. JV-2026-001258)
  ├── transaction_events          # state machine history
  ├── photos / documents
  ├── invoices / eway_bills
  ├── weighments / density_readings
  ├── gate_passes
  ├── stock_movements
  ├── customer_otp / whatsapp_messages
  ├── approvals / exceptions
  └── equipment_* / canteen_* (when type matches)
```

**Rule:** Never create business evidence without a foreign key to `transactions.id` (or nullable only while DRAFT with client_transaction_id pending sync).

## Entity groups

### Masters
- `customers`, `suppliers`, `products`, `vehicles`, `drivers`, `transporters`
- `storage_locations`, `tanks`, `barrels`, `ibcs`
- `equipment`, `canteen_items`

### Auth & access
- `users`, `roles`, `permissions`, `role_permissions`, `devices`

### Operations
- `transactions`, `transaction_events`
- `gate_passes`
- `invoices`, `eway_bills`, `documents`, `photos`
- `weighments`, `density_readings`
- `stock_movements`, `stock_adjustments`
- `job_work_batches`, `production_batches`, `production_losses`
- `equipment_movements`, `equipment_repairs`, `equipment_disposals`
- `canteen_purchases`, `canteen_stock`
- `customer_otp`, `whatsapp_messages`
- `approvals`, `exceptions`, `notifications`, `report_exports`
- `audit_logs`

## Key fields (selected)

### transactions
| Column | Notes |
|--------|-------|
| id | UUID PK |
| transaction_id | Unique business ID `JV-YYYY-NNNNNN` |
| client_transaction_id | Offline idempotency |
| type | Enum transaction types |
| status | State machine status |
| vehicle_id, driver_id, customer_id, supplier_id | Optional FKs by type |
| created_by, device_id | Traceability |
| geofence_ok | Last critical-op check |
| sync_status | For client mirror awareness |
| created_at, updated_at | |

### photos
| Column | Notes |
|--------|-------|
| capture_source | `LIVE_CAMERA` \| `OWNER_GALLERY_UPLOAD` |
| latitude, longitude, gps_accuracy | |
| content_hash | Integrity |
| storage_path | Original never overwritten |

### weighments
| Column | Notes |
|--------|-------|
| kind | TARE \| GROSS |
| weight_kg | Confirmed value |
| net_kg | Server-computed on pair |
| photo_id | Evidence |

### density_readings
| Column | Notes |
|--------|-------|
| density_kg_per_l, temperature_c | Confirmed |
| calculated_litres | Server: net_kg / density |
| confidence | From AI |

## Relationships (textual ERD)

```
users (1) ──── (N) devices
users (1) ──── (N) transactions.created_by
roles (N) ──── (N) permissions via role_permissions

transactions (1) ──── (N) transaction_events
transactions (1) ──── (N) photos
transactions (1) ──── (0..1) invoices
transactions (1) ──── (0..1) eway_bills
transactions (1) ──── (N) weighments
transactions (1) ──── (0..1) density_readings
transactions (1) ──── (N) gate_passes
transactions (1) ──── (N) stock_movements
transactions (1) ──── (0..1) customer_otp
transactions (1) ──── (N) approvals
transactions (1) ──── (N) exceptions

products (1) ──── (N) tanks/barrels/ibcs (allowed product)
storage_* (1) ──── (N) stock_movements

job_work_batches (1) ──── (N) production_batches / production_losses
equipment (1) ──── (N) equipment_movements
```

## Indexes (minimum)

- `transactions(transaction_id)` UNIQUE
- `transactions(client_transaction_id)` UNIQUE WHERE NOT NULL
- `transactions(status)`, `transactions(type)`, `transactions(created_at)`
- `vehicles(vehicle_number)`
- `gate_passes(gate_pass_number)` UNIQUE
- `invoices(invoice_number)`
- `eway_bills(eway_bill_number)`
- `photos(transaction_id)`, `audit_logs(transaction_id)`, `audit_logs(created_at)`
- `stock_movements(product_id, created_at)`, `stock_movements(storage_*)`

## Integrity rules

- Foreign keys ON DELETE RESTRICT for operational history
- Soft-disable masters (`active` flag); do not hard-delete referenced rows
- `audit_logs` insert-only (no UPDATE/DELETE for app roles)
