from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class OfflineDraftIn(BaseModel):
    client_transaction_id: str = Field(..., min_length=8, max_length=36)
    type: str
    notes: str | None = None
    device_id: str | None = None
    gps: GpsPayload | None = None
    queued_at: str | None = None  # ISO from client; informational


class SyncPushRequest(BaseModel):
    drafts: list[OfflineDraftIn] = Field(..., min_length=1, max_length=50)


class SyncItemResult(BaseModel):
    client_transaction_id: str
    outcome: str  # CREATED | IDEMPOTENT | CONFLICT | ERROR
    message: str
    transaction_pk: str | None = None
    transaction_id: str | None = None
    status: str | None = None
    sync_status: str | None = None


class SyncPushResponse(BaseModel):
    accepted: int
    conflicts: int
    errors: int
    results: list[SyncItemResult]


class SyncPolicyOut(BaseModel):
    policy: str
    rules: list[str]
