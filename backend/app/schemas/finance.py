from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class AdvanceCreate(BaseModel):
    customer_id: str
    entry_date: date
    direction: str = Field(..., pattern="^(PAID|RECEIVED_BACK)$")
    amount: float = Field(..., gt=0)
    reference: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class AdvanceOut(BaseModel):
    id: str
    customer_id: str
    entry_date: date
    direction: str
    amount: float
    reference: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdvanceBalanceOut(BaseModel):
    customer_id: str
    customer_code: str
    customer_name: str
    paid_total: float
    received_back_total: float
    balance: float


class SettlementCreate(BaseModel):
    customer_id: str
    period_from: date
    period_to: date
    report_no: str | None = None
    auto_fill_yard: bool = True
    feedstock_kg: float | None = None
    delivery_kg: float | None = None
    feedstock_consignments: int | None = None
    delivery_trips: int | None = None
    bleaching_return_kg: float = 0
    burner_fuel_kg: float = 0
    burner_rate: float = 0
    retail_kg: float = 0
    retail_rate: float = 0
    processing_rate_per_kg: float = 8.4
    gst_percent: float = 18.0
    notes: str | None = None


class SettlementOut(BaseModel):
    id: str
    customer_id: str
    report_no: str
    period_from: date
    period_to: date
    status: str
    feedstock_kg: float
    delivery_kg: float
    feedstock_consignments: int
    delivery_trips: int
    bleaching_return_kg: float
    burner_fuel_kg: float
    burner_rate: float
    retail_kg: float
    retail_rate: float
    processing_rate_per_kg: float
    gst_percent: float
    advance_paid: float
    advance_received_back: float
    processing_base: float
    gst_amount: float
    deductions_total: float
    net_processing: float
    payable: float
    notes: str | None
    finalized: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GstReconcileRow(BaseModel):
    invoice_id: str | None
    transaction_id: str | None
    invoice_number: str | None
    invoice_gstin: str | None
    party_gstin: str | None
    invoice_total: str | None
    match_status: str
    detail: str | None


class GstReconcileOut(BaseModel):
    run_id: str
    period_from: str
    period_to: str
    total: int
    matched: int
    mismatches: int
    rows: list[GstReconcileRow]
