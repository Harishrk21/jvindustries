from datetime import datetime

from pydantic import BaseModel, Field


class GpsPayload(BaseModel):
    lat: float
    lon: float
    accuracy_m: float = Field(..., ge=0)


class OtpSendRequest(BaseModel):
    transaction_pk: str
    customer_mobile: str = Field(..., min_length=10, max_length=20)
    customer_name: str | None = None
    gps: GpsPayload
    device_id: str | None = None


class OtpVerifyRequest(BaseModel):
    transaction_pk: str
    otp_id: str
    otp_code: str = Field(..., min_length=4, max_length=8)
    gps: GpsPayload
    device_id: str | None = None


class OtpSendOut(BaseModel):
    otp_id: str
    transaction_id: str
    status: str
    channel: str
    provider: str
    customer_mobile: str
    expires_at: datetime
    whatsapp_delivery_status: str
    # Present when mock/dev so yard can complete flow without Meta API
    otp_preview: str | None = None
    message: str


class OtpStatusOut(BaseModel):
    transaction_id: str
    transaction_status: str
    otp_id: str | None = None
    otp_status: str | None = None
    channel: str | None = None
    customer_mobile: str | None = None
    verified: bool = False
