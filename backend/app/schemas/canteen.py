from datetime import datetime

from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class CanteenItemOut(BaseModel):
    id: str
    code: str
    name: str
    unit: str
    active: bool

    model_config = {"from_attributes": True}


class CanteenBalanceOut(BaseModel):
    item_id: str
    item_code: str
    item_name: str
    quantity: float
    unit: str


class LineIn(BaseModel):
    item_code: str | None = None
    item_id: str | None = None
    item_name: str
    quantity: float = Field(..., gt=0)
    unit: str = "KG"


class CanteenDetectOut(BaseModel):
    purchase_id: str
    transaction_id: str
    transaction_pk: str
    photo_id: str | None
    invoice_number: str | None
    supplier_name: str | None
    invoice_total: str | None
    lines: list[dict]
    confidence: float
    provider: str
    failed: bool
    message: str
    ocr_raw_preview: str | None = None


class CanteenConfirmRequest(BaseModel):
    purchase_id: str
    transaction_pk: str
    gps: GpsPayload
    invoice_number: str | None = None
    supplier_name: str | None = None
    invoice_total: str | None = None
    lines: list[LineIn]
    device_id: str | None = None


class CanteenPurchaseOut(BaseModel):
    id: str
    transaction_id: str
    transaction_pk: str
    status: str
    invoice_number: str | None
    supplier_name: str | None
    invoice_total: str | None
    photo_id: str | None
    lines: list[dict]
    stock_posted: bool = False
    created_at: datetime
