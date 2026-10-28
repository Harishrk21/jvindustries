"""Product master CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.stock import Product
from app.models.user import User
from app.schemas.stock import ProductCreate, ProductOut, ProductUpdate
from app.services.audit_service import write_audit

router = APIRouter()


@router.get("", response_model=list[ProductOut])
def list_products(
    active_only: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("stock.view", "storage.select", "master.manage")),
) -> list[Product]:
    q = select(Product).order_by(Product.code)
    if active_only:
        q = q.where(Product.active.is_(True))
    return list(db.execute(q).scalars().all())


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> Product:
    code = body.code.strip().upper()
    exists = db.execute(select(Product).where(Product.code == code)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail=f"Product code {code} already exists.")
    row = Product(
        code=code,
        name=body.name.strip(),
        hsn=body.hsn,
        unit=body.unit.upper(),
        density_default=body.density_default,
        loss_limit_percent=body.loss_limit_percent,
        active=body.active,
    )
    db.add(row)
    write_audit(
        db,
        action="PRODUCT_CREATED",
        entity_type="product",
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.code,
    )
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> Product:
    row = db.get(Product, product_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "unit" and v:
            v = v.upper()
        setattr(row, k, v)
    write_audit(
        db,
        action="PRODUCT_UPDATED",
        entity_type="product",
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.code,
    )
    db.commit()
    db.refresh(row)
    return row
