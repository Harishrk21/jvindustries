from datetime import datetime

from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class EquipmentCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=150)
    category: str = "GENERAL"
    location_label: str | None = None
    active: bool = True


class EquipmentOut(BaseModel):
    id: str
    code: str
    name: str
    category: str
    status: str
    location_label: str | None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RepairOutRequest(BaseModel):
    equipment_id: str
    vendor_name: str = Field(..., min_length=2)
    reason: str = Field(..., min_length=3)
    expected_return_date: str | None = None
    gps: GpsPayload
    device_id: str | None = None


class RepairReturnRequest(BaseModel):
    equipment_id: str
    repair_id: str | None = None
    note: str | None = None
    gps: GpsPayload
    device_id: str | None = None


class TransferRequest(BaseModel):
    equipment_id: str
    destination: str = Field(..., min_length=2)
    reason: str = Field(..., min_length=3)
    gps: GpsPayload
    device_id: str | None = None


class DisposalRequest(BaseModel):
    equipment_id: str
    reason: str = Field(..., min_length=3)
    gps: GpsPayload
    device_id: str | None = None


class DisposalDecideRequest(BaseModel):
    disposal_id: str
    approve: bool = True
    approval_note: str = Field(..., min_length=3)
    gps: GpsPayload | None = None
    device_id: str | None = None


class MovementOut(BaseModel):
    id: str
    equipment_id: str
    transaction_id: str
    movement_type: str
    from_status: str | None
    to_status: str
    vendor_name: str | None
    destination: str | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RepairOut(BaseModel):
    id: str
    equipment_id: str
    transaction_id: str
    vendor_name: str
    reason: str
    expected_return_date: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DisposalOut(BaseModel):
    id: str
    equipment_id: str
    transaction_id: str
    reason: str
    status: str
    approval_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EquipmentActionOut(BaseModel):
    equipment: EquipmentOut
    transaction_id: str
    transaction_pk: str
    transaction_status: str
    movement: MovementOut | None = None
    repair: RepairOut | None = None
    disposal: DisposalOut | None = None
