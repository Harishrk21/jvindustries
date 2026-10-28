from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    transporter_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    license_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GatePass(Base):
    __tablename__ = "gate_passes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    gate_pass_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    pass_type: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    driver_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    driver_mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    transporter_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, default="INWARD")  # INWARD | OUTWARD
    purpose: Mapped[str | None] = mapped_column(String(40), nullable=True)
    material_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity_text: Mapped[str | None] = mapped_column(String(80), nullable=True)
    unit_text: Mapped[str | None] = mapped_column(String(40), nullable=True)
    invoice_challan_no: Mapped[str | None] = mapped_column(String(80), nullable=True)
    from_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    to_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    goods_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    documents_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ENTRY_VEHICLE, EXIT_VEHICLE, ...
    capture_source: Mapped[str] = mapped_column(String(40), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GatePassSequence(Base):
    __tablename__ = "gate_pass_sequences"

    year: Mapped[int] = mapped_column(primary_key=True)
    last_value: Mapped[int] = mapped_column(nullable=False, default=0)


class AnprResult(Base):
    __tablename__ = "anpr_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    photo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("photos.id"), nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DETECTED")  # DETECTED|FAILED|CONFIRMED|MANUAL
    manual_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_vehicle_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
