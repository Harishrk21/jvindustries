from datetime import date

from app.services.report_service import ReportBundle, ReportRow, report_to_pdf, report_to_xlsx, resolve_period


def test_resolve_daily_monthly_custom():
    label, a, b = resolve_period(period="daily", on_day="2026-10-27")
    assert label == "DAILY" and a == b == date(2026, 10, 27)

    label, a, b = resolve_period(period="monthly", on_day="2026-10-15")
    assert label == "MONTHLY" and a == date(2026, 10, 1) and b == date(2026, 10, 31)

    label, a, b = resolve_period(period="custom", date_from="2026-10-01", date_to="2026-10-10")
    assert label == "CUSTOM" and a == date(2026, 10, 1) and b == date(2026, 10, 10)


def test_pdf_xlsx_bytes():
    bundle = ReportBundle(
        title="DAILY operations report",
        date_from="2026-10-27",
        date_to="2026-10-27",
        rows=[
            ReportRow(
                transaction_id="JV-2026-000001",
                type="MATERIAL_LOADING_OUTWARD",
                status="COMPLETED",
                vehicle_number="TN 09 AB 1234",
                net_kg="100",
                litres="118",
                stock_posted="Y",
                created_at="2026-10-27T10:00:00+00:00",
            )
        ],
        summary={"transactions": 1, "net_kg_total": 100.0, "litres_total": 118.0},
    )
    pdf = report_to_pdf(bundle)
    assert pdf.startswith(b"%PDF")
    xlsx = report_to_xlsx(bundle)
    assert xlsx[:2] == b"PK"  # zip/xlsx
