"""EWayBillOCRService — extract fields from real OCR / QR text. Never invents values."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.ai.vehicle_recognition import extract_plate_candidates, normalize_plate


@dataclass
class EwayOcrResult:
    fields: dict[str, str | None]
    confidence: float
    provider: str
    failed: bool
    message: str
    raw_ocr_text: str | None = None
    vehicle_candidates: list[str] = field(default_factory=list)


_EWB = re.compile(
    r"(?:e[\-\s]?way\s*bill\s*(?:no|number|#)?|ewb\s*no\.?)\s*[:#-]?\s*(\d{10,14})",
    re.I,
)
_EWB_BARE = re.compile(r"\b(\d{12})\b")
_GSTIN = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9])\b", re.I)
_VALID = re.compile(r"(?:valid(?:ity)?(?:\s*upto)?|valid\s*till)\s*[:#-]?\s*([^\n]{6,40})", re.I)
_FROM = re.compile(
    r"(?:from|dispatch\s*from)\s*[:#-]?\s*([A-Za-z0-9 ,.\-]{3,80}?)(?=\s+(?:to|ship\s*to|destination)\b|$)",
    re.I,
)
_TO = re.compile(r"(?:to|ship\s*to|destination)\s*[:#-]?\s*([A-Za-z0-9 ,.\-]{3,80})", re.I)
_TRANS = re.compile(r"(?:transporter|transport)\s*[:#-]?\s*([A-Za-z0-9 &.\-]{3,80})", re.I)
_HSN = re.compile(r"(?:hsn|sac)\s*[:#-]?\s*(\d{4,8})", re.I)
_QTY = re.compile(r"(?:qty|quantity)\s*[:#-]?\s*([0-9]+(?:\.\d+)?)", re.I)


class EWayBillOCRService(ABC):
    @abstractmethod
    def recognize_from_ocr(self, *, ocr_text: str) -> EwayOcrResult:
        raise NotImplementedError


class OcrTextEwayService(EWayBillOCRService):
    provider_name = "ocr_text_parser"

    def recognize_from_ocr(self, *, ocr_text: str) -> EwayOcrResult:
        text = ocr_text or ""
        if not text.strip():
            return EwayOcrResult(
                fields={},
                confidence=0.0,
                provider=self.provider_name,
                failed=True,
                message="Empty OCR text. Retake E-Way Bill photograph.",
                raw_ocr_text=text,
            )

        plates = extract_plate_candidates(text)
        vehicle = plates[0][0] if plates else None

        ewb = _EWB.search(text) or _EWB_BARE.search(text)
        gst = _GSTIN.search(text)
        valid = _VALID.search(text)
        frm = _FROM.search(text)
        to = _TO.search(text)
        trans = _TRANS.search(text)
        hsn = _HSN.search(text)
        qty = _QTY.search(text)

        fields = {
            "eway_bill_number": ewb.group(1) if ewb else None,
            "eway_date": None,
            "validity": valid.group(1).strip() if valid else None,
            "gstin": gst.group(1).upper() if gst else None,
            "vehicle_number": normalize_plate(vehicle) if vehicle else None,
            "from_place": frm.group(1).strip()[:200] if frm else None,
            "to_place": to.group(1).strip()[:200] if to else None,
            "transporter_name": trans.group(1).strip()[:200] if trans else None,
            "hsn": hsn.group(1) if hsn else None,
            "quantity": qty.group(1) if qty else None,
            "supplier_name": None,
            "consignee_name": None,
            "product_name": None,
        }

        hits = sum(1 for v in fields.values() if v)
        if hits == 0:
            return EwayOcrResult(
                fields=fields,
                confidence=0.0,
                provider=self.provider_name,
                failed=True,
                message="Could not detect E-Way Bill fields. Retake or enter manually.",
                raw_ocr_text=text,
                vehicle_candidates=[p for p, _ in plates],
            )

        conf = min(0.95, 0.45 + 0.08 * hits)
        return EwayOcrResult(
            fields=fields,
            confidence=conf,
            provider=self.provider_name,
            failed=False,
            message="E-Way Bill candidates extracted from OCR. Operator must confirm.",
            raw_ocr_text=text,
            vehicle_candidates=[p for p, _ in plates],
        )


def get_eway_ocr_service() -> EWayBillOCRService:
    return OcrTextEwayService()
