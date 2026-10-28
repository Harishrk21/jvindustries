from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("client_transaction_id", name="uq_client_transaction_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    client_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="DRAFT")
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="SYNCED")
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("devices.id"), nullable=True)
    geofence_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Phase 2 vehicle spine (always linked via transaction_id)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(40), nullable=True)  # Truck|Tanker|Trailer
    driver_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("drivers.id"), nullable=True)
    driver_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    driver_mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    transporter_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    customer_whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(40), nullable=True)  # INWARD|OUTWARD|JOB_WORK|OTHER
    from_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    to_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_photo_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    exit_photo_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tare_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    density_kg_per_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculated_litres: Mapped[float | None] = mapped_column(Float, nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    storage_unit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("storage_units.id"), nullable=True, index=True
    )
    customer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("customers.id"), nullable=True, index=True)
    supplier_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("suppliers.id"), nullable=True, index=True)
    stock_posted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list[TransactionEvent]] = relationship(
        back_populates="transaction", order_by="TransactionEvent.created_at", lazy="selectin"
    )


class TransactionEvent(Base):
    __tablename__ = "transaction_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("devices.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transaction: Mapped[Transaction] = relationship(back_populates="events")


class TransactionSequence(Base):
    """Yearly counter for JV-YYYY-NNNNNN generation."""

    __tablename__ = "transaction_sequences"

    year: Mapped[int] = mapped_column(primary_key=True)
    last_value: Mapped[int] = mapped_column(nullable=False, default=0)
