from datetime import datetime

from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class InvoiceDetectOut(BaseModel):
    id: str
    transaction_id: str
    photo_id: str | None
    fields: dict[str, str | None]
    confidence: float
    provider: str
    failed: bool
    message: str
    vehicle_candidates: list[str] = []
    ocr_raw_preview: str | None = None


class InvoiceConfirmRequest(BaseModel):
    transaction_pk: str
    invoice_id: str
    gps: GpsPayload
    invoice_number: str | None = None
    invoice_date: str | None = None
    supplier_name: str | None = None
    customer_name: str | None = None
    gstin: str | None = None
    product_name: str | None = None
    hsn: str | None = None
    quantity: str | None = None
    unit: str | None = None
    rate: str | None = None
    tax: str | None = None
    total: str | None = None
    vehicle_number: str | None = None
    device_id: str | None = None


class EwayDetectOut(BaseModel):
    id: str
    transaction_id: str
    photo_id: str | None
    fields: dict[str, str | None]
    confidence: float
    provider: str
    failed: bool
    message: str
    vehicle_candidates: list[str] = []
    ocr_raw_preview: str | None = None


class EwayConfirmRequest(BaseModel):
    transaction_pk: str
    eway_id: str
    gps: GpsPayload
    eway_bill_number: str | None = None
    eway_date: str | None = None
    validity: str | None = None
    supplier_name: str | None = None
    consignee_name: str | None = None
    gstin: str | None = None
    vehicle_number: str | None = None
    product_name: str | None = None
    hsn: str | None = None
    quantity: str | None = None
    transporter_name: str | None = None
    from_place: str | None = None
    to_place: str | None = None
    device_id: str | None = None


class DocumentStatusOut(BaseModel):
    transaction_id: str
    status: str
    invoice_confirmed: bool
    eway_confirmed: bool
    anpr_vehicle: str | None = None
    invoice_vehicle: str | None = None
    eway_vehicle: str | None = None
    match_status: str | None = None
    mismatch_reason: str | None = None
    verification_id: str | None = None


class MismatchApproveRequest(BaseModel):
    transaction_pk: str
    verification_id: str
    approval_note: str = Field(..., min_length=3)
    gps: GpsPayload | None = None
    device_id: str | None = None


class InvoiceOut(BaseModel):
    id: str
    transaction_id: str
    invoice_number: str | None
    vehicle_number: str | None
    confirmed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
