from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permissions
from app.models.enums import TransactionStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.models.vehicle import GatePass
from app.schemas.vehicle import GatePassCreateRequest, GatePassOut
from app.services.audit_service import write_audit
from app.services.gate_pass_id import next_gate_pass_number

router = APIRouter()

PASS_TYPES = {
    "INWARD_MATERIAL",
    "OUTWARD_LOADING",
    "JOB_WORK",
    "EQUIPMENT_REPAIR",
    "EQUIPMENT_RETURN",
    "EQUIPMENT_TRANSFER",
    "SCRAP_DISPOSAL",
    "CANTEEN_SUPPLIER",
    "OTHER",
}


@router.post("", response_model=GatePassOut, status_code=201)
def create_gate_pass(
    body: GatePassCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("gatepass.create")),
) -> GatePassOut:
    if body.pass_type not in PASS_TYPES:
        raise HTTPException(status_code=400, detail="Unknown gate pass type.")

    txn = db.get(Transaction, body.transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if not txn.vehicle_number:
        raise HTTPException(status_code=400, detail="Vehicle must be verified before gate pass.")
    if txn.status in {
        TransactionStatus.DRAFT.value,
        TransactionStatus.CANCELLED.value,
        TransactionStatus.REJECTED.value,
    }:
        raise HTTPException(status_code=400, detail=f"Cannot issue gate pass in status {txn.status}.")

    existing = db.execute(
        select(GatePass).where(GatePass.transaction_pk == txn.id, GatePass.direction == body.direction)
    ).scalar_one_or_none()
    if existing:
        return GatePassOut.model_validate(existing)

    purpose = (body.purpose or body.direction or "").strip().upper() or None
    if purpose and purpose not in {"INWARD", "OUTWARD", "JOB_WORK", "OTHER"}:
        purpose = body.direction

    if body.from_location:
        txn.from_location = body.from_location.strip()[:200]
    if body.to_location:
        txn.to_location = body.to_location.strip()[:200]
    if body.remarks is not None:
        txn.remarks = body.remarks
    if purpose:
        txn.purpose = purpose

    gp = GatePass(
        gate_pass_number=next_gate_pass_number(db),
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        pass_type=body.pass_type,
        vehicle_number=txn.vehicle_number,
        vehicle_type=txn.vehicle_type,
        driver_name=txn.driver_name,
        driver_mobile=txn.driver_mobile,
        transporter_name=txn.transporter_name,
        direction=body.direction,
        purpose=purpose,
        material_description=(body.material_description or "").strip()[:200] or None,
        quantity_text=(body.quantity_text or "").strip()[:80] or None,
        unit_text=(body.unit_text or "").strip()[:40] or None,
        invoice_challan_no=(body.invoice_challan_no or "").strip()[:80] or None,
        from_location=(body.from_location or txn.from_location or "").strip()[:200] or None,
        to_location=(body.to_location or txn.to_location or "").strip()[:200] or None,
        remarks=body.remarks if body.remarks is not None else txn.remarks,
        vehicle_checked=bool(body.vehicle_checked),
        goods_verified=bool(body.goods_verified),
        documents_verified=bool(body.documents_verified),
        created_by=user.id,
    )
    db.add(gp)
    write_audit(
        db,
        action="GATE_PASS_CREATED",
        entity_type="gate_pass",
        entity_id=gp.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=body.device_id,
        details=gp.gate_pass_number,
    )
    db.commit()
    db.refresh(gp)
    return GatePassOut.model_validate(gp)


@router.get("/by-transaction/{transaction_pk}", response_model=list[GatePassOut])
def list_for_transaction(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("gatepass.view")),
) -> list[GatePassOut]:
    rows = db.execute(select(GatePass).where(GatePass.transaction_pk == transaction_pk)).scalars().all()
    return [GatePassOut.model_validate(r) for r in rows]
