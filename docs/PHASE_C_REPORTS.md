# Phase C — Ops reports

## Tabs (Reports page)
| Tab | API | Content |
|-----|-----|---------|
| Operations | `/reports/summary` + `/export` | Existing daily/monthly/custom txn rollup |
| Month stock | `/reports/ops/stock` | Opening / received / loaded / closing (+ L cols) |
| Tank-wise | `/reports/ops/tank` | Live balances by tank × product |
| Customer | `/reports/ops/customer` | Trips, net kg, litres by customer |
| Job-work | `/reports/ops/jobwork` | Batch in/out, loss %, approval flag |
| Audit | `/reports/ops/audit` | Append-only action log (period) |

## Export
`GET /api/v1/reports/ops/{kind}/export?format=pdf|xlsx|csv&period=…`

## Smoke
1. More → Reports → each tab loads without error  
2. Month stock shows seeded T-03 opening line  
3. Export Excel on tank-wise downloads  
