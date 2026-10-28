from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CanteenItem(Base):
    __tablename__ = "canteen_items"
    __table_args__ = (UniqueConstraint("code", name="uq_canteen_item_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CanteenPurchase(Base):
    __tablename__ = "canteen_purchases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    photo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("photos.id"), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    invoice_total: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # DETECTED | CONFIRMED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DETECTED")
    confirmed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CanteenPurchaseLine(Base):
    __tablename__ = "canteen_purchase_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    purchase_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("canteen_purchases.id"), nullable=False, index=True
    )
    item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("canteen_items.id"), nullable=True, index=True)
    item_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    item_name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")
    ocr_matched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CanteenStockMovement(Base):
    """Append-only canteen stock ledger. Balances from movements only."""

    __tablename__ = "canteen_stock_movements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id: Mapped[str] = mapped_column(String(36), ForeignKey("canteen_items.id"), nullable=False, index=True)
    transaction_pk: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("transactions.id"), nullable=True, index=True
    )
    transaction_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    purchase_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("canteen_purchases.id"), nullable=True, index=True
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # IN | OUT | OPENING | ADJUST
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
