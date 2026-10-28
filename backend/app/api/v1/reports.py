"""Phase 10 — Daily / monthly / custom reports (JSON + PDF/Excel)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission
from app.models.reports import ReportExport
from app.models.user import User
from app.services.audit_service import write_audit
from app.services.ops_reports import (
    build_named_report,
    table_to_csv,
    table_to_pdf,
    table_to_xlsx,
)
from app.services.report_service import (
    build_operations_report,
    report_to_csv,
    report_to_pdf,
    report_to_xlsx,
    resolve_period,
)

_OPS_KINDS = {"stock", "month", "month_stock", "tank", "customer", "jobwork", "job_work", "audit"}

router = APIRouter()


class ReportSummaryOut(BaseModel):
    report_type: str
    date_from: str
    date_to: str
    title: str
    summary: dict
    row_count: int
    sample_rows: list[dict]


class ReportExportOut(BaseModel):
    id: str
    report_type: str
    format: str
    date_from: str
    date_to: str
    row_count: int
    file_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


def _bundle(db: Session, period: str, date_from: str | None, date_to: str | None, on_day: str | None):
    try:
        label, d0, d1 = resolve_period(period=period, date_from=date_from, date_to=date_to, on_day=on_day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    title = f"{label} operations report"
    return label, build_operations_report(db, date_from=d0, date_to=d1, title=title)


@router.get("/summary", response_model=ReportSummaryOut)
def report_summary(
    period: str = Query("daily"),
    date_from: str | None = None,
    date_to: str | None = None,
    on_day: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.view", "dashboard.view")),
) -> ReportSummaryOut:
    if period.lower() not in {"daily", "monthly", "custom"}:
        raise HTTPException(status_code=400, detail="period must be daily, monthly, or custom.")
    label, bundle = _bundle(db, period, date_from, date_to, on_day)
    sample = [
        {
            "transaction_id": r.transaction_id,
            "type": r.type,
            "status": r.status,
            "vehicle_number": r.vehicle_number,
            "net_kg": r.net_kg,
            "litres": r.litres,
            "stock_posted": r.stock_posted,
            "created_at": r.created_at,
        }
        for r in bundle.rows[:20]
    ]
    return ReportSummaryOut(
        report_type=label,
        date_from=bundle.date_from,
        date_to=bundle.date_to,
        title=bundle.title,
        summary=bundle.summary,
        row_count=len(bundle.rows),
        sample_rows=sample,
    )


@router.get("/export")
def export_report(
    period: str = Query("daily"),
    format: str = Query("pdf"),
    date_from: str | None = None,
    date_to: str | None = None,
    on_day: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view")),
) -> Response:
    if period.lower() not in {"daily", "monthly", "custom"}:
        raise HTTPException(status_code=400, detail="period must be daily, monthly, or custom.")
    if format.lower() not in {"pdf", "xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format must be pdf, xlsx, or csv.")
    label, bundle = _bundle(db, period, date_from, date_to, on_day)
    fmt = format.upper()
    if fmt == "PDF":
        content = report_to_pdf(bundle)
        media = "application/pdf"
        ext = "pdf"
    elif fmt == "XLSX":
        content = report_to_xlsx(bundle)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        content = report_to_csv(bundle)
        media = "text/csv"
        ext = "csv"

    file_name = f"JV-{label}-{bundle.date_from}_to_{bundle.date_to}.{ext}"
    export = ReportExport(
        report_type=label,
        format=fmt,
        date_from=bundle.date_from,
        date_to=bundle.date_to,
        row_count=len(bundle.rows),
        file_name=file_name,
        notes=f"summary_txns={bundle.summary.get('transactions', 0)}",
        created_by=user.id,
    )
    db.add(export)
    write_audit(
        db,
        action="REPORT_EXPORTED",
        entity_type="report_export",
        entity_id=export.id,
        actor_user_id=user.id,
        details=f"{label} {fmt} rows={len(bundle.rows)}",
    )
    db.commit()

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/exports", response_model=list[ReportExportOut])
def list_exports(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.view", "report.export")),
) -> list[ReportExport]:
    rows = (
        db.execute(select(ReportExport).order_by(ReportExport.created_at.desc()).limit(limit)).scalars().all()
    )
    return list(rows)


class OpsReportOut(BaseModel):
    kind: str
    title: str
    date_from: str
    date_to: str
    columns: list[str]
    rows: list[list[str]]
    summary: dict
    row_count: int


@router.get("/ops/{kind}", response_model=OpsReportOut)
def ops_report(
    kind: str,
    period: str = Query("monthly"),
    date_from: str | None = None,
    date_to: str | None = None,
    on_day: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.view", "dashboard.view", "audit.view")),
) -> OpsReportOut:
    if kind.lower() not in _OPS_KINDS:
        raise HTTPException(
            status_code=400,
            detail="kind must be stock, tank, customer, jobwork, or audit.",
        )
    if kind.lower() != "tank" and period.lower() not in {"daily", "monthly", "custom"}:
        raise HTTPException(status_code=400, detail="period must be daily, monthly, or custom.")
    try:
        report = build_named_report(
            db,
            kind=kind,
            period=period,
            date_from=date_from,
            date_to=date_to,
            on_day=on_day,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OpsReportOut(
        kind=kind.lower(),
        title=report.title,
        date_from=report.date_from,
        date_to=report.date_to,
        columns=report.columns,
        rows=report.rows,
        summary=report.summary,
        row_count=len(report.rows),
    )


@router.get("/ops/{kind}/export")
def ops_report_export(
    kind: str,
    period: str = Query("monthly"),
    format: str = Query("xlsx"),
    date_from: str | None = None,
    date_to: str | None = None,
    on_day: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("report.export", "report.view", "audit.view")),
) -> Response:
    if kind.lower() not in _OPS_KINDS:
        raise HTTPException(status_code=400, detail="Unknown ops report kind.")
    if format.lower() not in {"pdf", "xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format must be pdf, xlsx, or csv.")
    try:
        report = build_named_report(
            db,
            kind=kind,
            period=period,
            date_from=date_from,
            date_to=date_to,
            on_day=on_day,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    fmt = format.upper()
    if fmt == "PDF":
        content = table_to_pdf(report)
        media = "application/pdf"
        ext = "pdf"
    elif fmt == "XLSX":
        content = table_to_xlsx(report)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        content = table_to_csv(report)
        media = "text/csv"
        ext = "csv"

    file_name = f"JV-{kind.upper()}-{report.date_from}_to_{report.date_to}.{ext}"
    export = ReportExport(
        report_type=f"OPS_{kind.upper()}",
        format=fmt,
        date_from=report.date_from,
        date_to=report.date_to,
        row_count=len(report.rows),
        file_name=file_name,
        notes=str(report.summary),
        created_by=user.id,
    )
    db.add(export)
    write_audit(
        db,
        action="OPS_REPORT_EXPORTED",
        entity_type="report_export",
        entity_id=export.id,
        actor_user_id=user.id,
        details=f"{kind} {fmt} rows={len(report.rows)}",
    )
    db.commit()
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
