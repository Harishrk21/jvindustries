from datetime import datetime

from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class ProductCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=150)
    hsn: str | None = None
    unit: str = "KG"
    density_default: float | None = None
    loss_limit_percent: float = 0.0
    active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = None
    hsn: str | None = None
    unit: str | None = None
    density_default: float | None = None
    loss_limit_percent: float | None = None
    active: bool | None = None


class ProductOut(BaseModel):
    id: str
    code: str
    name: str
    hsn: str | None
    unit: str
    density_default: float | None
    loss_limit_percent: float
    active: bool

    model_config = {"from_attributes": True}


class StorageUnitCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=150)
    kind: str = Field(..., pattern="^(TANK|BARREL|IBC)$")
    capacity: float | None = None
    capacity_unit: str = "L"
    product_id: str | None = None
    location_label: str | None = None
    active: bool = True


class StorageUnitUpdate(BaseModel):
    name: str | None = None
    capacity: float | None = None
    capacity_unit: str | None = None
    product_id: str | None = None
    location_label: str | None = None
    active: bool | None = None


class StorageUnitOut(BaseModel):
    id: str
    code: str
    name: str
    kind: str
    capacity: float | None
    capacity_unit: str
    product_id: str | None
    location_label: str | None
    active: bool

    model_config = {"from_attributes": True}


class BalanceOut(BaseModel):
    product_id: str
    product_code: str
    product_name: str
    storage_unit_id: str
    storage_code: str
    storage_kind: str
    quantity: float
    unit: str


class AssignStorageRequest(BaseModel):
    transaction_pk: str
    product_id: str
    storage_unit_id: str
    gps: GpsPayload
    device_id: str | None = None


class PostMovementRequest(BaseModel):
    transaction_pk: str
    product_id: str | None = None
    storage_unit_id: str | None = None
    direction: str = Field(..., pattern="^(IN|OUT)$")
    quantity: float | None = Field(None, gt=0)
    unit: str | None = None
    use_transaction_qty: bool = True
    note: str | None = None
    gps: GpsPayload
    device_id: str | None = None
    allow_negative: bool = False


class TransferRequest(BaseModel):
    product_id: str
    from_storage_unit_id: str
    to_storage_unit_id: str
    quantity: float = Field(..., gt=0)
    unit: str = "KG"
    note: str | None = None
    gps: GpsPayload
    device_id: str | None = None
    transaction_pk: str | None = None


class AdjustmentRequest(BaseModel):
    product_id: str
    storage_unit_id: str
    delta_quantity: float  # signed
    unit: str = "KG"
    reason: str = Field(..., min_length=3)
    gps: GpsPayload | None = None
    device_id: str | None = None


class AdjustmentApproveRequest(BaseModel):
    approval_note: str = Field(..., min_length=3)
    approve: bool = True


class MovementOut(BaseModel):
    id: str
    transaction_id: str | None
    product_id: str
    storage_unit_id: str
    direction: str
    quantity: float
    unit: str
    quantity_kg: float | None
    quantity_litres: float | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdjustmentOut(BaseModel):
    id: str
    product_id: str
    storage_unit_id: str
    requested_quantity: float
    unit: str
    reason: str
    status: str
    movement_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TxnStockOut(BaseModel):
    transaction_id: str
    status: str
    product_id: str | None = None
    product_code: str | None = None
    storage_unit_id: str | None = None
    storage_code: str | None = None
    net_kg: float | None = None
    calculated_litres: float | None = None
    stock_posted: bool = False
    movements: list[MovementOut] = []
