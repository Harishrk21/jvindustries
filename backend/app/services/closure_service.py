"""Phase E — hard rules before COMPLETED (docs / OTP / parties by type)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.documents import DocumentVerification, EwayBill, Invoice
from app.models.enums import TransactionType
from app.models.otp import CustomerOtp
from app.models.transaction import Transaction
from app.models.vehicle import GatePass

# Material yard flows that must not close incomplete
_DOCS_REQUIRED = {
    TransactionType.MATERIAL_LOADING_OUTWARD.value,
    TransactionType.MATERIAL_RECEIVING_INWARD.value,
}
_OTP_REQUIRED = {
    TransactionType.MATERIAL_LOADING_OUTWARD.value,
    TransactionType.JOB_WORK.value,
}
_CUSTOMER_REQUIRED = {
    TransactionType.MATERIAL_LOADING_OUTWARD.value,
    TransactionType.JOB_WORK.value,
}
_SUPPLIER_REQUIRED = {
    TransactionType.MATERIAL_RECEIVING_INWARD.value,
}


def _docs_ok(db: Session, txn: Transaction) -> bool:
    inv = (
        db.execute(
            select(Invoice)
            .where(Invoice.transaction_pk == txn.id, Invoice.confirmed.is_(True))
            .order_by(Invoice.created_at.desc())
        )
        .scalars()
        .first()
    )
    ewb = (
        db.execute(
            select(EwayBill)
            .where(EwayBill.transaction_pk == txn.id, EwayBill.confirmed.is_(True))
            .order_by(EwayBill.created_at.desc())
        )
        .scalars()
        .first()
    )
    if not inv or not ewb:
        return False
    ver = (
        db.execute(
            select(DocumentVerification)
            .where(DocumentVerification.transaction_pk == txn.id)
            .order_by(DocumentVerification.created_at.desc())
        )
        .scalars()
        .first()
    )
    if ver is None:
        return False
    if ver.match_status == "MATCH":
        return True
    return bool(ver.approved)


def _otp_ok(db: Session, txn: Transaction) -> bool:
    row = (
        db.execute(
            select(CustomerOtp)
            .where(CustomerOtp.transaction_pk == txn.id, CustomerOtp.status == "VERIFIED")
            .order_by(CustomerOtp.created_at.desc())
        )
        .scalars()
        .first()
    )
    return row is not None


def _gate_pass_ok(db: Session, txn: Transaction) -> bool:
    gp = (
        db.execute(select(GatePass).where(GatePass.transaction_pk == txn.id).limit(1))
        .scalars()
        .first()
    )
    return gp is not None


def closure_blockers(db: Session, txn: Transaction) -> list[str]:
    """Return human-readable blockers; empty list means COMPLETED is allowed."""
    blockers: list[str] = []
    t = txn.type

    if not txn.vehicle_number and t in _DOCS_REQUIRED:
        blockers.append("Vehicle number not verified.")

    if t in _DOCS_REQUIRED and not _docs_ok(db, txn):
        blockers.append("Invoice + E-Way Bill must be confirmed and vehicle matched (or mismatch approved).")

    if t in _OTP_REQUIRED and not _otp_ok(db, txn):
        blockers.append("Customer OTP must be verified before closing.")

    if t in _DOCS_REQUIRED and not _gate_pass_ok(db, txn):
        blockers.append("Gate pass must be generated before closing.")

    if t in _CUSTOMER_REQUIRED and not getattr(txn, "customer_id", None):
        blockers.append("Customer master must be linked to this transaction.")

    if t in _SUPPLIER_REQUIRED and not getattr(txn, "supplier_id", None):
        blockers.append("Supplier master must be linked to this transaction.")

    return blockers


def assert_can_complete(db: Session, txn: Transaction) -> None:
    blockers = closure_blockers(db, txn)
    if blockers:
        raise ValueError(" | ".join(blockers))
