"""Branded JV Industries PDFs — weighment slip + vehicle goods gate pass (Phase D)."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.calibration import WeighbridgeCalibration
from app.models.transaction import Transaction
from app.models.vehicle import GatePass

# Plant identity (from JV paper templates)
COMPANY = "JV INDUSTRIES"
TAGLINE = "RESOURCE RECYCLING FOR A CLEANER TOMORROW"
SUBLINE = "Recycling & Reprocessing of Petroleum Oils"
ADDRESS = "S.No. 821/A, Diguvamasampalli (V), Tiruttani Road, Chittoor, Andhra Pradesh – 517 503"
GSTIN = "37AARFJ6100D1ZI"
PHONE = "+91 94443 36500"
EMAIL = "jvindustries21@gmail.com"

NAVY = colors.HexColor("#0F2430")
GREEN = colors.HexColor("#1B6B4A")
BLUE = colors.HexColor("#1E4D7B")
GOLD = colors.HexColor("#C4A35A")
MUTED = colors.HexColor("#4A5C66")
ROW_BG = colors.HexColor("#E8EEF1")
GRID = colors.HexColor("#9AA8B0")


def _styles():
    base = getSampleStyleSheet()
    brand = ParagraphStyle(
        "JVBrand",
        parent=base["Heading1"],
        fontSize=16,
        textColor=NAVY,
        spaceAfter=2,
        alignment=1,
    )
    tag = ParagraphStyle(
        "JVTag",
        parent=base["Normal"],
        fontSize=8,
        textColor=GOLD,
        spaceAfter=2,
        alignment=1,
        fontName="Helvetica-Bold",
    )
    sub = ParagraphStyle(
        "JVSub",
        parent=base["Normal"],
        fontSize=8,
        textColor=MUTED,
        spaceAfter=2,
        alignment=1,
        leading=10,
    )
    section = ParagraphStyle(
        "JVSection",
        parent=base["Normal"],
        fontSize=10,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=1,
    )
    body = ParagraphStyle(
        "JVBody",
        parent=base["Normal"],
        fontSize=9,
        textColor=NAVY,
        leading=12,
    )
    small = ParagraphStyle(
        "JVSmall",
        parent=base["Normal"],
        fontSize=7.5,
        textColor=MUTED,
        leading=9,
    )
    return brand, tag, sub, section, body, small


def _kv_table(rows: list[list[Any]], col_widths: list[float] | None = None) -> Table:
    table = Table(rows, colWidths=col_widths or [48 * mm, 122 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), ROW_BG),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
                ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _section_bar(title: str, fill: colors.Color, section_style: ParagraphStyle, width: float = 170 * mm) -> Table:
    t = Table([[Paragraph(title, section_style)]], colWidths=[width])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _header_block(brand, tag, sub, small, *, doc_title: str, right_meta: list[tuple[str, str]]):
    story = [
        Paragraph(COMPANY, brand),
        Paragraph(TAGLINE, tag),
        Paragraph(SUBLINE, sub),
        Paragraph(ADDRESS, small),
        Paragraph(f"GSTIN: {GSTIN} · Tel: {PHONE} · {EMAIL}", small),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1.2, color=NAVY, spaceAfter=6),
    ]
    meta_left = Paragraph(f"<b>{doc_title}</b>", brand)
    meta_rows = [[k, v] for k, v in right_meta]
    meta_tbl = Table(meta_rows, colWidths=[32 * mm, 48 * mm])
    meta_tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    top = Table([[meta_left, meta_tbl]], colWidths=[90 * mm, 80 * mm])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(top)
    story.append(Spacer(1, 8))
    return story


def _fmt_dt(dt: datetime | None) -> tuple[str, str]:
    if not dt:
        return "—", "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    localish = dt.astimezone(timezone.utc)
    return localish.strftime("%d/%m/%Y"), localish.strftime("%H:%M")


def _kg_mt(kg: float | None) -> tuple[str, str]:
    if kg is None:
        return "—", "—"
    return f"{kg:,.0f}" if float(kg).is_integer() else f"{kg:,.3f}", f"{float(kg) / 1000.0:,.3f}"


def build_gate_pass_pdf(*, txn: Transaction, gate_pass: GatePass) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm
    )
    brand, tag, sub, section, body, small = _styles()
    issued = gate_pass.created_at or datetime.now(timezone.utc)
    d, t = _fmt_dt(issued)

    purpose = (gate_pass.purpose or txn.purpose or gate_pass.direction or "").upper()
    purpose_marks = "  ".join(
        [
            f"[{'X' if purpose == 'INWARD' else ' '}] Inward",
            f"[{'X' if purpose == 'OUTWARD' else ' '}] Outward",
            f"[{'X' if purpose == 'JOB_WORK' else ' '}] Job Work",
            f"[{'X' if purpose == 'OTHER' else ' '}] Other",
        ]
    )

    story = _header_block(
        brand,
        tag,
        sub,
        small,
        doc_title="VEHICLE GOODS MOVEMENT GATE PASS",
        right_meta=[
            ("Gate Pass No.", gate_pass.gate_pass_number),
            ("Date", d),
            ("Time In", t),
            ("Txn", txn.transaction_id),
        ],
    )

    story.append(_section_bar("VEHICLE DETAILS", GREEN, section))
    story.append(Spacer(1, 4))
    story.append(
        _kv_table(
            [
                ["Vehicle No.", gate_pass.vehicle_number or txn.vehicle_number or "—"],
                ["Vehicle Type", gate_pass.vehicle_type or txn.vehicle_type or "—"],
                ["Driver Name", gate_pass.driver_name or txn.driver_name or "—"],
                ["Driver Mobile", gate_pass.driver_mobile or txn.driver_mobile or "—"],
                ["Transporter / Company", gate_pass.transporter_name or txn.transporter_name or "—"],
            ]
        )
    )
    story.append(Spacer(1, 8))

    story.append(_section_bar("GOODS DETAILS", BLUE, section))
    story.append(Spacer(1, 4))
    story.append(
        _kv_table(
            [
                ["Purpose", purpose_marks],
                ["Material / Goods", gate_pass.material_description or "—"],
                ["Quantity", f"{gate_pass.quantity_text or (str(txn.net_kg) if txn.net_kg is not None else '—')} {gate_pass.unit_text or 'kg'}".strip()],
                ["Invoice / Challan No.", gate_pass.invoice_challan_no or "—"],
                ["From", gate_pass.from_location or txn.from_location or "—"],
                ["Destination", gate_pass.to_location or txn.to_location or "—"],
                ["Remarks", gate_pass.remarks or txn.remarks or "—"],
            ]
        )
    )
    story.append(Spacer(1, 8))

    story.append(_section_bar("SECURITY VERIFICATION", colors.HexColor("#8A6D1D"), section))
    story.append(Spacer(1, 4))
    yes_no = lambda ok: "Yes ☑   No ☐" if ok else "Yes ☐   No ☑"
    story.append(
        _kv_table(
            [
                ["Vehicle Checked", yes_no(bool(gate_pass.vehicle_checked))],
                ["Goods Verified", yes_no(bool(gate_pass.goods_verified))],
                ["Documents Verified", yes_no(bool(gate_pass.documents_verified))],
            ]
        )
    )
    story.append(Spacer(1, 16))

    sig = Table(
        [
            ["Driver Signature", "Security Officer", "Authorized By"],
            ["________________", "________________", "________________"],
            ["Name / Date", "Name / Date", "Name / Date"],
        ],
        colWidths=[56 * mm, 56 * mm, 56 * mm],
    )
    sig.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(sig)
    story.append(Spacer(1, 12))
    story.append(Paragraph("JV INDUSTRIES — SECURITY — CHITTOOR (A.P.)", small))
    story.append(
        Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Server authoritative",
            small,
        )
    )
    doc.build(story)
    return buf.getvalue()


def build_weighment_slip_pdf(
    *,
    txn: Transaction,
    calibration: WeighbridgeCalibration | None = None,
    party_name: str | None = None,
    party_address: str | None = None,
    party_mobile: str | None = None,
    product_name: str | None = None,
    gate_pass_no: str | None = None,
    gross_at: datetime | None = None,
    tare_at: datetime | None = None,
    issued_by: str | None = None,
) -> bytes:
    """Customer-facing weighment slip matching plant template sections."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm
    )
    brand, tag, sub, section, body, small = _styles()
    created = txn.created_at or datetime.now(timezone.utc)
    d, t = _fmt_dt(created)
    slip_no = txn.transaction_id

    story = _header_block(
        brand,
        tag,
        sub,
        small,
        doc_title="WEIGHMENT SLIP",
        right_meta=[
            ("Slip No.", slip_no),
            ("Date", d),
            ("Time", t),
            ("Gate Pass", gate_pass_no or "—"),
        ],
    )

    story.append(_section_bar("VEHICLE & DRIVER", GREEN, section))
    story.append(Spacer(1, 4))
    story.append(
        _kv_table(
            [
                ["Vehicle No.", txn.vehicle_number or "—"],
                ["Vehicle Type", txn.vehicle_type or "—"],
                ["Driver Name", txn.driver_name or "—"],
                ["Driver Contact", txn.driver_mobile or "—"],
                ["Transporter", txn.transporter_name or "—"],
            ]
        )
    )
    story.append(Spacer(1, 8))

    story.append(_section_bar("CUSTOMER / PARTY DETAILS", BLUE, section))
    story.append(Spacer(1, 4))
    story.append(
        _kv_table(
            [
                ["Customer / Party", party_name or "—"],
                ["Address", party_address or "—"],
                ["Contact No.", party_mobile or txn.customer_whatsapp or "—"],
                ["Product / Material", product_name or "—"],
                ["Purpose / Reference", txn.purpose or txn.type.replace("_", " "),],
                ["Remarks", txn.remarks or "—"],
            ]
        )
    )
    story.append(Spacer(1, 8))

    story.append(_section_bar("WEIGHT PARTICULARS", NAVY, section))
    story.append(Spacer(1, 4))
    gd, gt = _fmt_dt(gross_at)
    td, tt = _fmt_dt(tare_at)
    g_kg, g_mt = _kg_mt(txn.gross_kg)
    t_kg, t_mt = _kg_mt(txn.tare_kg)
    n_kg, n_mt = _kg_mt(txn.net_kg)
    weight_data = [
        ["PARTICULARS", "DATE", "TIME", "WEIGHT (kg)", "WEIGHT (MT)"],
        ["GROSS WEIGHT (Entry)", gd, gt, g_kg, g_mt],
        ["TARE WEIGHT (Exit)", td, tt, t_kg, t_mt],
        ["NET WEIGHT", "—", "—", n_kg, n_mt],
    ]
    wt = Table(weight_data, colWidths=[52 * mm, 28 * mm, 22 * mm, 34 * mm, 34 * mm])
    wt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DCE8F0")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(wt)
    dens_line = (
        f"Density: {txn.density_kg_per_l} kg/L"
        + (f" · Temp: {txn.temperature_c} °C" if txn.temperature_c is not None else "")
        + (f" · Calculated: {txn.calculated_litres} L" if txn.calculated_litres is not None else "")
    )
    story.append(Spacer(1, 4))
    story.append(Paragraph(dens_line if txn.density_kg_per_l is not None else "Density / litres: —", body))
    story.append(Spacer(1, 8))

    story.append(_section_bar("WEIGHBRIDGE CALIBRATION / VERIFICATION", colors.HexColor("#5C3D1E"), section))
    story.append(Spacer(1, 4))
    if calibration:
        story.append(
            _kv_table(
                [
                    ["Certificate No.", calibration.certificate_no],
                    [
                        "Verification / Next due",
                        f"{calibration.verification_date or '—'} / {calibration.next_due_date or '—'}",
                    ],
                    [
                        "Legal Metrology Officer",
                        f"{calibration.officer_name or '—'}"
                        + (f", {calibration.officer_title}" if calibration.officer_title else ""),
                    ],
                    ["Make / Model", calibration.make_model or "—"],
                    [
                        "Capacity (kg)",
                        f"Max {calibration.max_capacity_kg or '—'} · Min {calibration.min_capacity_kg or '—'}",
                    ],
                    ["Accuracy Class", calibration.accuracy_class or "—"],
                    [
                        "e / d value (kg)",
                        f"{calibration.e_value_kg or '—'} / {calibration.d_value_kg or '—'}",
                    ],
                    [
                        "Seals",
                        f"{calibration.seals_count or '—'} ({calibration.seals_note or '—'})",
                    ],
                ]
            )
        )
        story.append(Spacer(1, 2))
        story.append(Paragraph("SCAN / VERIFY CERTIFICATE — Weighbridge Calibration on file at plant.", small))
    else:
        story.append(Paragraph("No active calibration certificate on file.", body))

    story.append(Spacer(1, 14))
    sig = Table(
        [
            ["Weigh Bridge Operator", "Customer / Driver", "Authorised Signatory"],
            ["________________", "________________", "________________"],
            [issued_by or "Name & Signature", "Name & Signature", "For JV Industries"],
        ],
        colWidths=[56 * mm, 56 * mm, 56 * mm],
    )
    sig.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(sig)
    story.append(Spacer(1, 10))
    story.append(Paragraph("COMPANY SEAL — JV INDUSTRIES, CHITTOOR (A.P.)", small))
    story.append(
        Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Customer copy",
            small,
        )
    )
    doc.build(story)
    return buf.getvalue()


def build_transaction_summary_pdf(
    *,
    txn: Transaction,
    extra_rows: list[tuple[str, str]] | None = None,
    variant: str = "internal",
    calibration: WeighbridgeCalibration | None = None,
    party_name: str | None = None,
    party_address: str | None = None,
    party_mobile: str | None = None,
    product_name: str | None = None,
    gate_pass_no: str | None = None,
    gross_at: datetime | None = None,
    tare_at: datetime | None = None,
    issued_by: str | None = None,
) -> bytes:
    """customer → branded weighment slip; internal → compact ops summary."""
    if variant.lower() == "customer":
        return build_weighment_slip_pdf(
            txn=txn,
            calibration=calibration,
            party_name=party_name,
            party_address=party_address,
            party_mobile=party_mobile,
            product_name=product_name,
            gate_pass_no=gate_pass_no,
            gross_at=gross_at,
            tare_at=tare_at,
            issued_by=issued_by,
        )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm
    )
    brand, tag, sub, section, body, small = _styles()
    story = [
        Paragraph(COMPANY, brand),
        Paragraph("Internal Transaction Summary", tag),
        Paragraph(f"<b>{txn.transaction_id}</b> · {txn.status}", body),
        Spacer(1, 8),
    ]
    rows = [
        ["Type", txn.type],
        ["Status", txn.status],
        ["Vehicle", txn.vehicle_number or "—"],
        ["Driver", txn.driver_name or "—"],
        ["Tare kg", str(txn.tare_kg) if txn.tare_kg is not None else "—"],
        ["Gross kg", str(txn.gross_kg) if txn.gross_kg is not None else "—"],
        ["Net kg (server)", str(txn.net_kg) if txn.net_kg is not None else "—"],
        ["Density", str(txn.density_kg_per_l) if txn.density_kg_per_l is not None else "—"],
        ["Calculated litres", str(txn.calculated_litres) if txn.calculated_litres is not None else "—"],
        ["Stock posted", "Yes" if txn.stock_posted else "No"],
        ["Geofence OK", "Yes" if txn.geofence_ok else ("No" if txn.geofence_ok is False else "—")],
    ]
    if extra_rows:
        rows.extend([list(r) for r in extra_rows])
    story.append(_kv_table(rows))
    story.append(Spacer(1, 10))
    story.append(Paragraph("INTERNAL — Not for customer distribution.", small))
    doc.build(story)
    return buf.getvalue()
