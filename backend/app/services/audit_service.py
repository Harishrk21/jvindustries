from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    transaction_id: str | None = None,
    actor_user_id: str | None = None,
    device_id: str | None = None,
    details: str | None = None,
) -> AuditLog:
    row = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        transaction_id=transaction_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        details=details,
    )
    db.add(row)
    db.flush()
    return row
