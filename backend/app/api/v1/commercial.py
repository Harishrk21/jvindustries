"""Phase E — commercial PDF statements."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission
from app.models.parties import Customer
from app.models.user import User
from app.schemas.commercial import (
    CostingRequest,
    DistillationRequest,
    MomRequest,
    SupplyExpenseRequest,
)
from app.services.audit_service import write_audit
from app.services.commercial_pdf import (
    build_costing_pdf,
    build_distillation_pdf,
    build_mom_pdf,
    build_supply_expense_pdf,
)
from app.services.finance_service import advance_totals

router = APIRouter()


def _pdf(content: bytes, file_name: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.post("/supply-expense.pdf")
def supply_expense_pdf(
    body: SupplyExpenseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> Response:
    if body.customer_id:
        cust = db.get(Customer, body.customer_id)
        if cust:
            if not body.customer_address or body.customer_name == "Customer":
                body.customer_name = cust.name
                body.customer_address = body.customer_address or cust.address
            if body.advance_paid == 0 and body.advance_received_back == 0:
                paid, back, _ = advance_totals(db, body.customer_id)
                body.advance_paid = paid
                body.advance_received_back = back
    pdf = build_supply_expense_pdf(body)
    write_audit(
        db,
        action="COMMERCIAL_SUPPLY_EXPENSE_PDF",
        entity_type="commercial",
        entity_id=body.report_no,
        actor_user_id=user.id,
        details=body.customer_name,
    )
    db.commit()
    return _pdf(pdf, f"supply-expense-{body.report_no}.pdf")


@router.post("/distillation.pdf")
def distillation_pdf(
    body: DistillationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> Response:
    pdf = build_distillation_pdf(body)
    write_audit(
        db,
        action="COMMERCIAL_DISTILLATION_PDF",
        entity_type="commercial",
        entity_id=body.report_no,
        actor_user_id=user.id,
        details=body.customer_name,
    )
    db.commit()
    return _pdf(pdf, f"distillation-{body.report_no}.pdf")


@router.post("/costing.pdf")
def costing_pdf(
    body: CostingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> Response:
    pdf = build_costing_pdf(body)
    write_audit(
        db,
        action="COMMERCIAL_COSTING_PDF",
        entity_type="commercial",
        entity_id="costing",
        actor_user_id=user.id,
        details=body.title,
    )
    db.commit()
    return _pdf(pdf, "costing-sheet.pdf")


@router.post("/minutes.pdf")
def minutes_pdf(
    body: MomRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "owner.full")),
) -> Response:
    pdf = build_mom_pdf(body)
    write_audit(
        db,
        action="COMMERCIAL_MOM_PDF",
        entity_type="commercial",
        entity_id=body.meeting_date,
        actor_user_id=user.id,
        details=body.objective,
    )
    db.commit()
    return _pdf(pdf, f"minutes-{body.meeting_date}.pdf")
