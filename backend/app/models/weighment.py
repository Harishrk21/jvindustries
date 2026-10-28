from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Weighment(Base):
    __tablename__ = "weighments"
    __table_args__ = (
        UniqueConstraint("transaction_pk", "kind", name="uq_txn_weighment_kind"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # TARE | GROSS
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    ocr_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("photos.id"), nullable=True)
    confirmed_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    hardware_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DensityReading(Base):
    __tablename__ = "density_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    density_kg_per_l: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculated_litres: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_kg_snapshot: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("photos.id"), nullable=True)
    confirmed_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
