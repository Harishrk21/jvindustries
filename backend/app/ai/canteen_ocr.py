"""Canteen invoice OCR — extract known items (Rice/Dal/Oil etc). Never invents lines."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_INV_NO = re.compile(
    r"(?:invoice\s*(?:no|number|#)|inv\.?\s*no\.?|bill\s*no\.?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,})",
    re.I,
)
_TOTAL = re.compile(
    r"(?:grand\s*total|invoice\s*total|total\s*amount|net\s*payable|total)\s*[:#-]?\s*(?:rs\.?|inr)?\s*([0-9]+(?:,[0-9]{3})*(?:\.\d{1,2})?)",
    re.I,
)
_SUPPLIER = re.compile(r"(?:supplier|vendor|from)\s*[:#-]?\s*([A-Za-z0-9 &.\-]{3,80})", re.I)

# Known canteen item patterns: name then qty + optional unit
_ITEM_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("RICE", "Rice", re.compile(r"\brice\b[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*(kg|kgs|g)?", re.I)),
    ("DAL", "Dal", re.compile(r"\b(?:dal|dhal|toor|moong|urad)\b[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*(kg|kgs|g)?", re.I)),
    ("OIL", "Oil", re.compile(r"\b(?:oil|sunflower|groundnut)\b[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*(l|ltr|litre|liters|kg)?", re.I)),
    ("SUGAR", "Sugar", re.compile(r"\bsugar\b[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*(kg|kgs)?", re.I)),
    ("WHEAT", "Wheat", re.compile(r"\b(?:wheat|atta)\b[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*(kg|kgs)?", re.I)),
]


@dataclass
class CanteenLineDetect:
    item_code: str
    item_name: str
    quantity: float
    unit: str


@dataclass
class CanteenOcrResult:
    invoice_number: str | None
    supplier_name: str | None
    invoice_total: str | None
    lines: list[CanteenLineDetect] = field(default_factory=list)
    confidence: float = 0.0
    provider: str = "canteen_ocr_parser"
    failed: bool = False
    message: str = ""
    raw_ocr_text: str | None = None


def parse_canteen_ocr(ocr_text: str) -> CanteenOcrResult:
    text = ocr_text or ""
    if not text.strip():
        return CanteenOcrResult(
            invoice_number=None,
            supplier_name=None,
            invoice_total=None,
            failed=True,
            message="Empty OCR text. Retake canteen invoice photograph.",
            raw_ocr_text=text,
        )

    inv = _INV_NO.search(text)
    total = _TOTAL.search(text)
    supplier = _SUPPLIER.search(text)

    lines: list[CanteenLineDetect] = []
    for code, name, pat in _ITEM_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        qty = float(m.group(1))
        unit_raw = (m.group(2) or "").lower()
        if code == "OIL":
            unit = "L" if unit_raw.startswith("l") else ("KG" if unit_raw.startswith("k") else "L")
        else:
            unit = "KG"
        lines.append(CanteenLineDetect(item_code=code, item_name=name, quantity=qty, unit=unit))

    hits = (1 if inv else 0) + (1 if total else 0) + len(lines)
    if hits == 0:
        return CanteenOcrResult(
            invoice_number=None,
            supplier_name=None,
            invoice_total=None,
            failed=True,
            message="No canteen items or invoice fields found in OCR. Confirm manually or retake.",
            raw_ocr_text=text,
            confidence=0.0,
        )

    conf = min(0.95, 0.35 + 0.15 * hits)
    return CanteenOcrResult(
        invoice_number=inv.group(1).upper() if inv else None,
        supplier_name=supplier.group(1).strip()[:200] if supplier else None,
        invoice_total=total.group(1).replace(",", "") if total else None,
        lines=lines,
        confidence=conf,
        failed=False,
        message=f"Detected {len(lines)} canteen line(s)." if lines else "Invoice fields found; no known item lines.",
        raw_ocr_text=text,
    )
