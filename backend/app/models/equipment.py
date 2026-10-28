from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (UniqueConstraint("code", name="uq_equipment_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="GENERAL")
    # IN_YARD | OUT_FOR_REPAIR | TRANSFERRED | DISPOSED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="IN_YARD", index=True)
    location_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EquipmentMovement(Base):
    __tablename__ = "equipment_movements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    equipment_id: Mapped[str] = mapped_column(String(36), ForeignKey("equipment.id"), nullable=False, index=True)
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # REPAIR_OUT | REPAIR_RETURN | TRANSFER | DISPOSAL
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    vendor_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EquipmentRepair(Base):
    __tablename__ = "equipment_repairs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    equipment_id: Mapped[str] = mapped_column(String(36), ForeignKey("equipment.id"), nullable=False, index=True)
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(150), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expected_return_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # OPEN | RETURNED | CANCELLED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN", index=True)
    return_transaction_pk: Mapped[str | None] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EquipmentDisposal(Base):
    __tablename__ = "equipment_disposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    equipment_id: Mapped[str] = mapped_column(String(36), ForeignKey("equipment.id"), nullable=False, index=True)
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # PENDING | APPROVED | REJECTED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", index=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
