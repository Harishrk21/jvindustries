"""Phase 6 — Job work batches + production loss (server-authoritative)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.enums import TransactionStatus, TransactionType
from app.models.jobwork import JobWorkBatch, ProductionLoss
from app.models.stock import Product
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.jobwork import JobWorkCreate, JobWorkOut, JobWorkQuantities, LossApproveRequest, ProductionLossOut
from app.services.audit_service import write_audit
from app.services.calculations import CalculationError, compute_production_loss, loss_requires_approval
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.notify_service import create_alert
from app.services.transaction_flow import transition
from app.services.transaction_id import next_transaction_id

router = APIRouter()


def _gps_ok(lat: float, lon: float, acc: float) -> None:
    result = GeofenceService().verify(GpsSample(lat, lon, acc))
    if not result.authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.message)


def _loss_out(row: ProductionLoss | None) -> ProductionLossOut | None:
    if row is None:
        return None
    return ProductionLossOut.model_validate(row)


def _batch_out(db: Session, batch: JobWorkBatch) -> JobWorkOut:
    loss = (
        db.execute(
            select(ProductionLoss)
            .where(ProductionLoss.batch_id == batch.id)
            .order_by(ProductionLoss.created_at.desc())
        )
        .scalars()
        .first()
    )
    return JobWorkOut(
        id=batch.id,
        transaction_id=batch.transaction_id,
        transaction_pk=batch.transaction_pk,
        batch_code=batch.batch_code,
        product_id=batch.product_id,
        customer_name=batch.customer_name,
        customer_mobile=batch.customer_mobile,
        qty_in=batch.qty_in,
        qty_out=batch.qty_out,
        unit=batch.unit,
        status=batch.status,
        loss=_loss_out(loss),
        created_at=batch.created_at,
    )


@router.post("/batches", response_model=JobWorkOut, status_code=status.HTTP_201_CREATED)
def create_batch(
    body: JobWorkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("jobwork.manage", "transaction.create")),
) -> JobWorkOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    if body.product_id and db.get(Product, body.product_id) is None:
        raise HTTPException(status_code=400, detail="Product not found.")

    if body.transaction_pk:
        txn = db.get(Transaction, body.transaction_pk)
        if txn is None:
            raise HTTPException(status_code=404, detail="Transaction not found.")
    else:
        code = next_transaction_id(db)
        txn = Transaction(
            transaction_id=code,
            type=TransactionType.JOB_WORK.value,
            status=TransactionStatus.DRAFT.value,
            created_by=user.id,
            device_id=body.device_id,
            product_id=body.product_id,
            geofence_ok=True,
            last_lat=body.gps.lat,
            last_lon=body.gps.lon,
            last_gps_accuracy_m=body.gps.accuracy_m,
        )
        db.add(txn)
        db.flush()
        transition(
            db,
            txn,
            to_status=TransactionStatus.ENTRY_STARTED.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason="Job work batch started",
            lat=body.gps.lat,
            lon=body.gps.lon,
            gps_accuracy_m=body.gps.accuracy_m,
        )

    batch = JobWorkBatch(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        product_id=body.product_id or txn.product_id,
        batch_code=body.batch_code.strip().upper(),
        customer_name=body.customer_name,
        customer_mobile=body.customer_mobile,
        unit=body.unit.upper(),
        notes=body.notes,
        status="OPEN",
        created_by=user.id,
    )
    db.add(batch)
    write_audit(
        db,
        action="JOBWORK_BATCH_CREATED",
        entity_type="job_work_batch",
        entity_id=batch.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=batch.batch_code,
    )
    db.commit()
    db.refresh(batch)
    return _batch_out(db, batch)


@router.get("/batches/{batch_id}", response_model=JobWorkOut)
def get_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("jobwork.manage", "transaction.view")),
) -> JobWorkOut:
    batch = db.get(JobWorkBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found.")
    return _batch_out(db, batch)


@router.post("/batches/quantities", response_model=JobWorkOut)
def set_quantities(
    body: JobWorkQuantities,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("jobwork.manage", "production.loss.capture")),
) -> JobWorkOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    batch = db.get(JobWorkBatch, body.batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found.")
    txn = db.get(Transaction, batch.transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    try:
        loss_qty, loss_percent = compute_production_loss(qty_in=body.qty_in, qty_out=body.qty_out)
    except CalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    product = db.get(Product, batch.product_id) if batch.product_id else None
    limit = float(product.loss_limit_percent) if product else 2.0
    needs = loss_requires_approval(loss_percent=loss_percent, loss_limit_percent=limit)
    excess = round(max(0.0, loss_percent - limit), 4)

    batch.qty_in = float(body.qty_in)
    batch.qty_out = float(body.qty_out)
    batch.status = "LOSS_PENDING" if needs else "CLOSED"

    loss = ProductionLoss(
        batch_id=batch.id,
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        product_id=batch.product_id,
        qty_in=float(body.qty_in),
        qty_out=float(body.qty_out),
        loss_qty=loss_qty,
        loss_percent=loss_percent,
        loss_limit_percent=limit,
        excess_percent=excess,
        requires_approval=needs,
        approved=not needs,
        created_by=user.id,
    )
    db.add(loss)

    if needs:
        create_alert(
            db,
            category="LOSS",
            severity="CRITICAL",
            title="Excess production loss",
            body=(
                f"Batch {batch.batch_code}: loss {loss_percent}% exceeds limit {limit}% "
                f"(excess {excess}%). Approval required."
            ),
            transaction_pk=txn.id,
            transaction_id=txn.transaction_id,
            entity_type="production_loss",
            entity_id=loss.id,
            created_by=user.id,
            send_whatsapp=True,
        )
        # Drive txn into approval if allowed
        try:
            if txn.status in {
                TransactionStatus.ENTRY_STARTED.value,
                TransactionStatus.DOCUMENTS_VERIFIED.value,
                TransactionStatus.CUSTOMER_CONFIRMED.value,
                TransactionStatus.APPROVED.value,
                TransactionStatus.DRAFT.value,
            }:
                # Move DRAFT/ENTRY toward APPROVAL_PENDING via allowed path when possible
                if txn.status == TransactionStatus.DRAFT.value:
                    transition(
                        db,
                        txn,
                        to_status=TransactionStatus.ENTRY_STARTED.value,
                        actor_user_id=user.id,
                        device_id=body.device_id,
                        reason="Job work quantities captured",
                        lat=body.gps.lat,
                        lon=body.gps.lon,
                        gps_accuracy_m=body.gps.accuracy_m,
                    )
                if txn.status == TransactionStatus.ENTRY_STARTED.value:
                    # Jump via EXCEPTION then APPROVAL is messy; set APPROVAL_PENDING if allowed from ENTRY? Not in machine.
                    # Use EXCEPTION then APPROVAL_PENDING
                    transition(
                        db,
                        txn,
                        to_status=TransactionStatus.EXCEPTION.value,
                        actor_user_id=user.id,
                        device_id=body.device_id,
                        reason=f"Production loss {loss_percent}% exceeds limit {limit}%",
                        lat=body.gps.lat,
                        lon=body.gps.lon,
                        gps_accuracy_m=body.gps.accuracy_m,
                    )
                if txn.status == TransactionStatus.EXCEPTION.value:
                    transition(
                        db,
                        txn,
                        to_status=TransactionStatus.APPROVAL_PENDING.value,
                        actor_user_id=user.id,
                        device_id=body.device_id,
                        reason=f"Excess production loss {excess}%",
                        lat=body.gps.lat,
                        lon=body.gps.lon,
                        gps_accuracy_m=body.gps.accuracy_m,
                    )
                elif txn.status in {
                    TransactionStatus.DOCUMENTS_VERIFIED.value,
                    TransactionStatus.CUSTOMER_CONFIRMED.value,
                    TransactionStatus.APPROVED.value,
                }:
                    transition(
                        db,
                        txn,
                        to_status=TransactionStatus.APPROVAL_PENDING.value,
                        actor_user_id=user.id,
                        device_id=body.device_id,
                        reason=f"Excess production loss {excess}%",
                        lat=body.gps.lat,
                        lon=body.gps.lon,
                        gps_accuracy_m=body.gps.accuracy_m,
                    )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        write_audit(
            db,
            action="PRODUCTION_LOSS_WITHIN_LIMIT",
            entity_type="production_loss",
            entity_id=loss.id,
            transaction_id=txn.transaction_id,
            actor_user_id=user.id,
            details=f"{loss_percent}% <= {limit}%",
        )

    write_audit(
        db,
        action="JOBWORK_QTY_SET",
        entity_type="job_work_batch",
        entity_id=batch.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"in={body.qty_in} out={body.qty_out} loss={loss_percent}% need_approval={needs}",
    )
    db.commit()
    db.refresh(batch)
    return _batch_out(db, batch)


@router.post("/loss/approve", response_model=JobWorkOut)
def approve_loss(
    body: LossApproveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("production.loss.approve", "approval.act")),
) -> JobWorkOut:
    loss = db.get(ProductionLoss, body.loss_id)
    if loss is None:
        raise HTTPException(status_code=404, detail="Loss record not found.")
    if not loss.requires_approval:
        raise HTTPException(status_code=400, detail="This loss does not require approval.")
    if loss.approved:
        raise HTTPException(status_code=400, detail="Already approved.")

    batch = db.get(JobWorkBatch, loss.batch_id)
    txn = db.get(Transaction, loss.transaction_pk)
    if batch is None or txn is None:
        raise HTTPException(status_code=404, detail="Batch/transaction missing.")

    loss.approved = True
    loss.approved_by = user.id
    loss.approval_note = body.approval_note
    batch.status = "CLOSED"

    if txn.status == TransactionStatus.APPROVAL_PENDING.value:
        transition(
            db,
            txn,
            to_status=TransactionStatus.APPROVED.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason=f"Production loss approved: {body.approval_note}",
            lat=body.gps.lat if body.gps else None,
            lon=body.gps.lon if body.gps else None,
            gps_accuracy_m=body.gps.accuracy_m if body.gps else None,
        )

    write_audit(
        db,
        action="PRODUCTION_LOSS_APPROVED",
        entity_type="production_loss",
        entity_id=loss.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=body.approval_note,
    )
    db.commit()
    db.refresh(batch)
    return _batch_out(db, batch)
