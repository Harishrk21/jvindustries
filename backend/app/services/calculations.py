"""Server-authoritative calculations — never trust client math for commit."""

from __future__ import annotations


class CalculationError(ValueError):
    pass


def compute_net_kg(*, tare_kg: float, gross_kg: float) -> float:
    if tare_kg < 0 or gross_kg < 0:
        raise CalculationError("Weights must be positive.")
    if gross_kg < tare_kg:
        raise CalculationError("Gross weight must be greater than or equal to tare weight.")
    return round(gross_kg - tare_kg, 3)


def compute_calculated_litres(*, net_kg: float, density_kg_per_l: float) -> float:
    if net_kg < 0:
        raise CalculationError("Net weight must be non-negative.")
    if density_kg_per_l <= 0:
        raise CalculationError("Density must be positive.")
    # Label as CALCULATED QUANTITY — not a separately measured volume
    return round(net_kg / density_kg_per_l, 2)


def compute_production_loss(*, qty_in: float, qty_out: float) -> tuple[float, float]:
    """Return (loss_qty, loss_percent). Server-authoritative."""
    if qty_in <= 0:
        raise CalculationError("Input quantity must be positive.")
    if qty_out < 0:
        raise CalculationError("Output quantity must be non-negative.")
    if qty_out > qty_in:
        raise CalculationError("Output cannot exceed input.")
    loss_qty = round(qty_in - qty_out, 3)
    loss_percent = round((loss_qty / qty_in) * 100.0, 4)
    return loss_qty, loss_percent


def loss_requires_approval(*, loss_percent: float, loss_limit_percent: float) -> bool:
    return float(loss_percent) > float(loss_limit_percent) + 1e-9
