# Phase A — Yard field dictionary (locked)

Source: JV flow chart + Weighment Slip + Gate Pass templates.  
Scope: capture + persist correct fields on the happy path (branded PDF polish = Phase D).

## Movement rules

| Type | Weigh order | Docs |
|------|-------------|------|
| **Inward** (`MATERIAL_RECEIVING_INWARD`) | **Gross (loaded) → unload → Tare (empty)** → density | Invoice + E-Way **after** density |
| **Outward** (`MATERIAL_LOADING_OUTWARD`) | **Tare (empty) → load → Gross** → density | Invoice + E-Way **after** density; OTP before complete |

## Step checklist

1. Location (GPS)
2. Type (Inward / Outward)
3. Lorry photo + ANPR → vehicle number
4. Driver & vehicle details
5. Gate pass + product/tank + route + security
6. Weighment (order by type above)
7. Density → litres
8. Invoice + E-Way
9. Weighment slip PDF
10. Exit photo + ANPR match
11. Party + OTP (outward) → Complete
12. Deliverables (gate PDF / slip)

## Fields by step

### Driver
| Field | Required | Stored on |
|-------|----------|-----------|
| Vehicle type (Truck / Tanker / Trailer) | Yes | `transactions.vehicle_type` |
| Driver name | Yes | `transactions` + `drivers` |
| Driver mobile | Yes | `transactions` + `drivers` |
| Licence | No | `drivers.license_no` |
| Transporter / company | No | `transactions.transporter_name` |
| Customer WhatsApp | No* | `transactions.customer_whatsapp` |

\*Required before outward OTP / complete.

### Gate pass
| Field | Required | Stored on |
|-------|----------|-----------|
| Purpose (Inward / Outward) | Auto | `gate_passes.purpose`, `transactions.purpose` |
| Product / material | Yes | assign storage + `gate_passes.material_description` |
| Storage / tank | Yes | `transactions.storage_unit_id` |
| From / origin | No | txn + gate pass |
| To / destination | No | txn + gate pass |
| Invoice / challan no. | No | `gate_passes.invoice_challan_no` |
| Remarks | No | txn + gate pass |
| Vehicle checked | Yes (checkbox) | `gate_passes.vehicle_checked` |
| Goods verified | Yes (checkbox) | `gate_passes.goods_verified` |
| Documents verified | Checkbox | `gate_passes.documents_verified` |

### Weighment
| Field | Required | Notes |
|-------|----------|-------|
| Gross kg + live photo | Yes | Server locks; no overwrite without approval |
| Tare kg + live photo | Yes | |
| Net kg | Calculated | `gross − tare` |
| Density kg/L + temp | Yes (prod) | Litres = net / density |

### Documents
| Field | Required |
|-------|----------|
| Invoice no., date, vehicle, GSTIN, parties | Confirm after OCR |
| E-Way no., vehicle | Confirm; mismatch → approval |

### Close
| Field | Required |
|-------|----------|
| Customer (outward) / Supplier (inward) | Yes |
| OTP verify | Outward yes |

## Guardrails (Phase A)
- Gallery upload: **owner / `photo.gallery` only**
- Skip weigh / density: **Vite DEV only**
- Gallery / skip must not ship as operator defaults in production builds
