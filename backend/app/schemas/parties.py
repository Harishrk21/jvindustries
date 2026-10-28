from datetime import datetime

from pydantic import BaseModel, Field


class PartyCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=200)
    mobile: str | None = Field(default=None, max_length=20)
    whatsapp: str | None = Field(default=None, max_length=20)
    gstin: str | None = Field(default=None, max_length=20)
    address: str | None = None
    active: bool = True


class PartyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    mobile: str | None = Field(default=None, max_length=20)
    whatsapp: str | None = Field(default=None, max_length=20)
    gstin: str | None = Field(default=None, max_length=20)
    address: str | None = None
    active: bool | None = None


class PartyOut(BaseModel):
    id: str
    code: str
    name: str
    mobile: str | None
    whatsapp: str | None = None
    gstin: str | None
    address: str | None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AttachPartiesRequest(BaseModel):
    customer_id: str | None = None
    supplier_id: str | None = None


class ClosureCheckOut(BaseModel):
    transaction_pk: str
    transaction_id: str
    type: str
    status: str
    can_complete: bool
    blockers: list[str]
