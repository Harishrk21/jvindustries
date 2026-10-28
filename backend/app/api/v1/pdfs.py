"""PDF downloads — branded gate pass + weighment slip (Phase D)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission
from app.models.calibration import WeighbridgeCalibration
from app.models.parties import Customer, Supplier
from app.models.stock import Product
from app.models.transaction import Transaction
from app.models.user import User
from app.models.vehicle import GatePass
from app.models.weighment import Weighment
from app.services.audit_service import write_audit
from app.services.pdf_service import build_gate_pass_pdf, build_transaction_summary_pdf

router = APIRouter()


def _active_calibration(db: Session) -> WeighbridgeCalibration | None:
    return db.execute(
        select(WeighbridgeCalibration).where(WeighbridgeCalibration.is_active.is_(True)).limit(1)
    ).scalar_one_or_none()


def _party_fields(db: Session, txn: Transaction) -> tuple[str | None, str | None, str | None]:
    if txn.customer_id:
        c = db.get(Customer, txn.customer_id)
        if c:
            return c.name, c.address, c.whatsapp or c.mobile
    if txn.supplier_id:
        s = db.get(Supplier, txn.supplier_id)
        if s:
            return s.name, s.address, s.whatsapp or s.mobile
    return None, None, None


def _product_name(db: Session, txn: Transaction) -> str | None:
    if not txn.product_id:
        return None
    p = db.get(Product, txn.product_id)
    return f"{p.code} — {p.name}" if p else None


def _weigh_times(db: Session, txn: Transaction):
    rows = list(db.execute(select(Weighment).where(Weighment.transaction_pk == txn.id)).scalars().all())
    gross_at = next((w.created_at for w in rows if w.kind == "GROSS"), None)
    tare_at = next((w.created_at for w in rows if w.kind == "TARE"), None)
    return gross_at, tare_at


def _latest_gate(db: Session, txn: Transaction) -> GatePass | None:
    return (
        db.execute(
            select(GatePass).where(GatePass.transaction_pk == txn.id).order_by(GatePass.created_at.desc())
        )
        .scalars()
        .first()
    )


@router.get("/gate-pass/{transaction_pk}")
def pdf_gate_pass(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("gatepass.view", "transaction.view")),
) -> Response:
    txn = db.get(Transaction, transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    gp = _latest_gate(db, txn)
    if gp is None:
        raise HTTPException(status_code=404, detail="No gate pass for this transaction.")

    # Prefer product name on gate if material blank
    if not gp.material_description and txn.product_id:
        pname = _product_name(db, txn)
        if pname:
            gp.material_description = pname
    if gp.quantity_text is None and txn.net_kg is not None:
        gp.quantity_text = str(txn.net_kg)
        gp.unit_text = gp.unit_text or "kg"

    pdf = build_gate_pass_pdf(txn=txn, gate_pass=gp)
    write_audit(
        db,
        action="PDF_GATE_PASS",
        entity_type="gate_pass",
        entity_id=gp.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=gp.gate_pass_number,
    )
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{gp.gate_pass_number}.pdf"'},
    )


@router.get("/transaction/{transaction_pk}")
def pdf_transaction(
    transaction_pk: str,
    variant: str = Query(default="internal", pattern="^(customer|internal)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("transaction.view", "report.view", "gatepass.view")),
) -> Response:
    txn = db.get(Transaction, transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    party_name, party_address, party_mobile = _party_fields(db, txn)
    product_name = _product_name(db, txn)
    gross_at, tare_at = _weigh_times(db, txn)
    gp = _latest_gate(db, txn)
    cal = _active_calibration(db) if variant == "customer" else None

    pdf = build_transaction_summary_pdf(
        txn=txn,
        variant=variant,
        calibration=cal,
        party_name=party_name,
        party_address=party_address,
        party_mobile=party_mobile,
        product_name=product_name,
        gate_pass_no=gp.gate_pass_number if gp else None,
        gross_at=gross_at,
        tare_at=tare_at,
        issued_by=user.full_name if getattr(user, "full_name", None) else user.user_code,
    )
    write_audit(
        db,
        action="PDF_TRANSACTION_SUMMARY",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"variant={variant}",
    )
    db.commit()
    suffix = "weighment-slip" if variant == "customer" else "internal"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{txn.transaction_id}-{suffix}.pdf"'},
    )


@router.get("/weighment-slip/{transaction_pk}")
def pdf_weighment_slip(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("transaction.view", "gatepass.view")),
) -> Response:
    """Alias for branded customer weighment slip."""
    return pdf_transaction(transaction_pk=transaction_pk, variant="customer", db=db, user=user)
