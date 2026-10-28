"""Management alerts / notifications inbox."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission
from app.models.notification import Notification
from app.models.user import User
from app.services.audit_service import write_audit
from app.services.notify_service import create_alert

router = APIRouter()


class NotificationOut(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    body: str
    transaction_id: str | None
    whatsapp_sent: bool
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ManualAlertRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=3)
    category: str = "SYSTEM"
    severity: str = "WARN"
    transaction_pk: str | None = None
    send_whatsapp: bool = True


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("notification.view", "dashboard.view", "approval.act")),
) -> list[Notification]:
    q = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    return list(db.execute(q).scalars().all())


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("notification.view", "dashboard.view")),
) -> Notification:
    row = db.get(Notification, notification_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    row.is_read = True
    db.commit()
    db.refresh(row)
    return row


@router.post("/alert", response_model=NotificationOut, status_code=201)
def manual_alert(
    body: ManualAlertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("notification.send", "approval.act")),
) -> Notification:
    txn_id = None
    if body.transaction_pk:
        from app.models.transaction import Transaction

        txn = db.get(Transaction, body.transaction_pk)
        if txn is None:
            raise HTTPException(status_code=404, detail="Transaction not found.")
        txn_id = txn.transaction_id

    note = create_alert(
        db,
        category=body.category,
        title=body.title,
        body=body.body,
        severity=body.severity,
        transaction_pk=body.transaction_pk,
        transaction_id=txn_id,
        created_by=user.id,
        send_whatsapp=body.send_whatsapp,
    )
    write_audit(
        db,
        action="MANAGEMENT_ALERT",
        entity_type="notification",
        entity_id=note.id,
        transaction_id=txn_id,
        actor_user_id=user.id,
        details=body.title,
    )
    db.commit()
    db.refresh(note)
    return note
