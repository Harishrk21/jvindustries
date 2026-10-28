"""Server-authoritative stock balances from movements only."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import Product, StockMovement, StorageUnit

_IN_DIRS = {"IN", "TRANSFER_IN", "OPENING", "ADJUST_IN"}
_OUT_DIRS = {"OUT", "TRANSFER_OUT", "ADJUST_OUT"}


def signed_qty(direction: str, quantity: float) -> float:
    q = abs(float(quantity))
    if direction in _IN_DIRS or direction == "ADJUST" and quantity >= 0:
        return q
    if direction in _OUT_DIRS:
        return -q
    if direction == "ADJUST":
        return float(quantity)  # already signed
    raise ValueError(f"Unknown stock direction: {direction}")


@dataclass(frozen=True)
class BalanceRow:
    product_id: str
    product_code: str
    product_name: str
    storage_unit_id: str
    storage_code: str
    storage_kind: str
    quantity: float
    unit: str


def compute_balance(
    db: Session,
    *,
    product_id: str | None = None,
    storage_unit_id: str | None = None,
) -> list[BalanceRow]:
    q = select(StockMovement)
    if product_id:
        q = q.where(StockMovement.product_id == product_id)
    if storage_unit_id:
        q = q.where(StockMovement.storage_unit_id == storage_unit_id)
    rows = db.execute(q).scalars().all()

    buckets: dict[tuple[str, str], dict] = {}
    for m in rows:
        key = (m.product_id, m.storage_unit_id)
        b = buckets.setdefault(key, {"qty": 0.0, "unit": m.unit})
        if m.direction == "ADJUST":
            b["qty"] += float(m.quantity)  # signed
        else:
            b["qty"] += signed_qty(m.direction, m.quantity)
        b["unit"] = m.unit

    out: list[BalanceRow] = []
    for (pid, sid), data in buckets.items():
        product = db.get(Product, pid)
        unit = db.get(StorageUnit, sid)
        if product is None or unit is None:
            continue
        out.append(
            BalanceRow(
                product_id=pid,
                product_code=product.code,
                product_name=product.name,
                storage_unit_id=sid,
                storage_code=unit.code,
                storage_kind=unit.kind,
                quantity=round(data["qty"], 3),
                unit=data["unit"] or product.unit,
            )
        )
    out.sort(key=lambda r: (r.storage_code, r.product_code))
    return out


def balance_for(db: Session, *, product_id: str, storage_unit_id: str) -> float:
    rows = compute_balance(db, product_id=product_id, storage_unit_id=storage_unit_id)
    return rows[0].quantity if rows else 0.0
