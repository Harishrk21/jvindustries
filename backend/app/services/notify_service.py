"""In-app management alerts + optional WhatsApp fan-out."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.notification import Notification
from app.models.otp import WhatsappMessage
from app.services.whatsapp_client import get_whatsapp_client


def management_mobiles() -> list[str]:
    raw = (get_settings().management_alert_mobiles or "").strip()
    if not raw:
        return []
    return [m.strip() for m in raw.split(",") if m.strip()]


def create_alert(
    db: Session,
    *,
    category: str,
    title: str,
    body: str,
    severity: str = "WARN",
    transaction_pk: str | None = None,
    transaction_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    created_by: str | None = None,
    send_whatsapp: bool = True,
) -> Notification:
    note = Notification(
        category=category,
        severity=severity,
        title=title,
        body=body,
        transaction_pk=transaction_pk,
        transaction_id=transaction_id,
        entity_type=entity_type,
        entity_id=entity_id,
        created_by=created_by,
    )
    db.add(note)
    db.flush()

    if send_whatsapp:
        mobiles = management_mobiles()
        if mobiles:
            client = get_whatsapp_client()
            text = f"JV-OMS [{severity}] {title}\n{body}"
            if transaction_id:
                text += f"\nTxn: {transaction_id}"
            # Send to first configured management mobile (primary); log all attempts
            primary = mobiles[0]
            result = client.send_text(to_mobile=primary, body=text, template_name="management_alert")
            wa = WhatsappMessage(
                transaction_pk=transaction_pk,
                transaction_id=transaction_id,
                to_mobile=primary,
                template_name="management_alert",
                body_preview=text[:500],
                provider=result.provider,
                provider_message_id=result.provider_message_id,
                delivery_status=result.delivery_status,
                error_detail=result.error_detail,
            )
            db.add(wa)
            db.flush()
            note.whatsapp_sent = result.ok
            note.whatsapp_message_id = wa.id
        else:
            # No mobiles configured — still create in-app alert; mock a delivery log for auditability in dev
            client = get_whatsapp_client()
            result = client.send_text(
                to_mobile="0000000000",
                body=f"[DEV inbox only] {title}\n{body}",
                template_name="management_alert",
            )
            wa = WhatsappMessage(
                transaction_pk=transaction_pk,
                transaction_id=transaction_id,
                to_mobile="MANAGEMENT_INBOX",
                template_name="management_alert",
                body_preview=f"{title}\n{body}"[:500],
                provider=result.provider,
                provider_message_id=result.provider_message_id,
                delivery_status="INBOX_ONLY" if result.mocked else result.delivery_status,
                error_detail=None,
            )
            db.add(wa)
            db.flush()
            note.whatsapp_sent = False
            note.whatsapp_message_id = wa.id

    return note
