"""Phase 8 — Equipment master, repair out/return, transfer, disposal + approvals."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.enums import TransactionStatus, TransactionType
from app.models.equipment import Equipment, EquipmentDisposal, EquipmentMovement, EquipmentRepair
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.equipment import (
    DisposalDecideRequest,
    DisposalOut,
    DisposalRequest,
    EquipmentActionOut,
    EquipmentCreate,
    EquipmentOut,
    MovementOut,
    RepairOut,
    RepairOutRequest,
    RepairReturnRequest,
    TransferRequest,
)
from app.services.audit_service import write_audit
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.notify_service import create_alert
from app.services.transaction_flow import transition
from app.services.transaction_id import next_transaction_id

router = APIRouter()


def _gps_ok(lat: float, lon: float, acc: float) -> None:
    result = GeofenceService().verify(GpsSample(lat, lon, acc))
    if not result.authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.message)


def _start_txn(
    db: Session,
    *,
    user: User,
    txn_type: str,
    gps,
    device_id: str | None,
    reason: str,
) -> Transaction:
    txn = Transaction(
        transaction_id=next_transaction_id(db),
        type=txn_type,
        status=TransactionStatus.DRAFT.value,
        created_by=user.id,
        device_id=device_id,
        geofence_ok=True,
        last_lat=gps.lat,
        last_lon=gps.lon,
        last_gps_accuracy_m=gps.accuracy_m,
        notes=reason,
    )
    db.add(txn)
    db.flush()
    transition(
        db,
        txn,
        to_status=TransactionStatus.ENTRY_STARTED.value,
        actor_user_id=user.id,
        device_id=device_id,
        reason=reason,
        lat=gps.lat,
        lon=gps.lon,
        gps_accuracy_m=gps.accuracy_m,
    )
    return txn


def _move(
    db: Session,
    *,
    equipment: Equipment,
    txn: Transaction,
    movement_type: str,
    to_status: str,
    user: User,
    vendor_name: str | None = None,
    destination: str | None = None,
    reason: str | None = None,
) -> EquipmentMovement:
    from_status = equipment.status
    equipment.status = to_status
    row = EquipmentMovement(
        equipment_id=equipment.id,
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        movement_type=movement_type,
        from_status=from_status,
        to_status=to_status,
        vendor_name=vendor_name,
        destination=destination,
        reason=reason,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    return row


def _action_out(
    *,
    equipment: Equipment,
    txn: Transaction,
    movement: EquipmentMovement | None = None,
    repair: EquipmentRepair | None = None,
    disposal: EquipmentDisposal | None = None,
) -> EquipmentActionOut:
    return EquipmentActionOut(
        equipment=EquipmentOut.model_validate(equipment),
        transaction_id=txn.transaction_id,
        transaction_pk=txn.id,
        transaction_status=txn.status,
        movement=MovementOut.model_validate(movement) if movement else None,
        repair=RepairOut.model_validate(repair) if repair else None,
        disposal=DisposalOut.model_validate(disposal) if disposal else None,
    )


@router.get("", response_model=list[EquipmentOut])
def list_equipment(
    status_filter: str | None = Query(None, alias="status"),
    active_only: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("equipment.repair", "equipment.return", "transaction.view")),
) -> list[Equipment]:
    q = select(Equipment).order_by(Equipment.code)
    if active_only:
        q = q.where(Equipment.active.is_(True))
    if status_filter:
        q = q.where(Equipment.status == status_filter.upper())
    return list(db.execute(q).scalars().all())


@router.post("", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
def create_equipment(
    body: EquipmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> Equipment:
    code = body.code.strip().upper()
    if db.execute(select(Equipment).where(Equipment.code == code)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Equipment code {code} already exists.")
    row = Equipment(
        code=code,
        name=body.name.strip(),
        category=body.category.upper(),
        location_label=body.location_label,
        status="IN_YARD",
        active=body.active,
    )
    db.add(row)
    write_audit(
        db,
        action="EQUIPMENT_CREATED",
        entity_type="equipment",
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.code,
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/movements", response_model=list[MovementOut])
def list_movements(
    equipment_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("equipment.repair", "transaction.view")),
) -> list[EquipmentMovement]:
    q = select(EquipmentMovement).order_by(EquipmentMovement.created_at.desc()).limit(limit)
    if equipment_id:
        q = q.where(EquipmentMovement.equipment_id == equipment_id)
    return list(db.execute(q).scalars().all())


@router.get("/out-count")
def out_count(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("dashboard.view", "equipment.repair")),
) -> dict:
    n = (
        db.execute(
            select(func.count())
            .select_from(Equipment)
            .where(Equipment.status == "OUT_FOR_REPAIR", Equipment.active.is_(True))
        ).scalar()
        or 0
    )
    return {"equipment_out": n}


@router.post("/repair-out", response_model=EquipmentActionOut)
def repair_out(
    body: RepairOutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("equipment.repair", "transaction.create")),
) -> EquipmentActionOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    eq = db.get(Equipment, body.equipment_id)
    if eq is None or not eq.active:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    if eq.status != "IN_YARD":
        raise HTTPException(status_code=400, detail=f"Equipment must be IN_YARD (now {eq.status}).")

    txn = _start_txn(
        db,
        user=user,
        txn_type=TransactionType.EQUIPMENT_REPAIR_OUT.value,
        gps=body.gps,
        device_id=body.device_id,
        reason=f"Repair out {eq.code}",
    )
    move = _move(
        db,
        equipment=eq,
        txn=txn,
        movement_type="REPAIR_OUT",
        to_status="OUT_FOR_REPAIR",
        user=user,
        vendor_name=body.vendor_name,
        reason=body.reason,
    )
    repair = EquipmentRepair(
        equipment_id=eq.id,
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        vendor_name=body.vendor_name.strip(),
        reason=body.reason,
        expected_return_date=body.expected_return_date,
        status="OPEN",
        created_by=user.id,
    )
    db.add(repair)
    create_alert(
        db,
        category="SYSTEM",
        severity="WARN",
        title="Equipment out for repair",
        body=f"{eq.code} → {body.vendor_name}: {body.reason}",
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        entity_type="equipment",
        entity_id=eq.id,
        created_by=user.id,
        send_whatsapp=True,
    )
    write_audit(
        db,
        action="EQUIPMENT_REPAIR_OUT",
        entity_type="equipment",
        entity_id=eq.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=body.vendor_name,
    )
    # Move txn toward exit-ready for gate
    transition(
        db,
        txn,
        to_status=TransactionStatus.EXIT_PENDING.value,
        actor_user_id=user.id,
        device_id=body.device_id,
        reason="Equipment repair out recorded",
        lat=body.gps.lat,
        lon=body.gps.lon,
        gps_accuracy_m=body.gps.accuracy_m,
    )
    db.commit()
    db.refresh(eq)
    db.refresh(repair)
    db.refresh(move)
    db.refresh(txn)
    return _action_out(equipment=eq, txn=txn, movement=move, repair=repair)


@router.post("/repair-return", response_model=EquipmentActionOut)
def repair_return(
    body: RepairReturnRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("equipment.return", "equipment.repair")),
) -> EquipmentActionOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    eq = db.get(Equipment, body.equipment_id)
    if eq is None:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    if eq.status != "OUT_FOR_REPAIR":
        raise HTTPException(status_code=400, detail=f"Equipment is not OUT_FOR_REPAIR (now {eq.status}).")

    repair: EquipmentRepair | None = None
    if body.repair_id:
        repair = db.get(EquipmentRepair, body.repair_id)
    else:
        repair = (
            db.execute(
                select(EquipmentRepair)
                .where(EquipmentRepair.equipment_id == eq.id, EquipmentRepair.status == "OPEN")
                .order_by(EquipmentRepair.created_at.desc())
            )
            .scalars()
            .first()
        )
    if repair is None:
        raise HTTPException(status_code=400, detail="No open repair record for this equipment.")

    txn = _start_txn(
        db,
        user=user,
        txn_type=TransactionType.EQUIPMENT_REPAIR_RETURN.value,
        gps=body.gps,
        device_id=body.device_id,
        reason=f"Repair return {eq.code}",
    )
    move = _move(
        db,
        equipment=eq,
        txn=txn,
        movement_type="REPAIR_RETURN",
        to_status="IN_YARD",
        user=user,
        reason=body.note or "Returned from repair",
    )
    repair.status = "RETURNED"
    repair.return_transaction_pk = txn.id
    transition(
        db,
        txn,
        to_status=TransactionStatus.COMPLETED.value,
        actor_user_id=user.id,
        device_id=body.device_id,
        reason="Equipment returned to yard",
        lat=body.gps.lat,
        lon=body.gps.lon,
        gps_accuracy_m=body.gps.accuracy_m,
    )
    write_audit(
        db,
        action="EQUIPMENT_REPAIR_RETURN",
        entity_type="equipment",
        entity_id=eq.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=eq.code,
    )
    db.commit()
    db.refresh(eq)
    db.refresh(repair)
    db.refresh(move)
    db.refresh(txn)
    return _action_out(equipment=eq, txn=txn, movement=move, repair=repair)


@router.post("/transfer", response_model=EquipmentActionOut)
def transfer_equipment(
    body: TransferRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("equipment.repair", "transaction.create")),
) -> EquipmentActionOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    eq = db.get(Equipment, body.equipment_id)
    if eq is None or not eq.active:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    if eq.status != "IN_YARD":
        raise HTTPException(status_code=400, detail=f"Only IN_YARD equipment can transfer (now {eq.status}).")

    txn = _start_txn(
        db,
        user=user,
        txn_type=TransactionType.EQUIPMENT_TRANSFER.value,
        gps=body.gps,
        device_id=body.device_id,
        reason=f"Transfer {eq.code} → {body.destination}",
    )
    move = _move(
        db,
        equipment=eq,
        txn=txn,
        movement_type="TRANSFER",
        to_status="TRANSFERRED",
        user=user,
        destination=body.destination,
        reason=body.reason,
    )
    eq.location_label = body.destination
    transition(
        db,
        txn,
        to_status=TransactionStatus.EXIT_PENDING.value,
        actor_user_id=user.id,
        device_id=body.device_id,
        reason="Equipment transfer recorded",
        lat=body.gps.lat,
        lon=body.gps.lon,
        gps_accuracy_m=body.gps.accuracy_m,
    )
    write_audit(
        db,
        action="EQUIPMENT_TRANSFER",
        entity_type="equipment",
        entity_id=eq.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=body.destination,
    )
    db.commit()
    db.refresh(eq)
    db.refresh(move)
    db.refresh(txn)
    return _action_out(equipment=eq, txn=txn, movement=move)


@router.post("/disposal", response_model=EquipmentActionOut)
def request_disposal(
    body: DisposalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("equipment.disposal", "transaction.create")),
) -> EquipmentActionOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    eq = db.get(Equipment, body.equipment_id)
    if eq is None or not eq.active:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    if eq.status not in {"IN_YARD", "TRANSFERRED"}:
        raise HTTPException(status_code=400, detail=f"Cannot dispose from status {eq.status}.")

    txn = _start_txn(
        db,
        user=user,
        txn_type=TransactionType.EQUIPMENT_DISPOSAL.value,
        gps=body.gps,
        device_id=body.device_id,
        reason=f"Disposal request {eq.code}",
    )
    # Approval required — keep equipment status until approved; txn → APPROVAL_PENDING via EXCEPTION
    transition(
        db,
        txn,
        to_status=TransactionStatus.EXCEPTION.value,
        actor_user_id=user.id,
        device_id=body.device_id,
        reason="Disposal requires approval",
        lat=body.gps.lat,
        lon=body.gps.lon,
        gps_accuracy_m=body.gps.accuracy_m,
    )
    transition(
        db,
        txn,
        to_status=TransactionStatus.APPROVAL_PENDING.value,
        actor_user_id=user.id,
        device_id=body.device_id,
        reason=body.reason,
        lat=body.gps.lat,
        lon=body.gps.lon,
        gps_accuracy_m=body.gps.accuracy_m,
    )
    disposal = EquipmentDisposal(
        equipment_id=eq.id,
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        reason=body.reason,
        status="PENDING",
        created_by=user.id,
    )
    db.add(disposal)
    db.flush()
    create_alert(
        db,
        category="APPROVAL",
        severity="CRITICAL",
        title="Equipment disposal approval needed",
        body=f"{eq.code}: {body.reason}",
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        entity_type="equipment_disposal",
        entity_id=disposal.id,
        created_by=user.id,
        send_whatsapp=True,
    )
    write_audit(
        db,
        action="EQUIPMENT_DISPOSAL_REQUESTED",
        entity_type="equipment_disposal",
        entity_id=disposal.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=eq.code,
    )
    db.commit()
    db.refresh(eq)
    db.refresh(disposal)
    db.refresh(txn)
    return _action_out(equipment=eq, txn=txn, disposal=disposal)


@router.post("/disposal/decide", response_model=EquipmentActionOut)
def decide_disposal(
    body: DisposalDecideRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("equipment.approve", "approval.act")),
) -> EquipmentActionOut:
    disposal = db.get(EquipmentDisposal, body.disposal_id)
    if disposal is None:
        raise HTTPException(status_code=404, detail="Disposal not found.")
    if disposal.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Disposal already {disposal.status}.")
    eq = db.get(Equipment, disposal.equipment_id)
    txn = db.get(Transaction, disposal.transaction_pk)
    if eq is None or txn is None:
        raise HTTPException(status_code=404, detail="Equipment/transaction missing.")

    if not body.approve:
        disposal.status = "REJECTED"
        disposal.approved_by = user.id
        disposal.approval_note = body.approval_note
        if txn.status == TransactionStatus.APPROVAL_PENDING.value:
            transition(
                db,
                txn,
                to_status=TransactionStatus.REJECTED.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason=body.approval_note,
            )
        write_audit(
            db,
            action="EQUIPMENT_DISPOSAL_REJECTED",
            entity_type="equipment_disposal",
            entity_id=disposal.id,
            transaction_id=txn.transaction_id,
            actor_user_id=user.id,
            details=body.approval_note,
        )
        db.commit()
        db.refresh(eq)
        db.refresh(disposal)
        db.refresh(txn)
        return _action_out(equipment=eq, txn=txn, disposal=disposal)

    move = _move(
        db,
        equipment=eq,
        txn=txn,
        movement_type="DISPOSAL",
        to_status="DISPOSED",
        user=user,
        reason=disposal.reason,
    )
    eq.active = False
    disposal.status = "APPROVED"
    disposal.approved_by = user.id
    disposal.approval_note = body.approval_note
    if txn.status == TransactionStatus.APPROVAL_PENDING.value:
        transition(
            db,
            txn,
            to_status=TransactionStatus.APPROVED.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason=body.approval_note,
        )
        transition(
            db,
            txn,
            to_status=TransactionStatus.EXIT_PENDING.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason="Disposal approved — ready for exit/scrap gate",
        )
    write_audit(
        db,
        action="EQUIPMENT_DISPOSAL_APPROVED",
        entity_type="equipment_disposal",
        entity_id=disposal.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=body.approval_note,
    )
    db.commit()
    db.refresh(eq)
    db.refresh(disposal)
    db.refresh(move)
    db.refresh(txn)
    return _action_out(equipment=eq, txn=txn, movement=move, disposal=disposal)
