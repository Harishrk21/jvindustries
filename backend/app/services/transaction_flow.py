from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionEvent
from app.services.audit_service import write_audit
from app.services.state_machine import assert_transition


def transition(
    db: Session,
    txn: Transaction,
    *,
    to_status: str,
    actor_user_id: str,
    device_id: str | None = None,
    reason: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    gps_accuracy_m: float | None = None,
) -> TransactionEvent:
    assert_transition(txn.status, to_status)
    event = TransactionEvent(
        transaction_pk=txn.id,
        from_status=txn.status,
        to_status=to_status,
        actor_user_id=actor_user_id,
        device_id=device_id,
        reason=reason,
        lat=lat,
        lon=lon,
        gps_accuracy_m=gps_accuracy_m,
    )
    txn.status = to_status
    if lat is not None:
        txn.last_lat = lat
        txn.last_lon = lon
        txn.last_gps_accuracy_m = gps_accuracy_m
    db.add(event)
    write_audit(
        db,
        action="STATUS_TRANSITION",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        details=f"{event.from_status} -> {to_status}" + (f" ({reason})" if reason else ""),
    )
    db.flush()
    return event
