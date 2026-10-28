from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class JobWorkBatch(Base):
    __tablename__ = "job_work_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    product_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    batch_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    customer_mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    qty_in: Mapped[float | None] = mapped_column(Float, nullable=True)
    qty_out: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")  # OPEN | LOSS_PENDING | CLOSED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProductionLoss(Base):
    __tablename__ = "production_losses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("job_work_batches.id"), nullable=False, index=True)
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    product_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("products.id"), nullable=True)
    qty_in: Mapped[float] = mapped_column(Float, nullable=False)
    qty_out: Mapped[float] = mapped_column(Float, nullable=False)
    loss_qty: Mapped[float] = mapped_column(Float, nullable=False)
    loss_percent: Mapped[float] = mapped_column(Float, nullable=False)
    loss_limit_percent: Mapped[float] = mapped_column(Float, nullable=False)
    excess_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
