from datetime import datetime

from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class WeighmentDetectOut(BaseModel):
    transaction_id: str
    kind: str
    detected_weight_kg: float | None
    confidence: float
    provider: str
    failed: bool
    message: str
    candidates_kg: list[float] = []
    photo_id: str | None = None
    hardware_weight_kg: float | None = None
    ocr_raw_preview: str | None = None


class WeighmentConfirmRequest(BaseModel):
    transaction_pk: str
    kind: str  # TARE | GROSS
    photo_id: str
    confirmed_weight_kg: float = Field(..., gt=0)
    ocr_weight_kg: float | None = None
    ocr_confidence: float | None = None
    ocr_provider: str | None = None
    ocr_raw_text: str | None = None
    device_id: str | None = None
    gps: GpsPayload
    after_tare_mode: str | None = Field(
        default=None,
        description="LOADING or UNLOADING after tare (material flows)",
    )


class WeighmentOut(BaseModel):
    id: str
    transaction_id: str
    kind: str
    weight_kg: float
    ocr_weight_kg: float | None
    ocr_confidence: float | None
    photo_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NetWeightOut(BaseModel):
    transaction_id: str
    tare_kg: float
    gross_kg: float
    net_kg: float
    status: str


class DensityDetectOut(BaseModel):
    transaction_id: str
    detected_density: float | None
    detected_temperature_c: float | None
    confidence: float
    provider: str
    failed: bool
    message: str
    photo_id: str | None = None
    ocr_raw_preview: str | None = None


class DensityConfirmRequest(BaseModel):
    transaction_pk: str
    photo_id: str
    confirmed_density: float = Field(..., gt=0, lt=2)
    confirmed_temperature_c: float | None = None
    ocr_density: float | None = None
    ocr_temperature: float | None = None
    ocr_confidence: float | None = None
    ocr_provider: str | None = None
    ocr_raw_text: str | None = None
    device_id: str | None = None
    gps: GpsPayload
    require_supervisor_if_low_confidence: bool = True


class DensityOut(BaseModel):
    id: str
    transaction_id: str
    density_kg_per_l: float
    temperature_c: float | None
    calculated_litres: float | None
    net_kg_snapshot: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WeighmentSummaryOut(BaseModel):
    transaction_id: str
    status: str
    tare_kg: float | None
    gross_kg: float | None
    net_kg: float | None
    density_kg_per_l: float | None
    temperature_c: float | None
    calculated_litres: float | None
    calculated_quantity_label: str = "CALCULATED QUANTITY"
