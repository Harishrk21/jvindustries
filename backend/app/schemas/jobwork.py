from datetime import datetime

from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class JobWorkCreate(BaseModel):
    transaction_pk: str | None = None
    product_id: str | None = None
    batch_code: str = Field(..., min_length=1, max_length=40)
    customer_name: str | None = None
    customer_mobile: str | None = None
    unit: str = "KG"
    notes: str | None = None
    gps: GpsPayload
    device_id: str | None = None


class JobWorkQuantities(BaseModel):
    batch_id: str
    qty_in: float = Field(..., gt=0)
    qty_out: float = Field(..., ge=0)
    gps: GpsPayload
    device_id: str | None = None


class LossApproveRequest(BaseModel):
    loss_id: str
    approval_note: str = Field(..., min_length=3)
    gps: GpsPayload | None = None
    device_id: str | None = None


class ProductionLossOut(BaseModel):
    id: str
    batch_id: str
    transaction_id: str
    qty_in: float
    qty_out: float
    loss_qty: float
    loss_percent: float
    loss_limit_percent: float
    excess_percent: float
    requires_approval: bool
    approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class JobWorkOut(BaseModel):
    id: str
    transaction_id: str
    transaction_pk: str
    batch_code: str
    product_id: str | None
    customer_name: str | None
    customer_mobile: str | None
    qty_in: float | None
    qty_out: float | None
    unit: str
    status: str
    loss: ProductionLossOut | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
