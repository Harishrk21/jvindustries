# Phase F — Finance close-loop

## UI
**More → Finance**

| Tab | Endpoints | Purpose |
|-----|-----------|---------|
| Advances | `POST/GET /api/v1/finance/advances`, `GET .../balance`, `GET .../balances` | Paid / received-back ledger |
| Settlements | `POST/GET /api/v1/finance/settlements`, `POST .../finalize`, `POST .../supply-expense.pdf` | Period snapshot + Supply PDF |
| GST reconcile | `POST /api/v1/finance/gst/reconcile` | Confirmed invoices vs party GSTIN |

## Formulas
- Net feedstock = feedstock − bleaching return
- Processing base = net feedstock × rate/kg
- GST = base × gst%
- Deductions = burner_kg × burner_rate + retail_kg × retail_rate
- Net processing = base + GST − deductions
- Payable = net processing + (advance paid − received back)

## Auto-fill
- Settlement drafts pull yard delivery kg/trips from transactions in the period.
- Supply & Expense commercial PDF fills advances from the ledger when both advance fields are 0 and `customer_id` is set.
- Commercial UI pre-fills advance fields from `GET /finance/advances/balance`.
