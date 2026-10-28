"""Offline draft sync — push queue + conflict policy."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permissions
from app.models.enums import SyncStatus, TransactionStatus, TransactionType
from app.models.transaction import Transaction, TransactionEvent
from app.models.user import User
from app.schemas.sync import (
    OfflineDraftIn,
    SyncItemResult,
    SyncPolicyOut,
    SyncPushRequest,
    SyncPushResponse,
)
from app.services.audit_service import write_audit
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.sync_policy import decide_on_existing
from app.services.transaction_id import next_transaction_id

router = APIRouter()

POLICY_RULES = [
    "Same client_transaction_id → idempotent return (no overwrite of server fields).",
    "If server status progressed past DRAFT/ENTRY_STARTED → CONFLICT (client must use a new id).",
    "Type mismatch on same client_transaction_id → CONFLICT.",
    "Fresh client_transaction_id → create DRAFT with sync_status=SYNCED.",
    "Server calculations and state machine remain authoritative after sync.",
]


@router.get("/policy", response_model=SyncPolicyOut)
def sync_policy(
    _user: User = Depends(require_permissions("transaction.view")),
) -> SyncPolicyOut:
    return SyncPolicyOut(
        policy="server_authoritative_idempotent_create",
        rules=POLICY_RULES,
    )


def _apply_draft(
    db: Session,
    user: User,
    draft: OfflineDraftIn,
) -> SyncItemResult:
    try:
        TransactionType(draft.type)
    except ValueError:
        return SyncItemResult(
            client_transaction_id=draft.client_transaction_id,
            outcome="ERROR",
            message="Unknown transaction type.",
        )

    existing = db.execute(
        select(Transaction).where(Transaction.client_transaction_id == draft.client_transaction_id)
    ).scalar_one_or_none()

    if existing is not None:
        decision = decide_on_existing(
            existing_status=existing.status,
            incoming_type=draft.type,
            existing_type=existing.type,
        )
        if decision.outcome == "CONFLICT":
            if existing.sync_status != SyncStatus.CONFLICT.value:
                existing.sync_status = SyncStatus.CONFLICT.value
                write_audit(
                    db,
                    action="SYNC_CONFLICT",
                    entity_type="transaction",
                    entity_id=existing.id,
                    transaction_id=existing.transaction_id,
                    actor_user_id=user.id,
                    device_id=draft.device_id,
                    details=decision.message,
                )
            return SyncItemResult(
                client_transaction_id=draft.client_transaction_id,
                outcome="CONFLICT",
                message=decision.message,
                transaction_pk=existing.id,
                transaction_id=existing.transaction_id,
                status=existing.status,
                sync_status=existing.sync_status,
            )
        return SyncItemResult(
            client_transaction_id=draft.client_transaction_id,
            outcome="IDEMPOTENT",
            message=decision.message,
            transaction_pk=existing.id,
            transaction_id=existing.transaction_id,
            status=existing.status,
            sync_status=existing.sync_status,
        )

    geofence_ok = None
    lat = lon = acc = None
    if draft.gps is not None:
        result = GeofenceService().verify(
            GpsSample(draft.gps.lat, draft.gps.lon, draft.gps.accuracy_m)
        )
        geofence_ok = result.authorized
        lat, lon, acc = draft.gps.lat, draft.gps.lon, draft.gps.accuracy_m

    txn_code = next_transaction_id(db)
    txn = Transaction(
        transaction_id=txn_code,
        client_transaction_id=draft.client_transaction_id,
        type=draft.type,
        status=TransactionStatus.DRAFT.value,
        sync_status=SyncStatus.SYNCED.value,
        created_by=user.id,
        device_id=draft.device_id,
        geofence_ok=geofence_ok,
        last_lat=lat,
        last_lon=lon,
        last_gps_accuracy_m=acc,
        notes=draft.notes,
    )
    db.add(txn)
    db.flush()

    db.add(
        TransactionEvent(
            transaction_pk=txn.id,
            from_status=None,
            to_status=TransactionStatus.DRAFT.value,
            actor_user_id=user.id,
            device_id=draft.device_id,
            reason="Offline draft synced",
            lat=lat,
            lon=lon,
            gps_accuracy_m=acc,
        )
    )
    write_audit(
        db,
        action="SYNC_CREATED",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=draft.device_id,
        details=f"Offline sync created {txn.transaction_id} type={txn.type}",
    )
    return SyncItemResult(
        client_transaction_id=draft.client_transaction_id,
        outcome="CREATED",
        message="Draft created from offline queue.",
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        status=txn.status,
        sync_status=txn.sync_status,
    )


@router.post("/push", response_model=SyncPushResponse)
def sync_push(
    body: SyncPushRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("transaction.create")),
) -> SyncPushResponse:
    results: list[SyncItemResult] = []
    accepted = conflicts = errors = 0

    for draft in body.drafts:
        try:
            item = _apply_draft(db, user, draft)
        except Exception as exc:  # noqa: BLE001 — isolate per-item failures
            item = SyncItemResult(
                client_transaction_id=draft.client_transaction_id,
                outcome="ERROR",
                message=f"Sync failed: {exc}",
            )
        results.append(item)
        if item.outcome in ("CREATED", "IDEMPOTENT"):
            accepted += 1
        elif item.outcome == "CONFLICT":
            conflicts += 1
        else:
            errors += 1

    db.commit()
    return SyncPushResponse(
        accepted=accepted,
        conflicts=conflicts,
        errors=errors,
        results=results,
    )
