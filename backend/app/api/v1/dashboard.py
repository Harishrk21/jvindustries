from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permissions
from app.models.enums import TransactionStatus, TransactionType
from app.models.equipment import Equipment
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import DashboardSummary

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("dashboard.view")),
) -> DashboardSummary:
    def count_type(t: TransactionType) -> int:
        return (
            db.execute(select(func.count()).select_from(Transaction).where(Transaction.type == t.value)).scalar()
            or 0
        )

    def count_status(s: TransactionStatus) -> int:
        return (
            db.execute(
                select(func.count()).select_from(Transaction).where(Transaction.status == s.value)
            ).scalar()
            or 0
        )

    open_statuses = [
        TransactionStatus.ENTRY_STARTED.value,
        TransactionStatus.VEHICLE_VERIFIED.value,
        TransactionStatus.AWAITING_TARE.value,
        TransactionStatus.TARE_COMPLETED.value,
        TransactionStatus.LOADING.value,
        TransactionStatus.UNLOADING.value,
        TransactionStatus.GROSS_COMPLETED.value,
        TransactionStatus.DENSITY_PENDING.value,
        TransactionStatus.DOCUMENTS_PENDING.value,
        TransactionStatus.DOCUMENTS_VERIFIED.value,
        TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value,
        TransactionStatus.CUSTOMER_CONFIRMED.value,
        TransactionStatus.APPROVAL_PENDING.value,
        TransactionStatus.APPROVED.value,
        TransactionStatus.EXIT_PENDING.value,
    ]

    vehicles_in = (
        db.execute(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.status.in_(open_statuses))
        ).scalar()
        or 0
    )
    vehicles_out = (
        db.execute(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.status.in_([TransactionStatus.EXIT_COMPLETED.value, TransactionStatus.COMPLETED.value]))
        ).scalar()
        or 0
    )

    return DashboardSummary(
        vehicles_in=vehicles_in,
        vehicles_out=vehicles_out,
        material_received=count_type(TransactionType.MATERIAL_RECEIVING_INWARD),
        material_loaded=count_type(TransactionType.MATERIAL_LOADING_OUTWARD),
        pending_approvals=count_status(TransactionStatus.APPROVAL_PENDING),
        customer_otp_pending=count_status(TransactionStatus.CUSTOMER_CONFIRMATION_PENDING),
        exceptions=count_status(TransactionStatus.EXCEPTION),
        equipment_out=(
            db.execute(
                select(func.count())
                .select_from(Equipment)
                .where(Equipment.status == "OUT_FOR_REPAIR", Equipment.active.is_(True))
            ).scalar()
            or 0
        ),
        canteen_purchases=count_type(TransactionType.CANTEEN_PURCHASE),
    )
