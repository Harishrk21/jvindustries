"""VehicleRecognitionService — extracts Indian plates from real OCR text.

Never invents a plate number. If OCR text has no plate candidate, recognition fails
and the operator must enter manually with an audited reason.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleRecognitionResult:
    field: str
    value: str | None
    confidence: float
    provider: str
    failed: bool
    message: str
    raw_ocr_text: str | None = None
    candidates: tuple[str, ...] = ()


# Standard: TN 09 AB 1234 / TN09AB1234 / TN-09-AB-1234
_PLATE_FIND = re.compile(
    r"(?<![A-Z0-9])([A-Z]{2})\s*[-\s]?\s*(\d{1,2})\s*[-\s]?\s*([A-Z]{1,3})\s*[-\s]?\s*(\d{1,4})(?![A-Z0-9])",
    re.IGNORECASE,
)

# Two-line yellow plate OCR often returns: "AP28\nW4882" or "AP 28\nW 4882"
_LINE_STATE = re.compile(r"^([A-Z]{2})\s*(\d{1,2})$")
_LINE_SERIES = re.compile(r"^([A-Z]{1,3})\s*(\d{1,4})$")
# RJ 09 G / 4017 — series letter sits on the first line
_LINE_STATE_SERIES = re.compile(r"^([A-Z]{2})\s*(\d{1,2})\s*([A-Z]{1,3})$")
_LINE_NUM_ONLY = re.compile(r"^(\d{1,4})$")

# Compact glued: AP28W4882
_COMPACT = re.compile(r"(?<![A-Z0-9])([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{1,4})(?![A-Z0-9])", re.IGNORECASE)

# Letter↔digit confusions common in plate OCR (Tesseract on yellow plates)
_TO_DIGIT = {
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "8",  # stylized 8 often read as S
    "B": "8",
    "G": "6",
    "T": "8",  # 8 misread as T on yellow plates
    "A": "4",  # closed-top 4 → A (wa8s2 → W4882); invalid states filter fantasies
}
_TO_LETTER = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "5": "S",
    "8": "B",
    "6": "G",
}

# Reject OCR fantasies like NO94B1234 from prose
_VALID_STATES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
    "MZ", "NL", "OD", "OR", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK",
    "UP", "UT", "WB",
}


def _ocr_confusions(text: str) -> str:
    """Light OCR cleanup — only in mixed plate-like tokens, not free prose rewrite."""

    def fix_token(tok: str) -> str:
        if len(tok) < 4 or not re.search(r"[A-Za-z]", tok) or not re.search(r"\d", tok):
            return tok
        out = []
        for i, ch in enumerate(tok):
            up = ch.upper()
            if up == "O" and (i >= 2 or (i > 0 and tok[i - 1].isdigit())):
                out.append("0")
            elif up in {"I", "L"} and i >= 2 and any(c.isdigit() for c in tok):
                out.append("1" if sum(c.isdigit() for c in tok) >= 2 else up)
            else:
                out.append(up)
        return "".join(out)

    parts = re.split(r"(\s+)", text.upper())
    return "".join(fix_token(p) if p.strip() else p for p in parts)


def normalize_plate(value: str) -> str:
    cleaned_src = _ocr_confusions(value.replace(".", " "))
    m = _PLATE_FIND.search(cleaned_src)
    if not m:
        cleaned = re.sub(r"[^A-Z0-9]", "", cleaned_src.upper())
        m2 = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{1,4})$", cleaned)
        if not m2:
            return re.sub(r"\s+", " ", value.strip().upper())
        return f"{m2.group(1)} {m2.group(2)} {m2.group(3)} {m2.group(4)}"
    return f"{m.group(1).upper()} {m.group(2)} {m.group(3).upper()} {m.group(4)}"


def _add(found: list[tuple[str, float]], seen: set[str], plate: str, conf: float) -> None:
    plate = normalize_plate(plate)
    key = plate.replace(" ", "")
    if len(key) < 7 or key in seen:
        return
    if sum(c.isdigit() for c in key) < 3:
        return
    # Must look like ST + RTO + series + number after normalize
    if not re.match(r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$", key):
        return
    state = key[:2]
    if state not in _VALID_STATES:
        return
    seen.add(key)
    found.append((plate, conf))


def _parse_structured(compact: str) -> list[tuple[str, str, str, str, float]]:
    """Walk alnum string; parse Indian plate with letter/digit OCR confusions."""
    s = re.sub(r"[^A-Z0-9]", "", compact.upper())
    hits: list[tuple[str, str, str, str, float]] = []
    n = len(s)
    if n < 7:
        return hits

    def as_letters(ch: str) -> list[str]:
        up = ch.upper()
        opts = {up}
        if up in _TO_LETTER:
            opts.add(_TO_LETTER[up])
        if up.isalpha():
            opts.add(up)
        return [c for c in opts if c.isalpha()]

    def as_digits(ch: str) -> list[str]:
        up = ch.upper()
        opts = {up}
        if up in _TO_DIGIT:
            opts.add(_TO_DIGIT[up])
        if up.isdigit():
            opts.add(up)
        return [c for c in opts if c.isdigit()]

    for i in range(n - 6):
        # state: 2 letters
        st_opts = []
        a_opts = as_letters(s[i])
        b_opts = as_letters(s[i + 1])
        for a in a_opts:
            for b in b_opts:
                st_opts.append(a + b)
        if not st_opts:
            continue

        for st in st_opts:
            if st not in _VALID_STATES:
                continue
            # RTO: 1 or 2 digits
            for rto_len in (2, 1):
                j = i + 2
                if j + rto_len >= n:
                    continue
                rto_chars: list[str] = []
                ok = True
                conf_pen = 0.0
                for k in range(rto_len):
                    digs = as_digits(s[j + k])
                    if not digs:
                        ok = False
                        break
                    # Prefer literal digit if present
                    pick = next((d for d in digs if s[j + k].isdigit() and d == s[j + k]), digs[0])
                    if pick != s[j + k].upper() and not s[j + k].isdigit():
                        conf_pen += 0.03
                    rto_chars.append(pick)
                if not ok:
                    continue
                rto = "".join(rto_chars)
                p = j + rto_len
                # series: 1–3 letters
                for ser_len in (1, 2, 3):
                    if p + ser_len >= n:
                        continue
                    ser_chars: list[str] = []
                    ok_s = True
                    for k in range(ser_len):
                        lets = as_letters(s[p + k])
                        if not lets:
                            ok_s = False
                            break
                        pick = next((L for L in lets if s[p + k].isalpha() and L == s[p + k].upper()), lets[0])
                        if not s[p + k].isalpha():
                            conf_pen += 0.03
                        ser_chars.append(pick)
                    if not ok_s:
                        continue
                    series = "".join(ser_chars)
                    q = p + ser_len
                    # number: 1–4 digits (prefer 3–4)
                    for num_len in (4, 3, 2, 1):
                        if q + num_len > n:
                            continue
                        # Prefer end-of-token: next char not alnum or end
                        end = q + num_len
                        if end < n and s[end].isalnum() and num_len < 4:
                            # allow continue to longer
                            pass
                        num_chars: list[str] = []
                        ok_n = True
                        for k in range(num_len):
                            digs = as_digits(s[q + k])
                            if not digs:
                                ok_n = False
                                break
                            pick = next(
                                (d for d in digs if s[q + k].isdigit() and d == s[q + k]),
                                digs[0],
                            )
                            if not s[q + k].isdigit():
                                conf_pen += 0.04
                            num_chars.append(pick)
                        if not ok_n:
                            continue
                        number = "".join(num_chars)
                        # Prefer maximal digit run (don't emit AP28W488 when AP28W4882 fits)
                        if end < n and s[end].isdigit() and num_len < 4:
                            continue
                        if end < n and s[end].isalpha() and num_len < 4:
                            continue
                        base = 0.8
                        if rto_len == 2 and num_len >= 3:
                            base = 0.9
                        if num_len >= 4:
                            base = min(0.95, base + 0.02)
                        if conf_pen == 0:
                            base = min(0.95, base + 0.04)
                        # Too many letter↔digit guesses → reject (stops AR28IW0080 fantasies)
                        if conf_pen > 0.12:
                            continue
                        # Multi-letter series with leading OCR-noise I/L rarely real
                        if len(series) >= 2 and series[0] in {"I", "L"}:
                            conf_pen += 0.08
                        hits.append((st, rto, series, number, max(0.55, base - conf_pen)))
    return hits


def extract_plate_candidates(ocr_text: str) -> list[tuple[str, float]]:
    if not ocr_text or not ocr_text.strip():
        return []

    raw = _ocr_confusions(ocr_text)
    collapsed = re.sub(r"[\s\-]+", "", raw)
    spaced = re.sub(r"[\n\r]+", " ", raw)

    found: list[tuple[str, float]] = []
    seen: set[str] = set()

    for m in _PLATE_FIND.finditer(spaced):
        plate = f"{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)}"
        conf = 0.88
        if len(m.group(2)) == 2 and len(m.group(4)) >= 3:
            conf = 0.96
        _add(found, seen, plate, conf)

    for m in _COMPACT.finditer(collapsed):
        plate = f"{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)}"
        _add(found, seen, plate, 0.94)

    # Two-line plates: adjacent lines state+RTO then series+number
    lines = [re.sub(r"[^A-Z0-9 ]", "", ln).strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln]
    for i in range(len(lines) - 1):
        a = _LINE_STATE.match(lines[i].replace(" ", ""))
        if not a:
            a = _LINE_STATE.match(lines[i])
        b_compact = lines[i + 1].replace(" ", "")
        b = _LINE_SERIES.match(b_compact)
        if a and b:
            plate = f"{a.group(1)} {a.group(2)} {b.group(1)} {b.group(2)}"
            _add(found, seen, plate, 0.92)
        a2 = _LINE_STATE.match(lines[i])
        b2 = _LINE_SERIES.match(lines[i + 1])
        if a2 and b2:
            plate = f"{a2.group(1)} {a2.group(2)} {b2.group(1)} {b2.group(2)}"
            _add(found, seen, plate, 0.91)

        # RJ 09 G \n 4017
        a3 = _LINE_STATE_SERIES.match(lines[i].replace(" ", "")) or _LINE_STATE_SERIES.match(lines[i])
        b3 = _LINE_NUM_ONLY.match(b_compact) or _LINE_NUM_ONLY.match(lines[i + 1])
        if a3 and b3:
            plate = f"{a3.group(1)} {a3.group(2)} {a3.group(3)} {b3.group(1)}"
            _add(found, seen, plate, 0.93)

        # Compact first line RJ09G4017 already on one line of OCR
        glued = (lines[i] + lines[i + 1]).replace(" ", "")
        for m in _COMPACT.finditer(glued):
            plate = f"{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)}"
            _add(found, seen, plate, 0.9)

    for m in re.finditer(r"[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}", collapsed):
        _add(found, seen, m.group(0), 0.84)

    # Always run short-window fuzzy — exact hits may be wrong (AR28IW… from Ar2s)
    # while a literal AP28 + W4882 pair still needs to be discovered.
    windows: set[str] = set()
    clean_lines = [re.sub(r"[^A-Z0-9]", "", ln) for ln in lines if re.sub(r"[^A-Z0-9]", "", ln)]
    for i, ln in enumerate(clean_lines):
        windows.add(ln)
        for j in range(i + 1, min(i + 3, len(clean_lines))):
            glued = "".join(clean_lines[k] for k in range(i, j + 1))
            if 6 <= len(glued) <= 16:
                windows.add(glued)

    stateish = [
        ln
        for ln in clean_lines
        if re.match(r"^[A-Z]{2}\d{0,2}[A-Z0-9]{0,3}$", ln) and 3 <= len(ln) <= 7
    ]
    # Also capture literal state+RTO tokens embedded in lines (E AP28 I w4882)
    for ln in clean_lines:
        for m in re.finditer(r"[A-Z]{2}\d{1,2}", ln):
            stateish.append(m.group(0))
    seriesish: list[str] = []
    for ln in clean_lines:
        if re.match(r"^[A-Z]{1,3}\d[A-Z0-9]{1,5}$", ln) or re.match(r"^[A-Z]\d{3,4}$", ln):
            seriesish.append(ln)
        for m in re.finditer(r"[A-Z]{1,3}\d[A-Z0-9]{1,5}", ln):
            seriesish.append(m.group(0))
        for m in re.finditer(r"[A-Z]\d{3,4}", ln):
            seriesish.append(m.group(0))
    seriesish = sorted(set(seriesish), key=len)
    for a in sorted(set(stateish), key=len):
        for b in seriesish:
            glued = a + b
            if 7 <= len(glued) <= 14:
                windows.add(glued)

    for tok in re.findall(r"[A-Z0-9]{5,12}", " ".join(clean_lines)):
        windows.add(tok)

    enriched: set[str] = set()
    for soft in windows:
        if not soft:
            continue
        enriched.add(soft)
        enriched.add(soft.replace("S", "8").replace("T", "8").replace("Z", "2").replace("O", "0").replace("B", "8"))
    for var in enriched:
        for st, rto, series, number, conf in _parse_structured(var):
            # Cap multi-letter series — usually OCR glue (IW), not real series
            if len(series) > 1:
                conf = min(conf, 0.8)
            _add(found, seen, f"{st} {rto} {series} {number}", min(conf, 0.89))

    # Prefer single-letter series that is glued to the number (W48S2).
    # Drop multi-letter series that start with I/L when a single-letter alternative exists.
    # Boost when the number appears as its own OCR line (two-line plates: 4017 under RJ09G).
    num_lines = {re.sub(r"[^0-9]", "", ln) for ln in lines}
    by_core: dict[str, list[tuple[str, float, str]]] = {}
    for plate, conf in found:
        parts = plate.split()
        if len(parts) != 4:
            continue
        st, rto, series, number = parts
        core = f"{st}{rto}{number}"
        for m in re.finditer(rf"(?<![A-Z0-9]){re.escape(series)}([A-Z0-9]{{2,5}})(?![A-Z0-9])", collapsed):
            body_digits = "".join(
                _TO_DIGIT[c] if c in _TO_DIGIT else c for c in m.group(1) if c.isdigit() or c in _TO_DIGIT
            )
            if body_digits == number or number.startswith(body_digits) or body_digits.startswith(number):
                conf = min(0.97, conf + 0.12)
                break
        if len(series) == 1 and re.search(rf"(?<![A-Z0-9]){series}\d", collapsed):
            conf = min(0.97, conf + 0.05)
        if number in num_lines:
            conf = min(0.98, conf + 0.1)
        # Literal state+RTO in OCR (AP28) beats confusable scraps (Ar2s→AR28)
        if re.search(rf"(?<![A-Z0-9]){st}{rto}(?![A-Z0-9])", collapsed):
            conf = min(0.98, conf + 0.12)
        compact = f"{st}{rto}{series}{number}"
        votes = collapsed.count(compact) + raw.count(number)
        conf = min(0.98, conf + min(0.08, votes * 0.02))
        by_core.setdefault(core, []).append((plate, conf, series))

    boosted: list[tuple[str, float]] = []
    for group in by_core.values():
        series_set = {s for _, _, s in group}
        clean_singles = {s for s in series_set if len(s) == 1 and s not in {"I", "L", "O"}}
        for plate, conf, series in group:
            # Drop glued noise series like IW when a real single-letter W exists
            if len(series) >= 2 and series[0] in {"I", "L"} and clean_singles:
                continue
            if series in {"I", "L", "O"} and (clean_singles or any(len(s) >= 2 for s in series_set)):
                continue
            boosted.append((plate, conf))
    if not boosted:
        boosted = found

    # Longer plate body wins ties (AB1234 over B1234 / W4882 over W488)
    boosted.sort(key=lambda x: (-x[1], -len(x[0].replace(" ", "")), x[0]))
    return boosted


class VehicleRecognitionService(ABC):
    @abstractmethod
    def recognize_from_ocr(
        self,
        *,
        ocr_text: str,
        preferred_candidate: str | None = None,
    ) -> VehicleRecognitionResult:
        raise NotImplementedError


class OcrTextVehicleRecognitionService(VehicleRecognitionService):
    """Production path: parse plates from on-device (or cloud) OCR text only."""

    provider_name = "ocr_text_parser"

    def recognize_from_ocr(
        self,
        *,
        ocr_text: str,
        preferred_candidate: str | None = None,
    ) -> VehicleRecognitionResult:
        candidates = extract_plate_candidates(ocr_text)
        # Never invent a plate from preferred_candidate — only boost if OCR already supports it
        if preferred_candidate:
            pref = normalize_plate(preferred_candidate)
            pref_key = pref.replace(" ", "")
            ocr_flat = re.sub(r"\s+", "", (ocr_text or "").upper())
            if pref_key and pref_key in ocr_flat:
                if pref not in {c for c, _ in candidates}:
                    candidates.insert(0, (pref, 0.82))
                else:
                    candidates = [(pref, max(conf, 0.85)) if c == pref else (c, conf) for c, conf in candidates]
                    candidates.sort(key=lambda x: (-x[1], -len(x[0].replace(" ", ""))))

        # Cap confidence unless the compact plate is evidenced in OCR (stops 97% hallucinations)
        evidenced: list[tuple[str, float]] = []
        flat = re.sub(r"[^A-Z0-9]", "", (ocr_text or "").upper())
        flat_soft = (
            flat.replace("S", "8")
            .replace("T", "8")
            .replace("Z", "2")
            .replace("O", "0")
            .replace("B", "8")
            .replace("A", "4")
        )
        for plate, conf in candidates:
            key = plate.replace(" ", "")
            supported = bool(key) and (key in flat or key in flat_soft)
            if supported:
                evidenced.append((plate, conf))
            elif conf >= 0.85:
                evidenced.append((plate, min(conf, 0.68)))
            else:
                evidenced.append((plate, conf))
        candidates = evidenced
        candidates.sort(key=lambda x: (-x[1], -len(x[0].replace(" ", ""))))

        if not candidates:
            return VehicleRecognitionResult(
                field="vehicle_number",
                value=None,
                confidence=0.0,
                provider=self.provider_name,
                failed=True,
                message="No vehicle number detected in OCR text. Retake photo or enter manually with reason.",
                raw_ocr_text=ocr_text,
                candidates=(),
            )

        best_plate, best_conf = candidates[0]
        return VehicleRecognitionResult(
            field="vehicle_number",
            value=best_plate,
            confidence=best_conf,
            provider=self.provider_name,
            failed=False,
            message="Vehicle number candidate extracted from OCR. Confirm or retake.",
            raw_ocr_text=ocr_text,
            candidates=tuple(p for p, _ in candidates),
        )


def get_vehicle_recognition_service() -> VehicleRecognitionService:
    return OcrTextVehicleRecognitionService()
