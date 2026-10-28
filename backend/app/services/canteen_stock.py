"""Canteen stock balances from movements only."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.canteen import CanteenItem, CanteenStockMovement

_IN = {"IN", "OPENING", "ADJUST_IN"}
_OUT = {"OUT", "ADJUST_OUT"}


def signed(direction: str, quantity: float) -> float:
    q = abs(float(quantity))
    if direction in _IN:
        return q
    if direction in _OUT:
        return -q
    if direction == "ADJUST":
        return float(quantity)
    raise ValueError(f"Unknown canteen stock direction: {direction}")


@dataclass(frozen=True)
class CanteenBalance:
    item_id: str
    item_code: str
    item_name: str
    quantity: float
    unit: str


def compute_balances(db: Session, *, item_id: str | None = None) -> list[CanteenBalance]:
    q = select(CanteenStockMovement)
    if item_id:
        q = q.where(CanteenStockMovement.item_id == item_id)
    rows = db.execute(q).scalars().all()
    buckets: dict[str, dict] = {}
    for m in rows:
        b = buckets.setdefault(m.item_id, {"qty": 0.0, "unit": m.unit})
        b["qty"] += signed(m.direction, m.quantity)
        b["unit"] = m.unit

    out: list[CanteenBalance] = []
    for iid, data in buckets.items():
        item = db.get(CanteenItem, iid)
        if item is None:
            continue
        out.append(
            CanteenBalance(
                item_id=iid,
                item_code=item.code,
                item_name=item.name,
                quantity=round(data["qty"], 3),
                unit=data["unit"] or item.unit,
            )
        )
    out.sort(key=lambda r: r.item_code)
    return out
