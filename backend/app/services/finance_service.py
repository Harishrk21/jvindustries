"""Phase F — advances, settlement calc, GST invoice reconcile."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.documents import Invoice
from app.models.finance import AdvanceEntry, Settlement
from app.models.parties import Customer
from app.models.transaction import Transaction
from app.schemas.finance import SettlementCreate

_NUM = re.compile(r"[\d,.]+")


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def period_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    start, _ = _day_bounds(date_from)
    _, end = _day_bounds(date_to)
    return start, end


def advance_totals(db: Session, customer_id: str) -> tuple[float, float, float]:
    rows = list(
        db.execute(select(AdvanceEntry).where(AdvanceEntry.customer_id == customer_id)).scalars().all()
    )
    paid = sum(float(r.amount) for r in rows if r.direction == "PAID")
    back = sum(float(r.amount) for r in rows if r.direction == "RECEIVED_BACK")
    return round(paid, 2), round(back, 2), round(paid - back, 2)


def yard_delivery_stats(
    db: Session, *, customer_id: str, period_from: date, period_to: date
) -> tuple[float, int]:
    start, end = period_bounds(period_from, period_to)
    txns = list(
        db.execute(
            select(Transaction).where(
                and_(
                    Transaction.customer_id == customer_id,
                    Transaction.created_at >= start,
                    Transaction.created_at < end,
                )
            )
        )
        .scalars()
        .all()
    )
    kg = sum(float(t.net_kg) for t in txns if t.net_kg is not None)
    return round(kg, 3), len(txns)


def compute_settlement_amounts(
    *,
    feedstock_kg: float,
    bleaching_return_kg: float,
    burner_fuel_kg: float,
    burner_rate: float,
    retail_kg: float,
    retail_rate: float,
    processing_rate_per_kg: float,
    gst_percent: float,
    advance_paid: float,
    advance_received_back: float,
) -> dict[str, float]:
    net_feed = max(feedstock_kg - bleaching_return_kg, 0.0)
    deductions = burner_fuel_kg * burner_rate + retail_kg * retail_rate
    base = net_feed * processing_rate_per_kg
    gst = base * gst_percent / 100.0
    invoice_total = base + gst
    net_processing = invoice_total - deductions
    advance_bal = advance_paid - advance_received_back
    payable = net_processing + advance_bal
    return {
        "processing_base": round(base, 2),
        "gst_amount": round(gst, 2),
        "deductions_total": round(deductions, 2),
        "net_processing": round(net_processing, 2),
        "payable": round(payable, 2),
    }


def next_settlement_report_no(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"SE-{year}-"
    existing = list(
        db.execute(select(Settlement.report_no).where(Settlement.report_no.like(f"{prefix}%"))).scalars().all()
    )
    nums = []
    for code in existing:
        try:
            nums.append(int(str(code).split("-")[-1]))
        except ValueError:
            pass
    n = (max(nums) + 1) if nums else 1
    return f"{prefix}{n:04d}"


def create_settlement(db: Session, body: SettlementCreate, user_id: str) -> Settlement:
    cust = db.get(Customer, body.customer_id)
    if cust is None:
        raise ValueError("Customer not found.")

    delivery_kg = body.delivery_kg
    delivery_trips = body.delivery_trips
    feedstock_kg = body.feedstock_kg
    feedstock_consignments = body.feedstock_consignments

    if body.auto_fill_yard:
        auto_kg, auto_trips = yard_delivery_stats(
            db, customer_id=body.customer_id, period_from=body.period_from, period_to=body.period_to
        )
        if delivery_kg is None:
            delivery_kg = auto_kg
        if delivery_trips is None:
            delivery_trips = auto_trips
        # Feedstock default: deliveries + bleaching + burner if not provided
        if feedstock_kg is None:
            feedstock_kg = (delivery_kg or 0) + body.bleaching_return_kg + body.burner_fuel_kg + body.retail_kg
        if feedstock_consignments is None:
            feedstock_consignments = delivery_trips or 0

    delivery_kg = float(delivery_kg or 0)
    feedstock_kg = float(feedstock_kg or 0)
    delivery_trips = int(delivery_trips or 0)
    feedstock_consignments = int(feedstock_consignments or 0)

    paid, back, _bal = advance_totals(db, body.customer_id)
    amounts = compute_settlement_amounts(
        feedstock_kg=feedstock_kg,
        bleaching_return_kg=body.bleaching_return_kg,
        burner_fuel_kg=body.burner_fuel_kg,
        burner_rate=body.burner_rate,
        retail_kg=body.retail_kg,
        retail_rate=body.retail_rate,
        processing_rate_per_kg=body.processing_rate_per_kg,
        gst_percent=body.gst_percent,
        advance_paid=paid,
        advance_received_back=back,
    )

    report_no = (body.report_no or "").strip() or next_settlement_report_no(db)
    row = Settlement(
        customer_id=body.customer_id,
        report_no=report_no,
        period_from=body.period_from,
        period_to=body.period_to,
        status="DRAFT",
        feedstock_kg=feedstock_kg,
        delivery_kg=delivery_kg,
        feedstock_consignments=feedstock_consignments,
        delivery_trips=delivery_trips,
        bleaching_return_kg=body.bleaching_return_kg,
        burner_fuel_kg=body.burner_fuel_kg,
        burner_rate=body.burner_rate,
        retail_kg=body.retail_kg,
        retail_rate=body.retail_rate,
        processing_rate_per_kg=body.processing_rate_per_kg,
        gst_percent=body.gst_percent,
        advance_paid=paid,
        advance_received_back=back,
        processing_base=amounts["processing_base"],
        gst_amount=amounts["gst_amount"],
        deductions_total=amounts["deductions_total"],
        net_processing=amounts["net_processing"],
        payable=amounts["payable"],
        notes=body.notes,
        created_by=user_id,
    )
    db.add(row)
    db.flush()
    return row


def parse_money(raw: str | None) -> float | None:
    if not raw:
        return None
    m = _NUM.search(raw.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def reconcile_gst(
    db: Session, *, period_from: date, period_to: date
) -> tuple[str, list[dict]]:
    start, end = period_bounds(period_from, period_to)
    invoices = list(
        db.execute(
            select(Invoice).where(
                and_(Invoice.created_at >= start, Invoice.created_at < end, Invoice.confirmed.is_(True))
            )
        )
        .scalars()
        .all()
    )
    run_id = str(uuid.uuid4())
    rows: list[dict] = []
    for inv in invoices:
        txn = db.get(Transaction, inv.transaction_pk)
        party_gstin = None
        if txn and txn.customer_id:
            c = db.get(Customer, txn.customer_id)
            party_gstin = c.gstin if c else None
        elif txn and txn.supplier_id:
            from app.models.parties import Supplier

            s = db.get(Supplier, txn.supplier_id)
            party_gstin = s.gstin if s else None

        inv_gstin = (inv.gstin or "").strip().upper() or None
        party_gstin = (party_gstin or "").strip().upper() or None
        total = inv.total
        parsed = parse_money(total)

        if not inv_gstin:
            status = "MISSING_GSTIN"
            detail = "Invoice confirmed without GSTIN"
        elif party_gstin and inv_gstin != party_gstin:
            status = "GSTIN_MISMATCH"
            detail = f"Invoice {inv_gstin} vs party {party_gstin}"
        elif parsed is None and total:
            status = "UNPARSED_TOTAL"
            detail = f"Could not parse total '{total}'"
        else:
            status = "MATCH"
            detail = "GSTIN aligned with party master" if party_gstin else "GSTIN present; no party linked"

        rows.append(
            {
                "invoice_id": inv.id,
                "transaction_id": inv.transaction_id,
                "invoice_number": inv.invoice_number,
                "invoice_gstin": inv_gstin,
                "party_gstin": party_gstin,
                "invoice_total": total,
                "match_status": status,
                "detail": detail,
            }
        )
    return run_id, rows
