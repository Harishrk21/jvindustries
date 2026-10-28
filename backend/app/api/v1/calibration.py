"""Weighbridge calibration certificate master."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.calibration import WeighbridgeCalibration
from app.models.user import User
from app.schemas.calibration import CalibrationCreate, CalibrationOut, CalibrationUpdate
from app.services.audit_service import write_audit

router = APIRouter()


@router.get("", response_model=list[CalibrationOut])
def list_calibrations(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("master.manage", "weighment.tare", "weighment.gross", "owner.full")),
) -> list[CalibrationOut]:
    rows = db.execute(
        select(WeighbridgeCalibration).order_by(WeighbridgeCalibration.is_active.desc(), WeighbridgeCalibration.certificate_no)
    ).scalars().all()
    return [CalibrationOut.model_validate(r) for r in rows]


@router.get("/active", response_model=CalibrationOut)
def get_active_calibration(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("master.manage", "weighment.tare", "weighment.gross", "gatepass.view", "owner.full")),
) -> CalibrationOut:
    row = db.execute(
        select(WeighbridgeCalibration).where(WeighbridgeCalibration.is_active.is_(True)).limit(1)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No active weighbridge calibration on file.")
    return CalibrationOut.model_validate(row)


@router.post("", response_model=CalibrationOut, status_code=status.HTTP_201_CREATED)
def create_calibration(
    body: CalibrationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> CalibrationOut:
    cert = body.certificate_no.strip().upper()
    exists = db.execute(
        select(WeighbridgeCalibration).where(WeighbridgeCalibration.certificate_no == cert)
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="Certificate number already exists.")

    if body.is_active:
        db.execute(update(WeighbridgeCalibration).values(is_active=False))

    row = WeighbridgeCalibration(
        certificate_no=cert,
        verification_date=body.verification_date,
        next_due_date=body.next_due_date,
        officer_name=(body.officer_name or "").strip() or None,
        officer_title=(body.officer_title or "").strip() or None,
        make_model=(body.make_model or "").strip() or None,
        max_capacity_kg=body.max_capacity_kg,
        min_capacity_kg=body.min_capacity_kg,
        accuracy_class=(body.accuracy_class or "").strip() or None,
        e_value_kg=body.e_value_kg,
        d_value_kg=body.d_value_kg,
        seals_count=body.seals_count,
        seals_note=(body.seals_note or "").strip() or None,
        location_label=(body.location_label or "").strip() or None,
        notes=body.notes,
        is_active=body.is_active,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        action="CALIBRATION_CREATED",
        entity_type="weighbridge_calibration",
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.certificate_no,
    )
    db.commit()
    db.refresh(row)
    return CalibrationOut.model_validate(row)


@router.patch("/{calibration_id}", response_model=CalibrationOut)
def update_calibration(
    calibration_id: str,
    body: CalibrationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> CalibrationOut:
    row = db.get(WeighbridgeCalibration, calibration_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Calibration not found.")
    data = body.model_dump(exclude_unset=True)
    if data.get("is_active") is True:
        db.execute(
            update(WeighbridgeCalibration)
            .where(WeighbridgeCalibration.id != calibration_id)
            .values(is_active=False)
        )
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip() or None
        setattr(row, k, v)
    write_audit(
        db,
        action="CALIBRATION_UPDATED",
        entity_type="weighbridge_calibration",
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.certificate_no,
    )
    db.commit()
    db.refresh(row)
    return CalibrationOut.model_validate(row)
