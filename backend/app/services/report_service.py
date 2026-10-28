"""Operational reports — daily / monthly / custom date ranges."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.canteen import CanteenPurchase
from app.models.equipment import Equipment
from app.models.stock import StockMovement
from app.models.transaction import Transaction


@dataclass(frozen=True)
class ReportRow:
    transaction_id: str
    type: str
    status: str
    vehicle_number: str
    net_kg: str
    litres: str
    stock_posted: str
    created_at: str


@dataclass(frozen=True)
class ReportBundle:
    title: str
    date_from: str
    date_to: str
    rows: list[ReportRow]
    summary: dict[str, int | float]


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def resolve_period(
    *,
    period: str,
    date_from: str | None = None,
    date_to: str | None = None,
    on_day: str | None = None,
) -> tuple[str, date, date]:
    """Return (label, from_date, to_date inclusive)."""
    period = (period or "daily").upper()
    today = datetime.now(timezone.utc).date()

    if period == "DAILY":
        d = date.fromisoformat(on_day) if on_day else today
        return "DAILY", d, d
    if period == "MONTHLY":
        if on_day:
            d = date.fromisoformat(on_day)
        else:
            d = today
        first = date(d.year, d.month, 1)
        if d.month == 12:
            last = date(d.year, 12, 31)
        else:
            last = date(d.year, d.month + 1, 1) - timedelta(days=1)
        return "MONTHLY", first, last
    # CUSTOM
    if not date_from or not date_to:
        raise ValueError("Custom reports require date_from and date_to (YYYY-MM-DD).")
    a = date.fromisoformat(date_from)
    b = date.fromisoformat(date_to)
    if b < a:
        raise ValueError("date_to must be on or after date_from.")
    return "CUSTOM", a, b


def build_operations_report(db: Session, *, date_from: date, date_to: date, title: str) -> ReportBundle:
    start, _ = _day_bounds(date_from)
    _, end = _day_bounds(date_to)  # end exclusive next day after date_to

    txns = list(
        db.execute(
            select(Transaction)
            .where(and_(Transaction.created_at >= start, Transaction.created_at < end))
            .order_by(Transaction.created_at.desc())
        )
        .scalars()
        .all()
    )
    rows: list[ReportRow] = []
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    net_total = 0.0
    litres_total = 0.0
    for t in txns:
        by_type[t.type] = by_type.get(t.type, 0) + 1
        by_status[t.status] = by_status.get(t.status, 0) + 1
        if t.net_kg is not None:
            net_total += float(t.net_kg)
        if t.calculated_litres is not None:
            litres_total += float(t.calculated_litres)
        rows.append(
            ReportRow(
                transaction_id=t.transaction_id,
                type=t.type,
                status=t.status,
                vehicle_number=t.vehicle_number or "—",
                net_kg="" if t.net_kg is None else str(t.net_kg),
                litres="" if t.calculated_litres is None else str(t.calculated_litres),
                stock_posted="Y" if t.stock_posted else "N",
                created_at=t.created_at.isoformat() if t.created_at else "",
            )
        )

    stock_moves = (
        db.execute(
            select(func.count())
            .select_from(StockMovement)
            .where(and_(StockMovement.created_at >= start, StockMovement.created_at < end))
        ).scalar()
        or 0
    )
    canteen_buys = (
        db.execute(
            select(func.count())
            .select_from(CanteenPurchase)
            .where(
                and_(
                    CanteenPurchase.created_at >= start,
                    CanteenPurchase.created_at < end,
                    CanteenPurchase.status == "CONFIRMED",
                )
            )
        ).scalar()
        or 0
    )
    equipment_out = (
        db.execute(
            select(func.count())
            .select_from(Equipment)
            .where(Equipment.status == "OUT_FOR_REPAIR", Equipment.active.is_(True))
        ).scalar()
        or 0
    )

    summary = {
        "transactions": len(rows),
        "net_kg_total": round(net_total, 3),
        "litres_total": round(litres_total, 2),
        "stock_movements": int(stock_moves),
        "canteen_purchases": int(canteen_buys),
        "equipment_out_now": int(equipment_out),
        **{f"type_{k}": v for k, v in by_type.items()},
        **{f"status_{k}": v for k, v in by_status.items()},
    }
    return ReportBundle(
        title=title,
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        rows=rows,
        summary=summary,
    )


def report_to_pdf(bundle: ReportBundle) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    brand = ParagraphStyle("RBrand", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#0F2430"))
    sub = ParagraphStyle("RSub", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#4A5C66"))
    story = [
        Paragraph("JV Industries — Operations Report", brand),
        Paragraph(f"{bundle.title} · {bundle.date_from} → {bundle.date_to}", sub),
        Spacer(1, 8),
        Paragraph(
            f"Txns {bundle.summary.get('transactions', 0)} · "
            f"Net kg {bundle.summary.get('net_kg_total', 0)} · "
            f"Litres {bundle.summary.get('litres_total', 0)} · "
            f"Stock moves {bundle.summary.get('stock_movements', 0)} · "
            f"Canteen {bundle.summary.get('canteen_purchases', 0)}",
            sub,
        ),
        Spacer(1, 10),
    ]
    data = [["Txn ID", "Type", "Status", "Vehicle", "Net kg", "Litres", "Stock", "Created"]]
    for r in bundle.rows[:500]:
        data.append(
            [
                r.transaction_id,
                r.type.replace("_", " ")[:22],
                r.status[:18],
                r.vehicle_number,
                r.net_kg,
                r.litres,
                r.stock_posted,
                r.created_at[:19],
            ]
        )
    if len(bundle.rows) > 500:
        data.append(["…", f"{len(bundle.rows) - 500} more rows truncated", "", "", "", "", "", ""])
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2430")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9AA8B0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F8")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Server authoritative",
            sub,
        )
    )
    doc.build(story)
    return buf.getvalue()


def report_to_xlsx(bundle: ReportBundle) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Operations"
    ws.append(["JV Industries — Operations Report"])
    ws.append([bundle.title, f"{bundle.date_from} to {bundle.date_to}"])
    ws.append([])
    ws.append(["Metric", "Value"])
    for k, v in bundle.summary.items():
        ws.append([k, v])
    ws.append([])
    ws.append(["transaction_id", "type", "status", "vehicle_number", "net_kg", "litres", "stock_posted", "created_at"])
    for r in bundle.rows:
        ws.append(
            [r.transaction_id, r.type, r.status, r.vehicle_number, r.net_kg, r.litres, r.stock_posted, r.created_at]
        )
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def report_to_csv(bundle: ReportBundle) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["transaction_id", "type", "status", "vehicle_number", "net_kg", "litres", "stock_posted", "created_at"])
    for r in bundle.rows:
        w.writerow(
            [r.transaction_id, r.type, r.status, r.vehicle_number, r.net_kg, r.litres, r.stock_posted, r.created_at]
        )
    return buf.getvalue().encode("utf-8")
