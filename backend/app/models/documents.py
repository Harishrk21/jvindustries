from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    photo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("photos.id"), nullable=True)

    invoice_number: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    invoice_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hsn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rate: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tax: Mapped[str | None] = mapped_column(String(40), nullable=True)
    total: Mapped[str | None] = mapped_column(String(40), nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EwayBill(Base):
    __tablename__ = "eway_bills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    photo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("photos.id"), nullable=True)

    eway_bill_number: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    eway_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    validity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    consignee_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hsn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    transporter_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    from_place: Mapped[str | None] = mapped_column(String(200), nullable=True)
    to_place: Mapped[str | None] = mapped_column(String(200), nullable=True)

    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentVerification(Base):
    __tablename__ = "document_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_pk: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    anpr_vehicle: Mapped[str | None] = mapped_column(String(32), nullable=True)
    invoice_vehicle: Mapped[str | None] = mapped_column(String(32), nullable=True)
    eway_vehicle: Mapped[str | None] = mapped_column(String(32), nullable=True)
    match_status: Mapped[str] = mapped_column(String(30), nullable=False)  # MATCH | MISMATCH | PARTIAL
    mismatch_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
