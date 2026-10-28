from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # EXCEPTION | APPROVAL | LOSS | OTP | STOCK | SYSTEM
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")  # INFO | WARN | CRITICAL
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    transaction_pk: Mapped[str | None] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=True, index=True)
    transaction_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    whatsapp_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("whatsapp_messages.id"), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
