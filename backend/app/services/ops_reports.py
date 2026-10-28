"""Phase C — month / tank / customer / job-work / audit operational reports."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timezone

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.jobwork import JobWorkBatch, ProductionLoss
from app.models.parties import Customer
from app.models.stock import Product, StockMovement, StorageUnit
from app.models.transaction import Transaction
from app.services.report_service import _day_bounds, resolve_period
from app.services.stock_engine import compute_balance, signed_qty


@dataclass
class TableReport:
    title: str
    date_from: str
    date_to: str
    columns: list[str]
    rows: list[list[str]]
    summary: dict[str, str | int | float]


def _bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    start, _ = _day_bounds(date_from)
    _, end = _day_bounds(date_to)
    return start, end


def build_month_stock(db: Session, *, date_from: date, date_to: date) -> TableReport:
    """Opening / received / loaded / closing per product × tank for the period."""
    start, end = _bounds(date_from, date_to)
    moves = list(db.execute(select(StockMovement)).scalars().all())
    keys: set[tuple[str, str]] = set()
    for m in moves:
        keys.add((m.product_id, m.storage_unit_id))

    rows: list[list[str]] = []
    total_in = 0.0
    total_out = 0.0
    for pid, sid in sorted(keys, key=lambda k: k):
        product = db.get(Product, pid)
        unit = db.get(StorageUnit, sid)
        if not product or not unit:
            continue
        opening = 0.0
        received = 0.0
        loaded = 0.0
        open_l = 0.0
        in_l = 0.0
        out_l = 0.0
        for m in moves:
            if m.product_id != pid or m.storage_unit_id != sid:
                continue
            signed = signed_qty(m.direction, m.quantity) if m.direction != "ADJUST" else float(m.quantity)
            litres = float(m.quantity_litres) if m.quantity_litres is not None else None
            created = m.created_at
            if created is None:
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created < start:
                opening += signed
                if litres is not None:
                    open_l += litres if signed >= 0 else -abs(litres)
            elif start <= created < end:
                if signed >= 0:
                    received += signed
                    if litres is not None:
                        in_l += abs(litres)
                else:
                    loaded += abs(signed)
                    if litres is not None:
                        out_l += abs(litres)
        closing = opening + received - loaded
        close_l = open_l + in_l - out_l
        total_in += received
        total_out += loaded
        rows.append(
            [
                product.code,
                product.name,
                unit.code,
                unit.kind,
                f"{round(opening, 3)}",
                f"{round(received, 3)}",
                f"{round(loaded, 3)}",
                f"{round(closing, 3)}",
                product.unit,
                f"{round(open_l, 2)}" if open_l or in_l or out_l else "—",
                f"{round(in_l, 2)}" if in_l else "—",
                f"{round(out_l, 2)}" if out_l else "—",
                f"{round(close_l, 2)}" if open_l or in_l or out_l else "—",
            ]
        )

    return TableReport(
        title="Month-wise stock movement",
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        columns=[
            "Product",
            "Name",
            "Tank",
            "Kind",
            "Opening",
            "Received",
            "Loaded",
            "Closing",
            "Unit",
            "Open L",
            "In L",
            "Out L",
            "Close L",
        ],
        rows=rows,
        summary={
            "lines": len(rows),
            "received_total": round(total_in, 3),
            "loaded_total": round(total_out, 3),
        },
    )


def build_tank_wise(db: Session) -> TableReport:
    balances = compute_balance(db)
    rows = [
        [
            b.storage_code,
            b.storage_kind,
            b.product_code,
            b.product_name,
            f"{b.quantity}",
            b.unit,
        ]
        for b in balances
    ]
    today = datetime.now(timezone.utc).date().isoformat()
    return TableReport(
        title="Tank-wise stock balances",
        date_from=today,
        date_to=today,
        columns=["Tank", "Kind", "Product", "Name", "Balance", "Unit"],
        rows=rows,
        summary={"tanks_lines": len(rows), "total_qty": round(sum(b.quantity for b in balances), 3)},
    )


def build_customer_wise(db: Session, *, date_from: date, date_to: date) -> TableReport:
    start, end = _bounds(date_from, date_to)
    txns = list(
        db.execute(
            select(Transaction).where(
                and_(
                    Transaction.created_at >= start,
                    Transaction.created_at < end,
                    Transaction.customer_id.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    buckets: dict[str, dict] = {}
    for t in txns:
        cid = t.customer_id or ""
        b = buckets.setdefault(
            cid,
            {"count": 0, "net": 0.0, "litres": 0.0, "completed": 0},
        )
        b["count"] += 1
        if t.net_kg is not None:
            b["net"] += float(t.net_kg)
        if t.calculated_litres is not None:
            b["litres"] += float(t.calculated_litres)
        if t.status == "COMPLETED":
            b["completed"] += 1

    rows: list[list[str]] = []
    for cid, b in sorted(buckets.items(), key=lambda x: x[0]):
        cust = db.get(Customer, cid)
        rows.append(
            [
                cust.code if cust else "—",
                cust.name if cust else cid[:8],
                (cust.gstin or "—") if cust else "—",
                str(b["count"]),
                str(b["completed"]),
                f"{round(b['net'], 3)}",
                f"{round(b['litres'], 2)}",
            ]
        )
    return TableReport(
        title="Customer-wise movements",
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        columns=["Code", "Customer", "GSTIN", "Trips", "Completed", "Net kg", "Litres"],
        rows=rows,
        summary={"customers": len(rows), "trips": sum(int(r[3]) for r in rows)},
    )


def build_jobwork_recon(db: Session, *, date_from: date, date_to: date) -> TableReport:
    start, end = _bounds(date_from, date_to)
    batches = list(
        db.execute(
            select(JobWorkBatch).where(
                and_(JobWorkBatch.created_at >= start, JobWorkBatch.created_at < end)
            ).order_by(JobWorkBatch.created_at.desc())
        )
        .scalars()
        .all()
    )
    rows: list[list[str]] = []
    approval_needed = 0
    for batch in batches:
        loss = db.execute(
            select(ProductionLoss).where(ProductionLoss.batch_id == batch.id).order_by(ProductionLoss.created_at.desc())
        ).scalars().first()
        product = db.get(Product, batch.product_id) if batch.product_id else None
        flag = "OK"
        loss_pct = "—"
        if loss:
            loss_pct = f"{round(loss.loss_percent, 2)}"
            if loss.requires_approval and not loss.approved:
                flag = "APPROVAL REQUIRED"
                approval_needed += 1
            elif loss.requires_approval and loss.approved:
                flag = "APPROVED"
        rows.append(
            [
                batch.batch_code,
                batch.transaction_id,
                product.code if product else "—",
                batch.customer_name or "—",
                "" if batch.qty_in is None else str(batch.qty_in),
                "" if batch.qty_out is None else str(batch.qty_out),
                batch.unit,
                loss_pct,
                flag,
                batch.status,
            ]
        )
    return TableReport(
        title="Job-work reconciliation",
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        columns=[
            "Batch",
            "Txn",
            "Product",
            "Customer",
            "Qty in",
            "Qty out",
            "Unit",
            "Loss %",
            "Flag",
            "Status",
        ],
        rows=rows,
        summary={"batches": len(rows), "approval_required": approval_needed},
    )


def build_audit_trail(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    limit: int = 500,
) -> TableReport:
    start, end = _bounds(date_from, date_to)
    logs = list(
        db.execute(
            select(AuditLog)
            .where(and_(AuditLog.created_at >= start, AuditLog.created_at < end))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    rows = [
        [
            a.created_at.isoformat()[:19] if a.created_at else "",
            a.action,
            a.entity_type,
            a.entity_id or "—",
            a.transaction_id or "—",
            (a.details or "—")[:120],
        ]
        for a in logs
    ]
    return TableReport(
        title="Audit trail",
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        columns=["When", "Action", "Entity", "Entity ID", "Txn", "Details"],
        rows=rows,
        summary={"events": len(rows), "limit": limit},
    )


def table_to_xlsx(report: TableReport) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws.append([f"JV Industries — {report.title}"])
    ws.append([f"{report.date_from} → {report.date_to}"])
    ws.append([])
    ws.append(["Metric", "Value"])
    for k, v in report.summary.items():
        ws.append([k, v])
    ws.append([])
    ws.append(report.columns)
    for row in report.rows:
        ws.append(row)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def table_to_csv(report: TableReport) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(report.columns)
    for row in report.rows:
        w.writerow(row)
    return buf.getvalue().encode("utf-8")


def table_to_pdf(report: TableReport) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    brand = ParagraphStyle("TBrand", parent=styles["Heading1"], fontSize=14, textColor=colors.HexColor("#0F2430"))
    sub = ParagraphStyle("TSub", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#4A5C66"))
    story = [
        Paragraph(f"JV Industries — {report.title}", brand),
        Paragraph(f"{report.date_from} → {report.date_to}", sub),
        Spacer(1, 6),
        Paragraph(" · ".join(f"{k}={v}" for k, v in report.summary.items()), sub),
        Spacer(1, 8),
    ]
    data = [report.columns]
    for row in report.rows[:400]:
        data.append([str(c)[:28] for c in row])
    if len(report.rows) > 400:
        data.append([f"… {len(report.rows) - 400} more truncated"] + [""] * (len(report.columns) - 1))
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2430")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9AA8B0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F8")]),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buf.getvalue()


def build_named_report(
    db: Session,
    *,
    kind: str,
    period: str,
    date_from: str | None = None,
    date_to: str | None = None,
    on_day: str | None = None,
) -> TableReport:
    kind = kind.lower()
    if kind == "tank":
        return build_tank_wise(db)
    label, d0, d1 = resolve_period(period=period, date_from=date_from, date_to=date_to, on_day=on_day)
    _ = label
    if kind in {"stock", "month", "month_stock"}:
        return build_month_stock(db, date_from=d0, date_to=d1)
    if kind == "customer":
        return build_customer_wise(db, date_from=d0, date_to=d1)
    if kind in {"jobwork", "job_work"}:
        return build_jobwork_recon(db, date_from=d0, date_to=d1)
    if kind == "audit":
        return build_audit_trail(db, date_from=d0, date_to=d1)
    raise ValueError("Unknown report kind. Use stock, tank, customer, jobwork, or audit.")
