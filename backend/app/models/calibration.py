"""Weighbridge legal-metrology calibration certificate (Phase B masters)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WeighbridgeCalibration(Base):
    __tablename__ = "weighbridge_calibrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    certificate_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    verification_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    officer_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    officer_title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    make_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    max_capacity_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_capacity_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_class: Mapped[str | None] = mapped_column(String(40), nullable=True)
    e_value_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    d_value_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    seals_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seals_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
