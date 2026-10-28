"""Phase F — advances ledger, settlements, GST reconcile."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission
from app.models.finance import AdvanceEntry, GstReconcileItem, Settlement
from app.models.parties import Customer
from app.models.user import User
from app.schemas.commercial import SupplyExpenseRequest
from app.schemas.finance import (
    AdvanceBalanceOut,
    AdvanceCreate,
    AdvanceOut,
    GstReconcileOut,
    GstReconcileRow,
    SettlementCreate,
    SettlementOut,
)
from app.services.audit_service import write_audit
from app.services.commercial_pdf import build_supply_expense_pdf
from app.services.finance_service import (
    advance_totals,
    create_settlement,
    reconcile_gst,
)

router = APIRouter()


def _pdf(content: bytes, file_name: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.post("/advances", response_model=AdvanceOut)
def post_advance(
    body: AdvanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> AdvanceEntry:
    cust = db.get(Customer, body.customer_id)
    if cust is None:
        raise HTTPException(status_code=404, detail="Customer not found.")
    row = AdvanceEntry(
        customer_id=body.customer_id,
        entry_date=body.entry_date,
        direction=body.direction,
        amount=body.amount,
        reference=body.reference,
        notes=body.notes,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        action="FINANCE_ADVANCE_CREATE",
        entity_type="advance_entry",
        entity_id=row.id,
        actor_user_id=user.id,
        details=f"{body.direction} {body.amount}",
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/advances", response_model=list[AdvanceOut])
def list_advances(
    customer_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> list[AdvanceEntry]:
    _ = user
    q = select(AdvanceEntry)
    if customer_id:
        q = q.where(AdvanceEntry.customer_id == customer_id)
    q = q.order_by(AdvanceEntry.entry_date.desc(), AdvanceEntry.created_at.desc()).limit(limit)
    return list(db.execute(q).scalars().all())


@router.get("/advances/balance", response_model=AdvanceBalanceOut)
def advance_balance(
    customer_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> AdvanceBalanceOut:
    _ = user
    cust = db.get(Customer, customer_id)
    if cust is None:
        raise HTTPException(status_code=404, detail="Customer not found.")
    paid, back, bal = advance_totals(db, customer_id)
    return AdvanceBalanceOut(
        customer_id=cust.id,
        customer_code=cust.code,
        customer_name=cust.name,
        paid_total=paid,
        received_back_total=back,
        balance=bal,
    )


@router.get("/advances/balances", response_model=list[AdvanceBalanceOut])
def advance_balances(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> list[AdvanceBalanceOut]:
    _ = user
    customers = list(db.execute(select(Customer).where(Customer.active.is_(True)).order_by(Customer.code)).scalars().all())
    out: list[AdvanceBalanceOut] = []
    for c in customers:
        paid, back, bal = advance_totals(db, c.id)
        if paid == 0 and back == 0:
            continue
        out.append(
            AdvanceBalanceOut(
                customer_id=c.id,
                customer_code=c.code,
                customer_name=c.name,
                paid_total=paid,
                received_back_total=back,
                balance=bal,
            )
        )
    return out


@router.post("/settlements", response_model=SettlementOut)
def post_settlement(
    body: SettlementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> Settlement:
    if body.period_to < body.period_from:
        raise HTTPException(status_code=400, detail="period_to must be on/after period_from.")
    try:
        row = create_settlement(db, body, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    write_audit(
        db,
        action="FINANCE_SETTLEMENT_CREATE",
        entity_type="settlement",
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.report_no,
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/settlements", response_model=list[SettlementOut])
def list_settlements(
    customer_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> list[Settlement]:
    _ = user
    q = select(Settlement)
    if customer_id:
        q = q.where(Settlement.customer_id == customer_id)
    q = q.order_by(Settlement.created_at.desc()).limit(limit)
    return list(db.execute(q).scalars().all())


@router.get("/settlements/{settlement_id}", response_model=SettlementOut)
def get_settlement(
    settlement_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> Settlement:
    _ = user
    row = db.get(Settlement, settlement_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Settlement not found.")
    return row


@router.post("/settlements/{settlement_id}/finalize", response_model=SettlementOut)
def finalize_settlement(
    settlement_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "owner.full")),
) -> Settlement:
    row = db.get(Settlement, settlement_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Settlement not found.")
    if row.finalized:
        raise HTTPException(status_code=400, detail="Already finalized.")
    row.finalized = True
    row.status = "FINALIZED"
    write_audit(
        db,
        action="FINANCE_SETTLEMENT_FINALIZE",
        entity_type="settlement",
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.report_no,
    )
    db.commit()
    db.refresh(row)
    return row


@router.post("/settlements/{settlement_id}/supply-expense.pdf")
def settlement_supply_pdf(
    settlement_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> Response:
    row = db.get(Settlement, settlement_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Settlement not found.")
    cust = db.get(Customer, row.customer_id)
    body = SupplyExpenseRequest(
        customer_id=row.customer_id,
        customer_name=cust.name if cust else "Customer",
        customer_address=cust.address if cust else None,
        report_no=row.report_no,
        period_from=row.period_from.isoformat(),
        period_to=row.period_to.isoformat(),
        feedstock_kg=row.feedstock_kg,
        feedstock_consignments=row.feedstock_consignments,
        delivery_kg=row.delivery_kg,
        delivery_trips=row.delivery_trips,
        bleaching_return_kg=row.bleaching_return_kg,
        burner_fuel_kg=row.burner_fuel_kg,
        burner_rate=row.burner_rate,
        retail_kg=row.retail_kg,
        retail_rate=row.retail_rate,
        processing_rate_per_kg=row.processing_rate_per_kg,
        gst_percent=row.gst_percent,
        advance_paid=row.advance_paid,
        advance_received_back=row.advance_received_back,
    )
    pdf = build_supply_expense_pdf(body)
    write_audit(
        db,
        action="FINANCE_SETTLEMENT_PDF",
        entity_type="settlement",
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.report_no,
    )
    db.commit()
    return _pdf(pdf, f"supply-expense-{row.report_no}.pdf")


@router.post("/gst/reconcile", response_model=GstReconcileOut)
def gst_reconcile(
    period_from: date = Query(...),
    period_to: date = Query(...),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> GstReconcileOut:
    if period_to < period_from:
        raise HTTPException(status_code=400, detail="period_to must be on/after period_from.")
    run_id, rows = reconcile_gst(db, period_from=period_from, period_to=period_to)
    if persist:
        for r in rows:
            db.add(
                GstReconcileItem(
                    run_id=run_id,
                    invoice_id=r["invoice_id"],
                    transaction_id=r["transaction_id"],
                    invoice_number=r["invoice_number"],
                    invoice_gstin=r["invoice_gstin"],
                    party_gstin=r["party_gstin"],
                    invoice_total=r["invoice_total"],
                    match_status=r["match_status"],
                    detail=r["detail"],
                )
            )
    matched = sum(1 for r in rows if r["match_status"] == "MATCH")
    mismatches = len(rows) - matched
    write_audit(
        db,
        action="FINANCE_GST_RECONCILE",
        entity_type="gst_reconcile",
        entity_id=run_id,
        actor_user_id=user.id,
        details=f"{period_from}..{period_to} total={len(rows)} mismatch={mismatches}",
    )
    db.commit()
    return GstReconcileOut(
        run_id=run_id,
        period_from=period_from.isoformat(),
        period_to=period_to.isoformat(),
        total=len(rows),
        matched=matched,
        mismatches=mismatches,
        rows=[GstReconcileRow(**r) for r in rows],
    )
