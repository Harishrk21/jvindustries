from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("code", name="uq_product_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    hsn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")  # KG | L
    density_default: Mapped[float | None] = mapped_column(Float, nullable=True)
    loss_limit_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StorageUnit(Base):
    """Tank / Barrel / IBC storage vessel."""

    __tablename__ = "storage_units"
    __table_args__ = (UniqueConstraint("code", name="uq_storage_unit_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # TANK | BARREL | IBC
    capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="L")
    product_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    location_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StockMovement(Base):
    """Append-only stock ledger. Balances are derived from these rows only."""

    __tablename__ = "stock_movements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("transactions.id"), nullable=True, index=True
    )
    transaction_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    storage_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("storage_units.id"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # IN | OUT | TRANSFER_IN | TRANSFER_OUT | OPENING | ADJUST
    quantity: Mapped[float] = mapped_column(Float, nullable=False)  # always positive; direction decides sign
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")
    quantity_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity_litres: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("devices.id"), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    storage_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("storage_units.id"), nullable=False, index=True
    )
    requested_quantity: Mapped[float] = mapped_column(Float, nullable=False)  # signed delta (+ in / - out)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")  # PENDING | APPROVED | REJECTED
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    movement_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stock_movements.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
