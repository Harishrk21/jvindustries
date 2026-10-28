"""Customer / supplier masters + attach to transactions + closure check."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.parties import Customer, Supplier
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.parties import (
    AttachPartiesRequest,
    ClosureCheckOut,
    PartyCreate,
    PartyOut,
    PartyUpdate,
)
from app.services.audit_service import write_audit
from app.services.closure_service import closure_blockers

router = APIRouter()


def _create_party(model, body: PartyCreate, db: Session, user: User, action: str, entity: str):
    code = body.code.strip().upper()
    exists = db.execute(select(model).where(model.code == code)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail=f"Code {code} already exists.")
    row = model(
        code=code,
        name=body.name.strip(),
        mobile=body.mobile.strip() if body.mobile else None,
        whatsapp=(body.whatsapp or body.mobile or "").strip() or None,
        gstin=body.gstin.strip().upper() if body.gstin else None,
        address=(body.address or "").strip() or None,
        active=body.active,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        action=action,
        entity_type=entity,
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.code,
    )
    db.commit()
    db.refresh(row)
    return row


def _update_party(model, party_id: str, body: PartyUpdate, db: Session, user: User, action: str, entity: str):
    row = db.get(model, party_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Record not found.")
    data = body.model_dump(exclude_unset=True)
    if "gstin" in data and data["gstin"]:
        data["gstin"] = data["gstin"].strip().upper()
    if "mobile" in data and data["mobile"]:
        data["mobile"] = data["mobile"].strip()
    if "whatsapp" in data and data["whatsapp"]:
        data["whatsapp"] = data["whatsapp"].strip()
    if "address" in data and data["address"]:
        data["address"] = data["address"].strip()
    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()
    for k, v in data.items():
        setattr(row, k, v)
    write_audit(
        db,
        action=action,
        entity_type=entity,
        entity_id=row.id,
        actor_user_id=user.id,
        details=row.code,
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/customers", response_model=list[PartyOut])
def list_customers(
    active_only: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("master.manage", "transaction.view", "transaction.create")),
) -> list[Customer]:
    q = select(Customer).order_by(Customer.code)
    if active_only:
        q = q.where(Customer.active.is_(True))
    return list(db.execute(q).scalars().all())


@router.post("/customers", response_model=PartyOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    body: PartyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> Customer:
    return _create_party(Customer, body, db, user, "CUSTOMER_CREATED", "customer")


@router.patch("/customers/{customer_id}", response_model=PartyOut)
def update_customer(
    customer_id: str,
    body: PartyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> Customer:
    return _update_party(Customer, customer_id, body, db, user, "CUSTOMER_UPDATED", "customer")


@router.get("/suppliers", response_model=list[PartyOut])
def list_suppliers(
    active_only: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("master.manage", "transaction.view", "transaction.create")),
) -> list[Supplier]:
    q = select(Supplier).order_by(Supplier.code)
    if active_only:
        q = q.where(Supplier.active.is_(True))
    return list(db.execute(q).scalars().all())


@router.post("/suppliers", response_model=PartyOut, status_code=status.HTTP_201_CREATED)
def create_supplier(
    body: PartyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> Supplier:
    return _create_party(Supplier, body, db, user, "SUPPLIER_CREATED", "supplier")


@router.patch("/suppliers/{supplier_id}", response_model=PartyOut)
def update_supplier(
    supplier_id: str,
    body: PartyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("master.manage")),
) -> Supplier:
    return _update_party(Supplier, supplier_id, body, db, user, "SUPPLIER_UPDATED", "supplier")


@router.post("/transactions/{transaction_pk}/parties", response_model=dict)
def attach_parties(
    transaction_pk: str,
    body: AttachPartiesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("transaction.create", "master.manage", "approval.act")),
) -> dict:
    txn = db.get(Transaction, transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if body.customer_id:
        cust = db.get(Customer, body.customer_id)
        if cust is None or not cust.active:
            raise HTTPException(status_code=400, detail="Customer not found or inactive.")
        txn.customer_id = cust.id
    if body.supplier_id:
        sup = db.get(Supplier, body.supplier_id)
        if sup is None or not sup.active:
            raise HTTPException(status_code=400, detail="Supplier not found or inactive.")
        txn.supplier_id = sup.id
    write_audit(
        db,
        action="TRANSACTION_PARTIES_ATTACHED",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"customer={txn.customer_id} supplier={txn.supplier_id}",
    )
    db.commit()
    return {
        "id": txn.id,
        "transaction_id": txn.transaction_id,
        "customer_id": txn.customer_id,
        "supplier_id": txn.supplier_id,
    }


@router.get("/transactions/{transaction_pk}/closure-check", response_model=ClosureCheckOut)
def closure_check(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("transaction.view", "vehicle.exit", "approval.act")),
) -> ClosureCheckOut:
    txn = db.get(Transaction, transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    blockers = closure_blockers(db, txn)
    return ClosureCheckOut(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        type=txn.type,
        status=txn.status,
        can_complete=len(blockers) == 0,
        blockers=blockers,
    )
