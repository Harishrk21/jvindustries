"""Storage units — Tank / Barrel / IBC."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.stock import Product, StorageUnit
from app.models.user import User
from app.schemas.stock import StorageUnitCreate, StorageUnitOut, StorageUnitUpdate
from app.services.audit_service import write_audit

router = APIRouter()


@router.get("/units", response_model=list[StorageUnitOut])
def list_units(
    kind: str | None = Query(None),
    active_only: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("stock.view", "storage.select", "master.manage")),
) -> list[StorageUnit]:
    q = select(StorageUnit).order_by(StorageUnit.code)
    if active_only:
        q = q.where(StorageUnit.active.is_(True))
    if kind:
        q = q.where(StorageUnit.kind == kind.upper())
    return list(db.execute(q).scalars().all())


@router.post("/units", response_model=StorageUnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(
    body: StorageUnitCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> StorageUnit:
    code = body.code.strip().upper()
    exists = db.execute(select(StorageUnit).where(StorageUnit.code == code)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail=f"Storage code {code} already exists.")
    if body.product_id and db.get(Product, body.product_id) is None:
        raise HTTPException(status_code=400, detail="Product not found.")
    row = StorageUnit(
        code=code,
        name=body.name.strip(),
        kind=body.kind.upper(),
        capacity=body.capacity,
        capacity_unit=body.capacity_unit.upper(),
        product_id=body.product_id,
        location_label=body.location_label,
        active=body.active,
    )
    db.add(row)
    write_audit(
        db,
        action="STORAGE_UNIT_CREATED",
        entity_type="storage_unit",
        entity_id=row.id,
        actor_user_id=user.id,
        details=f"{row.kind} {row.code}",
    )
    db.commit()
    db.refresh(row)
    return row


@router.patch("/units/{unit_id}", response_model=StorageUnitOut)
def update_unit(
    unit_id: str,
    body: StorageUnitUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> StorageUnit:
    row = db.get(StorageUnit, unit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Storage unit not found.")
    data = body.model_dump(exclude_unset=True)
    if "product_id" in data and data["product_id"] and db.get(Product, data["product_id"]) is None:
        raise HTTPException(status_code=400, detail="Product not found.")
    for k, v in data.items():
        setattr(row, k, v)
    write_audit(
        db,
        action="STORAGE_UNIT_UPDATED",
        entity_type="storage_unit",
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.code,
    )
    db.commit()
    db.refresh(row)
    return row
