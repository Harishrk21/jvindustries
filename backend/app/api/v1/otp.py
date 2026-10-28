"""Phase 6 — Customer OTP via WhatsApp (mock/dev screen fallback for perfect working)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission
from app.models.enums import TransactionStatus
from app.models.otp import CustomerOtp
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.otp import OtpSendOut, OtpSendRequest, OtpStatusOut, OtpVerifyRequest
from app.services.audit_service import write_audit
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.otp_service import issue_customer_otp, verify_customer_otp
from app.services.transaction_flow import transition

router = APIRouter()

_SEND_OK = {
    TransactionStatus.DOCUMENTS_VERIFIED.value,
    TransactionStatus.APPROVED.value,
    TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value,
    TransactionStatus.CUSTOMER_CONFIRMED.value,
    TransactionStatus.EXIT_PENDING.value,
    TransactionStatus.ENTRY_STARTED.value,  # job-work path
    TransactionStatus.VEHICLE_VERIFIED.value,
    TransactionStatus.GROSS_COMPLETED.value,
}


def _gps_ok(lat: float, lon: float, acc: float) -> None:
    result = GeofenceService().verify(GpsSample(lat, lon, acc))
    if not result.authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.message)


@router.post("/send", response_model=OtpSendOut)
def send_otp(
    body: OtpSendRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("otp.send", "transaction.create", "approval.act")),
) -> OtpSendOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = db.get(Transaction, body.transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if txn.status not in _SEND_OK:
        raise HTTPException(status_code=400, detail=f"OTP not allowed in status {txn.status}.")

    mobile = "".join(ch for ch in body.customer_mobile if ch.isdigit() or ch == "+")
    if len("".join(ch for ch in mobile if ch.isdigit())) < 10:
        raise HTTPException(status_code=400, detail="Customer mobile must have at least 10 digits.")

    row, wa, preview = issue_customer_otp(
        db,
        txn=txn,
        user=user,
        customer_mobile=mobile,
        customer_name=body.customer_name,
    )
    if row.status == "FAILED":
        db.commit()
        raise HTTPException(status_code=502, detail=wa.error_detail or "WhatsApp delivery failed.")

    try:
        if txn.status in {
            TransactionStatus.DOCUMENTS_VERIFIED.value,
            TransactionStatus.ENTRY_STARTED.value,
        }:
            transition(
                db,
                txn,
                to_status=TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason="Customer OTP sent via WhatsApp",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
    except ValueError:
        pass

    write_audit(
        db,
        action="CUSTOMER_OTP_SENT",
        entity_type="customer_otp",
        entity_id=row.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"{row.channel} {row.provider} {wa.delivery_status}",
    )
    db.commit()
    db.refresh(row)

    msg = (
        "OTP sent via WhatsApp (mock). Use on-screen code to verify."
        if preview
        else "OTP sent via WhatsApp to the customer."
    )
    return OtpSendOut(
        otp_id=row.id,
        transaction_id=txn.transaction_id,
        status=row.status,
        channel=row.channel,
        provider=row.provider,
        customer_mobile=row.customer_mobile,
        expires_at=row.expires_at,
        whatsapp_delivery_status=wa.delivery_status,
        otp_preview=preview,
        message=msg,
    )


@router.post("/verify", response_model=OtpStatusOut)
def verify_otp(
    body: OtpVerifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("otp.verify", "transaction.create", "approval.act")),
) -> OtpStatusOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = db.get(Transaction, body.transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    row = db.get(CustomerOtp, body.otp_id)
    if row is None or row.transaction_pk != txn.id:
        raise HTTPException(status_code=404, detail="OTP not found.")

    ok, message = verify_customer_otp(db, otp_row=row, code=body.otp_code)
    if not ok:
        db.commit()
        raise HTTPException(status_code=400, detail=message)

    try:
        if txn.status == TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value:
            transition(
                db,
                txn,
                to_status=TransactionStatus.CUSTOMER_CONFIRMED.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason="Customer OTP verified",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
        elif txn.status in {
            TransactionStatus.DOCUMENTS_VERIFIED.value,
            TransactionStatus.APPROVED.value,
            TransactionStatus.ENTRY_STARTED.value,
        }:
            # If OTP verified before pending transition, move through pending→confirmed when possible
            if txn.status == TransactionStatus.DOCUMENTS_VERIFIED.value:
                transition(
                    db,
                    txn,
                    to_status=TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value,
                    actor_user_id=user.id,
                    device_id=body.device_id,
                    reason="OTP verified — sync status",
                    lat=body.gps.lat,
                    lon=body.gps.lon,
                    gps_accuracy_m=body.gps.accuracy_m,
                )
            if txn.status == TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value:
                transition(
                    db,
                    txn,
                    to_status=TransactionStatus.CUSTOMER_CONFIRMED.value,
                    actor_user_id=user.id,
                    device_id=body.device_id,
                    reason="Customer OTP verified",
                    lat=body.gps.lat,
                    lon=body.gps.lon,
                    gps_accuracy_m=body.gps.accuracy_m,
                )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    write_audit(
        db,
        action="CUSTOMER_OTP_VERIFIED",
        entity_type="customer_otp",
        entity_id=row.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=message,
    )
    db.commit()
    return OtpStatusOut(
        transaction_id=txn.transaction_id,
        transaction_status=txn.status,
        otp_id=row.id,
        otp_status=row.status,
        channel=row.channel,
        customer_mobile=row.customer_mobile,
        verified=True,
    )


@router.get("/status/{transaction_pk}", response_model=OtpStatusOut)
def otp_status(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("otp.send", "otp.verify", "transaction.view")),
) -> OtpStatusOut:
    txn = db.get(Transaction, transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    row = (
        db.execute(
            select(CustomerOtp)
            .where(CustomerOtp.transaction_pk == txn.id)
            .order_by(CustomerOtp.created_at.desc())
        )
        .scalars()
        .first()
    )
    return OtpStatusOut(
        transaction_id=txn.transaction_id,
        transaction_status=txn.status,
        otp_id=row.id if row else None,
        otp_status=row.status if row else None,
        channel=row.channel if row else None,
        customer_mobile=row.customer_mobile if row else None,
        verified=bool(row and row.status == "VERIFIED"),
    )
