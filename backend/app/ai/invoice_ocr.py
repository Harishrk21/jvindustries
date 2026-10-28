"""InvoiceOCRService — extract fields from real OCR text. Never invents values."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.ai.vehicle_recognition import extract_plate_candidates, normalize_plate


@dataclass
class InvoiceOcrResult:
    fields: dict[str, str | None]
    confidence: float
    provider: str
    failed: bool
    message: str
    raw_ocr_text: str | None = None
    vehicle_candidates: list[str] = field(default_factory=list)


_INV_NO = re.compile(
    r"(?:invoice\s*(?:no|number|#)|inv\.?\s*no\.?|bill\s*no\.?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,})",
    re.I,
)
_GSTIN = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9])\b", re.I)
_DATE = re.compile(
    r"(?:date|dt)\s*[:#-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    re.I,
)
_HSN = re.compile(r"(?:hsn|sac)\s*[:#-]?\s*(\d{4,8})", re.I)
_TOTAL = re.compile(
    r"(?:grand\s*total|invoice\s*total|total\s*amount|net\s*payable|total)\s*[:#-]?\s*(?:rs\.?|inr)?\s*([0-9]+(?:,[0-9]{3})*(?:\.\d{1,2})?)",
    re.I,
)
_QTY = re.compile(r"(?:qty|quantity)\s*[:#-]?\s*([0-9]+(?:\.\d+)?)\s*(kg|l|ltr|mt|nos|pcs)?", re.I)


class InvoiceOCRService(ABC):
    @abstractmethod
    def recognize_from_ocr(self, *, ocr_text: str) -> InvoiceOcrResult:
        raise NotImplementedError


class OcrTextInvoiceService(InvoiceOCRService):
    provider_name = "ocr_text_parser"

    def recognize_from_ocr(self, *, ocr_text: str) -> InvoiceOcrResult:
        text = ocr_text or ""
        if not text.strip():
            return InvoiceOcrResult(
                fields={},
                confidence=0.0,
                provider=self.provider_name,
                failed=True,
                message="Empty OCR text. Retake invoice photograph.",
                raw_ocr_text=text,
            )

        plates = extract_plate_candidates(text)
        vehicle = plates[0][0] if plates else None

        inv = _INV_NO.search(text)
        gst = _GSTIN.search(text)
        dt = _DATE.search(text)
        hsn = _HSN.search(text)
        total = _TOTAL.search(text)
        qty = _QTY.search(text)

        fields = {
            "invoice_number": inv.group(1).upper() if inv else None,
            "invoice_date": dt.group(1) if dt else None,
            "gstin": gst.group(1).upper() if gst else None,
            "hsn": hsn.group(1) if hsn else None,
            "total": total.group(1).replace(",", "") if total else None,
            "quantity": qty.group(1) if qty else None,
            "unit": (qty.group(2) or "").upper() if qty and qty.group(2) else None,
            "vehicle_number": normalize_plate(vehicle) if vehicle else None,
            "supplier_name": None,
            "customer_name": None,
            "product_name": None,
            "rate": None,
            "tax": None,
        }

        hits = sum(1 for v in fields.values() if v)
        if hits == 0:
            return InvoiceOcrResult(
                fields=fields,
                confidence=0.0,
                provider=self.provider_name,
                failed=True,
                message="Could not detect invoice fields. Retake or enter manually.",
                raw_ocr_text=text,
                vehicle_candidates=[p for p, _ in plates],
            )

        conf = min(0.95, 0.45 + 0.08 * hits)
        return InvoiceOcrResult(
            fields=fields,
            confidence=conf,
            provider=self.provider_name,
            failed=False,
            message="Invoice candidates extracted from OCR. Operator must confirm.",
            raw_ocr_text=text,
            vehicle_candidates=[p for p, _ in plates],
        )


def get_invoice_ocr_service() -> InvoiceOCRService:
    return OcrTextInvoiceService()
