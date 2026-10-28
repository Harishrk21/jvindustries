from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.pdf_service import build_gate_pass_pdf, build_transaction_summary_pdf


def test_transaction_pdf_header():
    txn = SimpleNamespace(
        transaction_id="JV-2026-009999",
        type="JOB_WORK",
        status="ENTRY_STARTED",
        vehicle_number="TN 09 AB 1234",
        driver_name="Ravi",
        tare_kg=11820.0,
        gross_kg=45110.0,
        net_kg=33290.0,
        density_kg_per_l=0.845,
        calculated_litres=39396.45,
        stock_posted=False,
    )
    pdf = build_transaction_summary_pdf(txn=txn)  # type: ignore[arg-type]
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_gate_pass_pdf_header():
    txn = SimpleNamespace(
        transaction_id="JV-2026-009998",
        vehicle_number="TN 09 AB 1234",
        driver_name="Ravi",
        status="VEHICLE_VERIFIED",
    )
    gp = SimpleNamespace(
        gate_pass_number="GP-2026-000001",
        pass_type="OUTWARD_LOADING",
        direction="INWARD",
        vehicle_number="TN 09 AB 1234",
        driver_name="Ravi",
        created_at=datetime.now(timezone.utc),
    )
    pdf = build_gate_pass_pdf(txn=txn, gate_pass=gp)  # type: ignore[arg-type]
    assert pdf.startswith(b"%PDF")
