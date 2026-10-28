# Phase D — Branded yard PDFs

## Documents
| PDF | Endpoint | Matches template |
|-----|----------|------------------|
| **Weighment slip** | `GET /api/v1/pdfs/transaction/{pk}?variant=customer` · alias `/pdfs/weighment-slip/{pk}` | Header, vehicle/driver, party, weight table (kg+MT), density, calibration, signatures |
| **Gate pass** | `GET /api/v1/pdfs/gate-pass/{pk}` | Vehicle / goods / security sections, purpose checkboxes, signatures |
| Internal summary | `?variant=internal` | Compact ops copy (not customer) |

## Branding
JV INDUSTRIES · tagline · Chittoor address · GSTIN `37AARFJ6100D1ZI` · phone · email

## Data sources
- Weights + weigh timestamps from `weighments`
- Calibration from active `weighbridge_calibrations`
- Party from customer/supplier master
- Product from assigned `product_id`
- Gate pass fields from Phase A capture

## Smoke
Yard → finish weigh → **Download / Share slip** · Done → **Share gate pass**
