from datetime import datetime

from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)
    timestamp: datetime | None = None


class TransactionCreateRequest(BaseModel):
    client_transaction_id: str | None = Field(default=None, max_length=36)
    type: str
    device_id: str | None = None
    gps: GpsPayload | None = None
    notes: str | None = None
    require_geofence: bool = False


class TransactionEventOut(BaseModel):
    id: str
    from_status: str | None
    to_status: str
    actor_user_id: str
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionOut(BaseModel):
    id: str
    transaction_id: str
    client_transaction_id: str | None
    type: str
    status: str
    sync_status: str
    geofence_ok: bool | None
    created_by: str
    created_at: datetime
    events: list[TransactionEventOut] = []

    model_config = {"from_attributes": True}


class TransactionListItem(BaseModel):
    id: str
    transaction_id: str
    type: str
    status: str
    vehicle_number: str | None = None
    driver_name: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TransactionSearchResponse(BaseModel):
    items: list[TransactionListItem]
    total: int
    page: int
    page_size: int


class TimelineResponse(BaseModel):
    transaction_pk: str
    transaction_id: str
    type: str
    status: str
    vehicle_number: str | None = None
    events: list[TransactionEventOut]


class InboxItem(BaseModel):
    kind: str
    id: str
    transaction_pk: str | None = None
    transaction_id: str | None = None
    title: str
    detail: str | None = None
    status: str
    created_at: datetime | None = None
    action_hint: str | None = None


class InboxResponse(BaseModel):
    items: list[InboxItem]
    total: int


class DashboardSummary(BaseModel):
    vehicles_in: int = 0
    vehicles_out: int = 0
    material_received: int = 0
    material_loaded: int = 0
    weighments: int = 0
    pending_approvals: int = 0
    customer_otp_pending: int = 0
    exceptions: int = 0
    production_loss_alerts: int = 0
    equipment_out: int = 0
    canteen_purchases: int = 0


class GeofenceCheckRequest(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class GeofenceCheckResponse(BaseModel):
    authorized: bool
    message: str
    distance_m: float
    accuracy_m: float
