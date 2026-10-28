"""WeighbridgeOCRService — parse weight values from real OCR of TRUWEIGH display.

Never invents a weight. If OCR text has no numeric weight, recognition fails.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class WeighbridgeOcrResult:
    field: str
    value_kg: float | None
    confidence: float
    provider: str
    failed: bool
    message: str
    raw_ocr_text: str | None = None
    candidates_kg: tuple[float, ...] = ()


# Prefer numbers near kg / KG / KGS markers; also plain large integers
_WEIGHT_MARKED = re.compile(
    r"(?<![A-Z0-9])(\d{1,3}(?:[,\s]\d{3})+|\d{4,6})(?:\.\d+)?\s*(?:KG|KGS|kg|kgs)?\b"
)
_WEIGHT_PLAIN = re.compile(r"(?<![A-Z0-9.])(\d{4,6})(?:\.\d+)?(?![A-Z0-9])")


def _to_float(raw: str) -> float | None:
    cleaned = raw.replace(",", "").replace(" ", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if value < 100 or value > 200_000:
        return None
    return value


def extract_weight_candidates(ocr_text: str) -> list[tuple[float, float]]:
    if not ocr_text or not ocr_text.strip():
        return []
    found: list[tuple[float, float]] = []
    seen: set[float] = set()
    for pattern, base_conf in ((_WEIGHT_MARKED, 0.9), (_WEIGHT_PLAIN, 0.7)):
        for m in pattern.finditer(ocr_text):
            val = _to_float(m.group(1))
            if val is None or val in seen:
                continue
            seen.add(val)
            found.append((val, base_conf))
    # Prefer larger plausible weighbridge readings first when multiple
    found.sort(key=lambda x: (-x[1], -x[0]))
    return found


class WeighbridgeOCRService(ABC):
    @abstractmethod
    def recognize_from_ocr(self, *, ocr_text: str) -> WeighbridgeOcrResult:
        raise NotImplementedError


class OcrTextWeighbridgeService(WeighbridgeOCRService):
    provider_name = "ocr_text_parser"

    def recognize_from_ocr(self, *, ocr_text: str) -> WeighbridgeOcrResult:
        candidates = extract_weight_candidates(ocr_text)
        if not candidates:
            return WeighbridgeOcrResult(
                field="weight_kg",
                value_kg=None,
                confidence=0.0,
                provider=self.provider_name,
                failed=True,
                message="No weight detected on display OCR. Retake the TRUWEIGH photograph.",
                raw_ocr_text=ocr_text,
            )
        best, conf = candidates[0]
        return WeighbridgeOcrResult(
            field="weight_kg",
            value_kg=best,
            confidence=conf,
            provider=self.provider_name,
            failed=False,
            message="Weight candidate extracted from OCR. Operator must confirm.",
            raw_ocr_text=ocr_text,
            candidates_kg=tuple(v for v, _ in candidates),
        )


def get_weighbridge_ocr_service() -> WeighbridgeOCRService:
    return OcrTextWeighbridgeService()
