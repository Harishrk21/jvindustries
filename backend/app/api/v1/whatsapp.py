"""WhatsApp message log + status."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission
from app.models.otp import WhatsappMessage
from app.models.user import User

router = APIRouter()


class WhatsappMessageOut(BaseModel):
    id: str
    transaction_id: str | None
    to_mobile: str
    template_name: str
    body_preview: str | None
    provider: str
    provider_message_id: str | None
    delivery_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/messages", response_model=list[WhatsappMessageOut])
def list_messages(
    limit: int = Query(50, ge=1, le=200),
    transaction_pk: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("whatsapp.view", "notification.view", "otp.send")),
) -> list[WhatsappMessage]:
    q = select(WhatsappMessage).order_by(WhatsappMessage.created_at.desc()).limit(limit)
    if transaction_pk:
        q = q.where(WhatsappMessage.transaction_pk == transaction_pk)
    return list(db.execute(q).scalars().all())
