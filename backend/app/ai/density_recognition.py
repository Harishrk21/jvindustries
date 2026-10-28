"""DensityRecognitionService — parse density + temperature from hydrometer OCR text."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DensityRecognitionResult:
    density_kg_per_l: float | None
    temperature_c: float | None
    confidence: float
    provider: str
    failed: bool
    message: str
    raw_ocr_text: str | None = None


_DENSITY = re.compile(
    r"(?:density|dens|sg|sp\.?\s*gr)?\s*[:=]?\s*(0\.\d{2,4}|\d\.\d{2,4})\s*(?:kg\s*/?\s*l|g\s*/?\s*ml|g/cc)?",
    re.IGNORECASE,
)
_TEMP = re.compile(
    r"(?:temp|temperature|t)?\s*[:=]?\s*(-?\d{1,2}(?:\.\d+)?)\s*(?:°\s*c|deg(?:ree)?s?\s*c|c\b)",
    re.IGNORECASE,
)
_BARE_DENSITY = re.compile(r"\b(0\.\d{3,4})\b")
_BARE_TEMP = re.compile(r"\b([2-4]\d(?:\.\d)?)\b")


class DensityRecognitionService(ABC):
    @abstractmethod
    def recognize_from_ocr(self, *, ocr_text: str) -> DensityRecognitionResult:
        raise NotImplementedError


class OcrTextDensityService(DensityRecognitionService):
    provider_name = "ocr_text_parser"

    def recognize_from_ocr(self, *, ocr_text: str) -> DensityRecognitionResult:
        if not ocr_text or not ocr_text.strip():
            return DensityRecognitionResult(
                density_kg_per_l=None,
                temperature_c=None,
                confidence=0.0,
                provider=self.provider_name,
                failed=True,
                message="Empty OCR text. Retake hydrometer photograph.",
                raw_ocr_text=ocr_text,
            )

        density = None
        temp = None
        conf = 0.0

        dm = _DENSITY.search(ocr_text)
        if dm:
            density = float(dm.group(1))
            conf = 0.85
        else:
            bm = _BARE_DENSITY.search(ocr_text)
            if bm:
                density = float(bm.group(1))
                conf = 0.65

        tm = _TEMP.search(ocr_text)
        if tm:
            temp = float(tm.group(1))
            conf = max(conf, 0.8)
        else:
            # only accept bare temp if density already found (avoid random numbers)
            if density is not None:
                bt = _BARE_TEMP.search(ocr_text)
                if bt:
                    temp = float(bt.group(1))
                    conf = max(conf, 0.6)

        if density is None or density <= 0 or density >= 2.0:
            return DensityRecognitionResult(
                density_kg_per_l=None,
                temperature_c=temp,
                confidence=0.0,
                provider=self.provider_name,
                failed=True,
                message="Density not detected clearly. Retake or request supervisor confirmation.",
                raw_ocr_text=ocr_text,
            )

        return DensityRecognitionResult(
            density_kg_per_l=density,
            temperature_c=temp,
            confidence=conf,
            provider=self.provider_name,
            failed=False,
            message="Density candidate extracted from OCR. Operator must confirm.",
            raw_ocr_text=ocr_text,
        )


def get_density_recognition_service() -> DensityRecognitionService:
    return OcrTextDensityService()
