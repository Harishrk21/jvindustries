"""Phase F — advances ledger + customer settlements."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AdvanceEntry(Base):
    """Customer advance paid / received-back ledger (append-oriented)."""

    __tablename__ = "advance_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # PAID | RECEIVED_BACK
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Settlement(Base):
    """Period settlement snapshot for a customer (feeds Supply & Expense PDF)."""

    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    report_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    period_from: Mapped[date] = mapped_column(Date, nullable=False)
    period_to: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")  # DRAFT | FINALIZED

    feedstock_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    delivery_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    feedstock_consignments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_trips: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    bleaching_return_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    burner_fuel_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    burner_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    retail_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    retail_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    processing_rate_per_kg: Mapped[float] = mapped_column(Float, nullable=False, default=8.4)
    gst_percent: Mapped[float] = mapped_column(Float, nullable=False, default=18.0)

    advance_paid: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    advance_received_back: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    processing_base: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    gst_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    deductions_total: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    net_processing: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    payable: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GstReconcileItem(Base):
    """Snapshot row from GST reconcile run (invoice vs party master)."""

    __tablename__ = "gst_reconcile_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    invoice_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    invoice_gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    party_gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    invoice_total: Mapped[str | None] = mapped_column(String(40), nullable=True)
    match_status: Mapped[str] = mapped_column(String(30), nullable=False)  # MATCH | GSTIN_MISMATCH | MISSING_GSTIN | UNPARSED_TOTAL
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
