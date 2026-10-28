"""Customer OTP — hashed at rest; WhatsApp delivery + screen fallback for perfect working."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.otp import CustomerOtp, WhatsappMessage
from app.models.transaction import Transaction
from app.models.user import User
from app.services.whatsapp_client import get_whatsapp_client


def _hash_otp(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


def generate_otp_code(length: int = 6) -> str:
    # Cryptographically strong digits; never sequential
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def issue_customer_otp(
    db: Session,
    *,
    txn: Transaction,
    user: User,
    customer_mobile: str,
    customer_name: str | None = None,
    ttl_minutes: int = 10,
) -> tuple[CustomerOtp, WhatsappMessage, str | None]:
    """
    Create OTP + WhatsApp message row.
    Returns (otp_row, wa_row, otp_preview_for_ui).
    Preview is returned when mock/dev so operators can confirm without Meta credentials.
    """
    code = generate_otp_code()
    salt = secrets.token_hex(8)
    expires = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

    client = get_whatsapp_client()
    send = client.send_otp(to_mobile=customer_mobile, otp_code=code, transaction_id=txn.transaction_id)

    wa = WhatsappMessage(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        to_mobile=customer_mobile,
        template_name="customer_otp",
        body_preview=f"OTP for {txn.transaction_id}",
        provider=send.provider,
        provider_message_id=send.provider_message_id,
        delivery_status=send.delivery_status,
        error_detail=send.error_detail,
    )
    db.add(wa)
    db.flush()

    channel = "WHATSAPP"
    preview: str | None = None
    settings = get_settings()
    # Perfect working now: always expose preview in development/mock; never in production official sends
    if send.mocked or settings.app_env != "production" or settings.debug:
        preview = code
        if send.mocked:
            channel = "WHATSAPP_DEV"

    row = CustomerOtp(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        customer_mobile=customer_mobile,
        customer_name=customer_name,
        otp_hash=_hash_otp(code, salt) + ":" + salt,  # store hash:salt
        channel=channel,
        provider=send.provider,
        status="SENT" if send.ok else "FAILED",
        expires_at=expires,
        whatsapp_message_id=wa.id,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    return row, wa, preview


def verify_customer_otp(db: Session, *, otp_row: CustomerOtp, code: str) -> tuple[bool, str]:
    if otp_row.status == "VERIFIED":
        return True, "Already verified."
    if otp_row.status == "EXPIRED":
        return False, "OTP expired. Request a new one."
    if otp_row.attempts >= otp_row.max_attempts:
        otp_row.status = "EXPIRED"
        return False, "Too many attempts. Request a new OTP."

    now = datetime.now(timezone.utc)
    exp = otp_row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        otp_row.status = "EXPIRED"
        return False, "OTP expired. Request a new one."

    otp_row.attempts += 1
    try:
        digest, salt = otp_row.otp_hash.split(":", 1)
    except ValueError:
        return False, "Invalid OTP record."
    if not secrets.compare_digest(digest, _hash_otp(code.strip(), salt)):
        return False, "Incorrect OTP."

    otp_row.status = "VERIFIED"
    otp_row.verified_at = now
    return True, "OTP verified."
