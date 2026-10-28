"""Phase E — commercial statement request bodies."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SupplyExpenseRequest(BaseModel):
    customer_id: str | None = None
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_address: str | None = None
    report_no: str = "SE-001"
    report_date: str | None = None
    period_from: str  # YYYY-MM-DD
    period_to: str
    prepared_as_on: str | None = None

    feedstock_kg: float = Field(..., ge=0)
    feedstock_consignments: int = Field(default=1, ge=0)
    delivery_kg: float = Field(..., ge=0)
    delivery_trips: int = Field(default=1, ge=0)

    bleaching_return_kg: float = Field(default=0, ge=0)
    burner_fuel_kg: float = Field(default=0, ge=0)
    burner_rate: float = Field(default=0, ge=0)
    retail_kg: float = Field(default=0, ge=0)
    retail_rate: float = Field(default=0, ge=0)

    processing_rate_per_kg: float = Field(default=8.4, ge=0)
    gst_percent: float = Field(default=18.0, ge=0)
    advance_paid: float = Field(default=0, ge=0)
    advance_received_back: float = Field(default=0, ge=0)

    schedule_receipts: list[dict] = []  # {date, consignments, qty_kg}
    schedule_deliveries: list[dict] = []


class DistillationRequest(BaseModel):
    report_no: str = "DR-001"
    report_date: str | None = None
    period_from: str
    period_to: str
    customer_name: str = "Job-work customer"
    process_capacity_kg: float = 60000

    total_feed_kg: float = Field(..., ge=0)
    bleaching_return_kg: float = 0
    boiler_fuel_kg: float = 0
    first_cut_kg: float = 0
    second_cut_kg: float = 0
    bottom_cut_kg: float = 0
    vapor_loss_kg: float = 0
    water_loss_kg: float = 0

    processing_rate_per_kg: float = 8.4
    fuel_cost: float = 0
    power_cost: float = 0
    labour_cost: float = 0
    other_cost: float = 0
    process_days: float = 1


class CostingLine(BaseModel):
    description: str
    unit: str = "kg"
    quantity: float = 0
    rate: float = 0
    remarks: str | None = None


class CostingRequest(BaseModel):
    title: str = "COSTING SHEET FOR PURCHASES AND SALES"
    as_on: str | None = None
    batch_size_kg: float = 60000
    purchase_lines: list[CostingLine] = []
    opex_lines: list[CostingLine] = []
    option_a_name: str = "Kerosene route"
    option_a_yield_pct: float = 85
    option_a_sell_rate: float = 55
    option_b_name: str = "Waste oil route"
    option_b_yield_pct: float = 90
    option_b_sell_rate: float = 48


class MomParticipant(BaseModel):
    name: str
    designation: str | None = None
    organization: str | None = None


class MomAction(BaseModel):
    action: str
    owner: str | None = None
    target_date: str | None = None
    status: str = "Open"


class MomRequest(BaseModel):
    meeting_date: str
    meeting_time: str | None = "10:00"
    venue: str = "Conference Room / Plant Site"
    objective: str = "Operations & commercial review"
    participants: list[MomParticipant] = []
    discussion_points: list[str] = []
    recommendations: list[MomAction] = []
    action_points: list[MomAction] = []
