# Phase E — Commercial statements

## UI
**More → Commercial**

| Tab | Endpoint | Output |
|-----|----------|--------|
| Supply & Expense | `POST /api/v1/commercial/supply-expense.pdf` | Stock schedule, material recon, deductions, GST, advances, payable |
| Distillation | `POST /api/v1/commercial/distillation.pdf` | Material balance + cut pie/bar charts + cost |
| Costing | `POST /api/v1/commercial/costing.pdf` | Purchase / opex / profitability options |
| Minutes | `POST /api/v1/commercial/minutes.pdf` | MoM participants, discussion, actions |

## Notes
- Numbers are entered (or seeded defaults) for the period; customer master fills name/address when `customer_id` set.
- Full ledger auto-link from every yard trip can deepen later; Phase E locks the **statement layouts** and formulas.
