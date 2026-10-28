"""Phase D — supervisor approvals + exceptions inbox."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission
from app.models.documents import DocumentVerification
from app.models.enums import TransactionStatus
from app.models.equipment import EquipmentDisposal
from app.models.jobwork import ProductionLoss
from app.models.stock import StockAdjustment
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import InboxItem, InboxResponse

router = APIRouter()


@router.get("/approvals", response_model=InboxResponse)
def list_approvals(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission("approval.act", "transaction.view", "transaction.search", "dashboard.view")
    ),
    limit: int = Query(50, ge=1, le=200),
) -> InboxResponse:
    items: list[InboxItem] = []

    mismatches = (
        db.execute(
            select(DocumentVerification)
            .where(
                DocumentVerification.match_status == "MISMATCH",
                DocumentVerification.approved.is_(False),
            )
            .order_by(DocumentVerification.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    for ver in mismatches:
        items.append(
            InboxItem(
                kind="DOCUMENT_MISMATCH",
                id=ver.id,
                transaction_pk=ver.transaction_pk,
                transaction_id=ver.transaction_id,
                title="Document vehicle mismatch",
                detail=ver.mismatch_reason
                or f"ANPR={ver.anpr_vehicle} invoice={ver.invoice_vehicle} eway={ver.eway_vehicle}",
                status="PENDING_APPROVAL",
                created_at=ver.created_at,
                action_hint="Approve from Documents or POST /documents/mismatch/approve",
            )
        )

    losses = (
        db.execute(
            select(ProductionLoss)
            .where(ProductionLoss.requires_approval.is_(True), ProductionLoss.approved.is_(False))
            .order_by(ProductionLoss.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    for loss in losses:
        items.append(
            InboxItem(
                kind="PRODUCTION_LOSS",
                id=loss.id,
                transaction_pk=loss.transaction_pk,
                transaction_id=loss.transaction_id,
                title="Production loss exceeds limit",
                detail=(
                    f"loss={loss.loss_percent}% limit={loss.loss_limit_percent}% "
                    f"excess={loss.excess_percent}%"
                ),
                status="PENDING_APPROVAL",
                created_at=loss.created_at,
                action_hint="Approve from Job Work",
            )
        )

    adjustments = (
        db.execute(
            select(StockAdjustment)
            .where(StockAdjustment.status == "PENDING")
            .order_by(StockAdjustment.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    for adj in adjustments:
        items.append(
            InboxItem(
                kind="STOCK_ADJUSTMENT",
                id=adj.id,
                transaction_pk=None,
                transaction_id=None,
                title="Stock adjustment pending",
                detail=f"{adj.reason} ({adj.requested_quantity} {adj.unit})",
                status=adj.status,
                created_at=adj.created_at,
                action_hint="Decide from Storage & Stock",
            )
        )

    disposals = (
        db.execute(
            select(EquipmentDisposal)
            .where(EquipmentDisposal.status == "PENDING")
            .order_by(EquipmentDisposal.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    for disp in disposals:
        items.append(
            InboxItem(
                kind="EQUIPMENT_DISPOSAL",
                id=disp.id,
                transaction_pk=disp.transaction_pk,
                transaction_id=disp.transaction_id,
                title="Equipment disposal pending",
                detail=disp.reason,
                status=disp.status,
                created_at=disp.created_at,
                action_hint="Decide from Equipment",
            )
        )

    pending_txns = (
        db.execute(
            select(Transaction)
            .where(Transaction.status == TransactionStatus.APPROVAL_PENDING.value)
            .order_by(Transaction.updated_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    seen_txn = {i.transaction_pk for i in items if i.transaction_pk}
    for txn in pending_txns:
        if txn.id in seen_txn:
            continue
        items.append(
            InboxItem(
                kind="TRANSACTION_APPROVAL",
                id=txn.id,
                transaction_pk=txn.id,
                transaction_id=txn.transaction_id,
                title=f"Transaction needs approval ({txn.type})",
                detail=txn.vehicle_number or txn.notes,
                status=txn.status,
                created_at=txn.updated_at or txn.created_at,
                action_hint="Review linked module (documents / loss / stock / equipment)",
            )
        )

    items.sort(key=lambda x: x.created_at.timestamp() if x.created_at else 0.0, reverse=True)
    return InboxResponse(items=items[:limit], total=len(items))


@router.get("/exceptions", response_model=InboxResponse)
def list_exceptions(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission("approval.act", "transaction.view", "transaction.search", "dashboard.view")
    ),
    limit: int = Query(50, ge=1, le=200),
) -> InboxResponse:
    rows = (
        db.execute(
            select(Transaction)
            .where(Transaction.status == TransactionStatus.EXCEPTION.value)
            .order_by(Transaction.updated_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    items = [
        InboxItem(
            kind="TRANSACTION_EXCEPTION",
            id=txn.id,
            transaction_pk=txn.id,
            transaction_id=txn.transaction_id,
            title=f"Exception — {txn.type}",
            detail=txn.notes or txn.vehicle_number,
            status=txn.status,
            created_at=txn.updated_at or txn.created_at,
            action_hint="Supervisor review required",
        )
        for txn in rows
    ]
    return InboxResponse(items=items, total=len(items))
