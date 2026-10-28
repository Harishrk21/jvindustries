"""Groq vision ANPR — read the number plate from the evidence image itself.

Never invents a plate: if the model cannot see one, recognition fails and the
operator must type it.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from typing import Any

import httpx

from app.ai.vehicle_recognition import (
    VehicleRecognitionResult,
    extract_plate_candidates,
    normalize_plate,
)
from app.core.config import get_settings

logger = logging.getLogger("jvoms.groq_plate")

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_PROMPT = """Read ONLY the vehicle number plate in this photo (Indian gate ANPR).
Ignore bumper slogans, art, watermarks, brand text.
Two-line plates → one string (e.g. RJ09G / 4017 → "RJ 09 G 4017"; TAV / 3657 → "TAV 3657").
Do not invent characters. If unreadable, plate=null.
JSON only: {"plate":"RJ 09 G 4017"|null,"raw_lines":["RJ09G","4017"],"confidence":0.0,"notes":""}
"""


def _downscale_jpeg(image_bytes: bytes, max_side: int = 1024, quality: int = 72) -> tuple[bytes, str]:
    """Shrink image for faster Groq vision; fall back to original if Pillow missing."""
    try:
        from io import BytesIO

        from PIL import Image  # type: ignore

        im = Image.open(BytesIO(image_bytes))
        im = im.convert("RGB")
        w, h = im.size
        scale = min(1.0, max_side / max(w, h))
        if scale < 0.98:
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return image_bytes, _mime_for(image_bytes)


def _mime_for(image_bytes: bytes) -> str:
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _parse_json_content(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {}


def _format_plate(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", str(raw).upper()).strip()
    if not cleaned:
        return None
    # Prefer normalize when it is a standard Indian plate
    norm = normalize_plate(cleaned)
    compact = re.sub(r"\s+", "", norm)
    if re.match(r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$", compact):
        return norm
    # Non-standard but readable (e.g. TAV 3657) — keep spaced alnum tokens
    return cleaned


def recognize_plate_with_groq(
    image_bytes: bytes,
    *,
    ocr_text: str | None = None,
) -> VehicleRecognitionResult | None:
    """Call Groq vision. Returns None if API key missing or request fails hard."""
    settings = get_settings()
    api_key = (settings.groq_api_key or settings.ai_api_key or "").strip()
    if not api_key:
        return None

    vision_bytes, mime = _downscale_jpeg(image_bytes)
    b64 = base64.b64encode(vision_bytes).decode("ascii")
    model = settings.groq_vision_model or "qwen/qwen3.8-27b"

    payload = {
        "model": model,
        "temperature": 0,
        "max_completion_tokens": 160,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = None
            for attempt in range(3):
                resp = client.post(
                    _GROQ_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if resp.status_code != 429:
                    break
                wait = 2.0 * (attempt + 1)
                m = re.search(r"try again in ([0-9.]+)s", resp.text or "", re.I)
                if m:
                    wait = min(45.0, float(m.group(1)) + 0.5)
                logger.warning("Groq rate-limited; sleeping %.1fs", wait)
                time.sleep(wait)
            if resp is None or resp.status_code >= 400:
                logger.warning(
                    "Groq vision HTTP %s: %s",
                    getattr(resp, "status_code", "?"),
                    (resp.text if resp is not None else "")[:400],
                )
                return None
            body = resp.json()
            content = (
                ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Groq vision failed: %s", exc)
        return None

    data = _parse_json_content(content)
    plate = _format_plate(data.get("plate") if isinstance(data.get("plate"), str) else None)
    raw_lines = data.get("raw_lines") if isinstance(data.get("raw_lines"), list) else []
    try:
        conf = float(data.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    notes = str(data.get("notes") or "")

    vision_raw = "\n".join(str(x) for x in raw_lines if x) or content
    if ocr_text:
        vision_raw = f"{vision_raw}\n---on_device_ocr---\n{ocr_text}"

    if not plate:
        return VehicleRecognitionResult(
            field="vehicle_number",
            value=None,
            confidence=0.0,
            provider="groq_vision",
            failed=True,
            message="Groq vision found no readable plate. Retake or type the number.",
            raw_ocr_text=vision_raw,
            candidates=(),
        )

    # If device OCR also supports this plate, nudge confidence up slightly
    ocr_hits = extract_plate_candidates(ocr_text or "") if ocr_text else []
    compact = plate.replace(" ", "")
    if any(p.replace(" ", "") == compact for p, _ in ocr_hits):
        conf = max(conf, 0.9)

    if conf < 0.35:
        conf = 0.55  # readable plate returned — allow confirm UI

    return VehicleRecognitionResult(
        field="vehicle_number",
        value=plate,
        confidence=conf if conf >= 0.55 else 0.7,
        provider="groq_vision",
        failed=False,
        message=notes or "Plate read from photo via Groq vision. Confirm or retake.",
        raw_ocr_text=vision_raw,
        candidates=(plate,),
    )
