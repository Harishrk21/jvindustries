"""Compare ANPR / invoice / e-way vehicle numbers."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.vehicle_recognition import normalize_plate


def _canon(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    return normalize_plate(value).replace(" ", "")


@dataclass(frozen=True)
class VehicleMatchResult:
    match_status: str  # MATCH | MISMATCH | PARTIAL
    anpr_vehicle: str | None
    invoice_vehicle: str | None
    eway_vehicle: str | None
    reason: str | None


def compare_vehicles(
    *,
    anpr_vehicle: str | None,
    invoice_vehicle: str | None,
    eway_vehicle: str | None,
) -> VehicleMatchResult:
    a = _canon(anpr_vehicle)
    i = _canon(invoice_vehicle)
    e = _canon(eway_vehicle)
    present = [v for v in (a, i, e) if v]
    if len(present) < 2:
        return VehicleMatchResult(
            match_status="PARTIAL",
            anpr_vehicle=anpr_vehicle,
            invoice_vehicle=invoice_vehicle,
            eway_vehicle=eway_vehicle,
            reason="Need at least two vehicle sources to verify match.",
        )
    unique = set(present)
    if len(unique) == 1:
        return VehicleMatchResult(
            match_status="MATCH",
            anpr_vehicle=anpr_vehicle,
            invoice_vehicle=invoice_vehicle,
            eway_vehicle=eway_vehicle,
            reason=None,
        )
    return VehicleMatchResult(
        match_status="MISMATCH",
        anpr_vehicle=anpr_vehicle,
        invoice_vehicle=invoice_vehicle,
        eway_vehicle=eway_vehicle,
        reason=f"Vehicle mismatch ANPR={anpr_vehicle or '—'} Invoice={invoice_vehicle or '—'} EWB={eway_vehicle or '—'}",
    )
