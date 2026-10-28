"""WhatsApp Business API abstraction — official when configured, mock otherwise."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger("jvoms.whatsapp")


@dataclass(frozen=True)
class WhatsAppSendResult:
    ok: bool
    provider: str
    provider_message_id: str | None
    delivery_status: str
    error_detail: str | None = None
    mocked: bool = False


def _digits(mobile: str) -> str:
    return "".join(ch for ch in mobile if ch.isdigit())


class WhatsAppClient(ABC):
    @abstractmethod
    def send_text(self, *, to_mobile: str, body: str, template_name: str = "text") -> WhatsAppSendResult:
        raise NotImplementedError

    def send_otp(self, *, to_mobile: str, otp_code: str, transaction_id: str) -> WhatsAppSendResult:
        body = (
            f"JV Industries OMS\n"
            f"Transaction {transaction_id}\n"
            f"Your confirmation OTP is {otp_code}. Valid for 10 minutes."
        )
        return self.send_text(to_mobile=to_mobile, body=body, template_name="customer_otp")


class MockWhatsAppClient(WhatsAppClient):
    """Always works — used when Meta credentials are absent (dev / staging)."""

    provider_name = "mock_whatsapp"

    def send_text(self, *, to_mobile: str, body: str, template_name: str = "text") -> WhatsAppSendResult:
        mid = f"mock-{uuid.uuid4()}"
        logger.info(
            "MOCK WhatsApp to=%s template=%s msg=%s body=%s",
            to_mobile,
            template_name,
            mid,
            body[:120],
        )
        return WhatsAppSendResult(
            ok=True,
            provider=self.provider_name,
            provider_message_id=mid,
            delivery_status="MOCKED",
            mocked=True,
        )


class OfficialWhatsAppClient(WhatsAppClient):
    """Meta Cloud API — requires WHATSAPP_* settings."""

    provider_name = "meta_cloud"

    def send_text(self, *, to_mobile: str, body: str, template_name: str = "text") -> WhatsAppSendResult:
        settings = get_settings()
        phone_id = settings.whatsapp_phone_number_id
        token = settings.whatsapp_token
        base = (settings.whatsapp_api_url or "https://graph.facebook.com/v19.0").rstrip("/")
        if not phone_id or not token:
            return WhatsAppSendResult(
                ok=False,
                provider=self.provider_name,
                provider_message_id=None,
                delivery_status="FAILED",
                error_detail="WhatsApp credentials not configured.",
            )

        to = _digits(to_mobile)
        url = f"{base}/{phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                res = client.post(
                    url,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=payload,
                )
            if res.status_code >= 400:
                return WhatsAppSendResult(
                    ok=False,
                    provider=self.provider_name,
                    provider_message_id=None,
                    delivery_status="FAILED",
                    error_detail=res.text[:500],
                )
            data = res.json()
            mid = None
            try:
                mid = data["messages"][0]["id"]
            except Exception:  # noqa: BLE001
                mid = str(data.get("messages"))
            return WhatsAppSendResult(
                ok=True,
                provider=self.provider_name,
                provider_message_id=mid,
                delivery_status="SENT",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("WhatsApp send failed")
            return WhatsAppSendResult(
                ok=False,
                provider=self.provider_name,
                provider_message_id=None,
                delivery_status="FAILED",
                error_detail=str(exc)[:500],
            )


def get_whatsapp_client() -> WhatsAppClient:
    settings = get_settings()
    if settings.whatsapp_token and settings.whatsapp_phone_number_id:
        return OfficialWhatsAppClient()
    return MockWhatsAppClient()
