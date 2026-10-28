from datetime import datetime

from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class VehicleEntryStartRequest(BaseModel):
    client_transaction_id: str | None = None
    type: str = "MATERIAL_LOADING_OUTWARD"
    device_id: str | None = None
    gps: GpsPayload
    notes: str | None = None


class AnprConfirmRequest(BaseModel):
    transaction_pk: str
    anpr_result_id: str
    confirm: bool = True
    vehicle_number: str | None = None
    manual_reason: str | None = None
    device_id: str | None = None
    gps: GpsPayload | None = None


class DriverDetailsRequest(BaseModel):
    transaction_pk: str
    driver_name: str = Field(..., min_length=1, max_length=150)
    driver_mobile: str = Field(..., min_length=8, max_length=20)
    transporter_name: str | None = Field(default=None, max_length=150)
    license_no: str | None = Field(default=None, max_length=50)
    vehicle_type: str | None = Field(default=None, max_length=40)
    customer_whatsapp: str | None = Field(default=None, max_length=20)
    device_id: str | None = None


class GatePassCreateRequest(BaseModel):
    transaction_pk: str
    pass_type: str = "OUTWARD_LOADING"
    direction: str = "INWARD"
    purpose: str | None = Field(default=None, max_length=40)
    material_description: str | None = Field(default=None, max_length=200)
    quantity_text: str | None = Field(default=None, max_length=80)
    unit_text: str | None = Field(default=None, max_length=40)
    invoice_challan_no: str | None = Field(default=None, max_length=80)
    from_location: str | None = Field(default=None, max_length=200)
    to_location: str | None = Field(default=None, max_length=200)
    remarks: str | None = None
    vehicle_checked: bool = False
    goods_verified: bool = False
    documents_verified: bool = False
    device_id: str | None = None


class VehicleExitJsonRequest(BaseModel):
    """Exit when photo already uploaded via /vehicles/exit/detect."""

    transaction_pk: str
    anpr_result_id: str | None = None
    device_id: str | None = None
    gps: GpsPayload
    complete_transaction: bool = False


class AnprResultOut(BaseModel):
    id: str
    transaction_id: str
    vehicle_number: str | None
    confidence: float | None
    provider: str
    status: str
    message: str | None = None
    candidates: list[str] = []
    photo_id: str | None = None
    ocr_raw_preview: str | None = None

    model_config = {"from_attributes": True}


class GatePassOut(BaseModel):
    id: str
    gate_pass_number: str
    transaction_id: str
    pass_type: str
    vehicle_number: str | None
    vehicle_type: str | None = None
    driver_name: str | None
    driver_mobile: str | None = None
    transporter_name: str | None = None
    direction: str
    purpose: str | None = None
    material_description: str | None = None
    quantity_text: str | None = None
    unit_text: str | None = None
    invoice_challan_no: str | None = None
    from_location: str | None = None
    to_location: str | None = None
    remarks: str | None = None
    vehicle_checked: bool = False
    goods_verified: bool = False
    documents_verified: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class VehicleTxnOut(BaseModel):
    id: str
    transaction_id: str
    type: str
    status: str
    vehicle_number: str | None
    vehicle_type: str | None = None
    driver_name: str | None
    driver_mobile: str | None
    transporter_name: str | None
    customer_whatsapp: str | None = None
    purpose: str | None = None
    from_location: str | None = None
    to_location: str | None = None
    remarks: str | None = None
    geofence_ok: bool | None
    tare_kg: float | None = None
    gross_kg: float | None = None
    net_kg: float | None = None
    density_kg_per_l: float | None = None
    temperature_c: float | None = None
    calculated_litres: float | None = None
    entry_photo_id: str | None = None
    exit_photo_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
