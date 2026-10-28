from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CustomerOtp(Base):
    __tablename__ = "customer_otps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    customer_mobile: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    otp_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="WHATSAPP")  # WHATSAPP | DEV_SCREEN
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SENT")  # SENT | VERIFIED | EXPIRED | FAILED
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("whatsapp_messages.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhatsappMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str | None] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=True, index=True)
    transaction_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    to_mobile: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(80), nullable=False, default="customer_otp")
    body_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED")
    # QUEUED | SENT | DELIVERED | FAILED | MOCKED
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
