"""Phase E — Supply & Expense, Distillation, Costing, Minutes of Meeting PDFs."""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.commercial import (
    CostingRequest,
    DistillationRequest,
    MomRequest,
    SupplyExpenseRequest,
)
from app.services.pdf_service import (
    ADDRESS,
    BLUE,
    COMPANY,
    EMAIL,
    GOLD,
    GREEN,
    GRID,
    GSTIN,
    MUTED,
    NAVY,
    PHONE,
    ROW_BG,
    SUBLINE,
)

_inr = lambda n: f"₹ {n:,.2f}"
_kg = lambda n: f"{n:,.0f} kg" if float(n).is_integer() else f"{n:,.3f} kg"


def _styles():
    base = getSampleStyleSheet()
    brand = ParagraphStyle("CBrand", parent=base["Heading1"], fontSize=15, textColor=BLUE, alignment=1, spaceAfter=2)
    sub = ParagraphStyle("CSub", parent=base["Normal"], fontSize=8, textColor=MUTED, alignment=1, leading=10)
    h = ParagraphStyle("CH", parent=base["Heading2"], fontSize=11, textColor=NAVY, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("CB", parent=base["Normal"], fontSize=9, textColor=NAVY, leading=12)
    small = ParagraphStyle("CS", parent=base["Normal"], fontSize=7.5, textColor=MUTED, leading=9)
    return brand, sub, h, body, small


def _header(story, brand, sub, title: str, meta: list[tuple[str, str]]):
    story += [
        Paragraph(COMPANY, brand),
        Paragraph(SUBLINE, sub),
        Paragraph(ADDRESS, sub),
        Paragraph(f"GSTIN: {GSTIN} · {PHONE} · {EMAIL}", sub),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=6),
        Paragraph(f"<b>{title}</b>", brand),
        Spacer(1, 4),
    ]
    rows = [[k, v] for k, v in meta]
    t = Table(rows, colWidths=[45 * mm, 125 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
                ("BACKGROUND", (0, 0), (0, -1), ROW_BG),
                ("GRID", (0, 0), (-1, -1), 0.3, GRID),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 8))


def _table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def _section(h_style, title: str):
    return Paragraph(f"<b>{title}</b>", h_style)


def build_supply_expense_pdf(req: SupplyExpenseRequest) -> bytes:
    brand, sub, h, body, small = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    story: list = []
    today = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    _header(
        story,
        brand,
        sub,
        "SUPPLY & EXPENSE ACCOUNTING STATEMENT",
        [
            ("Customer", req.customer_name),
            ("Address", req.customer_address or "—"),
            ("Report No.", req.report_no),
            ("Report Date", req.report_date or today),
            ("Processing Period", f"{req.period_from} to {req.period_to}"),
            ("Prepared As On", req.prepared_as_on or today),
        ],
    )

    story.append(_section(h, "1. Stock Movement Summary"))
    story.append(
        _table(
            [
                ["", "Feedstock Receipt", "Finished Product Delivery"],
                ["Period", f"{req.period_from} → {req.period_to}", f"{req.period_from} → {req.period_to}"],
                ["Consignments / Trips", str(req.feedstock_consignments), str(req.delivery_trips)],
                ["Total weight", _kg(req.feedstock_kg), _kg(req.delivery_kg)],
            ],
            col_widths=[40 * mm, 65 * mm, 65 * mm],
        )
    )

    story.append(_section(h, "2. Date-Wise Stock Movement Schedule"))
    rec = req.schedule_receipts or [{"date": req.period_from, "consignments": req.feedstock_consignments, "qty_kg": req.feedstock_kg}]
    deliv = req.schedule_deliveries or [{"date": req.period_to, "consignments": req.delivery_trips, "qty_kg": req.delivery_kg}]
    left = [["S.No", "Date", "Cons.", "Qty (kg)"]]
    for i, r in enumerate(rec[:20], 1):
        left.append([str(i), str(r.get("date", "")), str(r.get("consignments", "")), f"{float(r.get('qty_kg', 0)):,.0f}"])
    left.append(["", "TOTAL", "", f"{req.feedstock_kg:,.0f}"])
    right = [["S.No", "Date", "Trips", "Qty (kg)"]]
    for i, r in enumerate(deliv[:20], 1):
        right.append([str(i), str(r.get("date", "")), str(r.get("consignments", r.get("trips", ""))), f"{float(r.get('qty_kg', 0)):,.0f}"])
    right.append(["", "TOTAL", "", f"{req.delivery_kg:,.0f}"])
    twin = Table([[_table(left), _table(right)]], colWidths=[85 * mm, 85 * mm])
    story.append(twin)

    net_feed = req.feedstock_kg - req.bleaching_return_kg
    balance = net_feed - req.burner_fuel_kg - req.retail_kg - req.delivery_kg
    story.append(_section(h, "3. Material Accounting Reconciliation (kg)"))
    story.append(
        _table(
            [
                ["Particulars", "Qty (kg)"],
                ["1. Total Feedstock Received", f"{req.feedstock_kg:,.0f}"],
                ["2. Less: Bleaching Return Load", f"{req.bleaching_return_kg:,.0f}"],
                ["3. Net Feedstock for Distillation", f"{net_feed:,.0f}"],
                ["4. Less: Burner Fuel Consumed", f"{req.burner_fuel_kg:,.0f}"],
                ["5. Less: Direct Retail", f"{req.retail_kg:,.0f}"],
                ["6. Total Finished Product Delivered", f"{req.delivery_kg:,.0f}"],
                ["Balance (3−4−5−6)", f"{balance:,.0f}"],
            ],
            col_widths=[120 * mm, 50 * mm],
        )
    )

    burner_amt = req.burner_fuel_kg * req.burner_rate
    retail_amt = req.retail_kg * req.retail_rate
    deductions = burner_amt + retail_amt
    story.append(_section(h, "4. Customer Settlement / Deductions (INR)"))
    story.append(
        _table(
            [
                ["Item", "Qty", "Rate ₹/kg", "Amount ₹"],
                ["Burner Fuel Consumed", f"{req.burner_fuel_kg:,.0f}", f"{req.burner_rate:,.2f}", f"{burner_amt:,.2f}"],
                ["Direct Retail Quantity", f"{req.retail_kg:,.0f}", f"{req.retail_rate:,.2f}", f"{retail_amt:,.2f}"],
                ["Total Deductions", "", "", f"{deductions:,.2f}"],
            ],
            col_widths=[60 * mm, 35 * mm, 35 * mm, 40 * mm],
        )
    )

    base_amt = net_feed * req.processing_rate_per_kg
    gst = base_amt * req.gst_percent / 100.0
    invoice_total = base_amt + gst
    net_processing = invoice_total - deductions
    advance_bal = req.advance_paid - req.advance_received_back
    payable = net_processing + advance_bal

    story.append(_section(h, "5. Processing Invoice Reconciliation"))
    story.append(
        _table(
            [
                ["Particulars", "Amount ₹"],
                [f"Processing charges ({net_feed:,.0f} kg × ₹{req.processing_rate_per_kg:.2f})", f"{base_amt:,.2f}"],
                [f"GST @ {req.gst_percent:.0f}%", f"{gst:,.2f}"],
                ["Total Invoice (incl. GST)", f"{invoice_total:,.2f}"],
                ["Less: Total Deductions", f"{deductions:,.2f}"],
                ["Net Processing Amount Payable", f"{net_processing:,.2f}"],
            ],
            col_widths=[120 * mm, 50 * mm],
        )
    )

    story.append(_section(h, "6. Advance Sales Payment Reconciliation"))
    story.append(
        _table(
            [
                ["Particulars", "Amount ₹"],
                ["Advance paid", f"{req.advance_paid:,.2f}"],
                ["Less: Advance received back", f"{req.advance_received_back:,.2f}"],
                ["Balance Advance Amount", f"{advance_bal:,.2f}"],
            ],
            col_widths=[120 * mm, 50 * mm],
        )
    )

    story.append(_section(h, "7. Final Amount Payable"))
    box = Table(
        [[Paragraph(f"<b>FINAL AMOUNT PAYABLE: {_inr(payable)}</b>", body)]],
        colWidths=[170 * mm],
    )
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E6F4EA")),
                ("BOX", (0, 0), (-1, -1), 1.2, GREEN),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(box)
    story.append(Spacer(1, 14))
    sig = Table(
        [["Prepared By", "Checked By", "Approved By", "Received By (Customer)"]],
        colWidths=[42 * mm] * 4,
    )
    sig.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(sig)
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", small))
    doc.build(story)
    return buf.getvalue()


def _pie(labels: list[str], data: list[float], title: str) -> Drawing:
    d = Drawing(200, 140)
    d.add(String(100, 130, title, textAnchor="middle", fontSize=8, fillColor=NAVY))
    pie = Pie()
    pie.x = 35
    pie.y = 15
    pie.width = 90
    pie.height = 90
    pie.data = data if sum(data) > 0 else [1]
    pie.labels = labels if sum(data) > 0 else ["n/a"]
    pie.slices.strokeWidth = 0.5
    colors_list = [GREEN, BLUE, GOLD, colors.HexColor("#8B4513"), MUTED]
    for i in range(len(pie.data)):
        pie.slices[i].fillColor = colors_list[i % len(colors_list)]
    d.add(pie)
    return d


def _bars(values: list[float], labels: list[str], title: str) -> Drawing:
    d = Drawing(220, 140)
    d.add(String(110, 130, title, textAnchor="middle", fontSize=8, fillColor=NAVY))
    bc = VerticalBarChart()
    bc.x = 20
    bc.y = 20
    bc.height = 90
    bc.width = 180
    bc.data = [values if values else [0]]
    bc.categoryAxis.categoryNames = labels if labels else ["—"]
    bc.bars[0].fillColor = BLUE
    d.add(bc)
    return d


def build_distillation_pdf(req: DistillationRequest) -> bytes:
    brand, sub, h, body, small = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
    story: list = []
    today = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    net_feed = req.total_feed_kg - req.bleaching_return_kg
    accounted = req.first_cut_kg + req.second_cut_kg + req.bottom_cut_kg + req.vapor_loss_kg + req.water_loss_kg + req.boiler_fuel_kg
    _header(
        story,
        brand,
        sub,
        "DISTILLATION RECOVERY, SUPPLY & DELIVERY STATEMENT",
        [
            ("Report No.", req.report_no),
            ("Date", req.report_date or today),
            ("Customer", req.customer_name),
            ("Period", f"{req.period_from} → {req.period_to}"),
            ("Process capacity", _kg(req.process_capacity_kg)),
        ],
    )

    story.append(_section(h, "Material Balance"))
    story.append(
        _table(
            [
                ["Particulars", "kg"],
                ["Total Feedstock", f"{req.total_feed_kg:,.0f}"],
                ["Less: Bleaching return", f"{req.bleaching_return_kg:,.0f}"],
                ["Net Feed", f"{net_feed:,.0f}"],
                ["1st Cut", f"{req.first_cut_kg:,.0f}"],
                ["2nd Cut", f"{req.second_cut_kg:,.0f}"],
                ["Bottom Cut", f"{req.bottom_cut_kg:,.0f}"],
                ["Boiler / burner fuel", f"{req.boiler_fuel_kg:,.0f}"],
                ["Vapor loss", f"{req.vapor_loss_kg:,.0f}"],
                ["Water loss", f"{req.water_loss_kg:,.0f}"],
                ["Accounted total", f"{accounted:,.0f}"],
            ],
            col_widths=[120 * mm, 50 * mm],
        )
    )

    cuts = [req.first_cut_kg, req.second_cut_kg, req.bottom_cut_kg]
    cut_labels = ["1st Cut", "2nd Cut", "Bottom"]
    story.append(_section(h, "Yield Charts"))
    charts = Table(
        [[_pie(cut_labels, cuts, "Cut-wise yield"), _bars(cuts, cut_labels, "Cut volumes (kg)")]],
        colWidths=[95 * mm, 95 * mm],
    )
    story.append(charts)
    story.append(Spacer(1, 6))

    cost_total = req.fuel_cost + req.power_cost + req.labour_cost + req.other_cost
    proc = net_feed * req.processing_rate_per_kg
    story.append(_section(h, "Cost & Processing"))
    story.append(
        _table(
            [
                ["Item", "Amount ₹"],
                ["Fuel", f"{req.fuel_cost:,.2f}"],
                ["Power", f"{req.power_cost:,.2f}"],
                ["Labour", f"{req.labour_cost:,.2f}"],
                ["Other", f"{req.other_cost:,.2f}"],
                ["Process cost total", f"{cost_total:,.2f}"],
                [f"Processing charge ({net_feed:,.0f} × {req.processing_rate_per_kg})", f"{proc:,.2f}"],
                ["Process days", str(req.process_days)],
            ],
            col_widths=[120 * mm, 50 * mm],
        )
    )
    cost_vals = [req.fuel_cost, req.power_cost, req.labour_cost, req.other_cost]
    story.append(_bars(cost_vals, ["Fuel", "Power", "Labour", "Other"], "Process cost breakdown"))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Flow: Feedstock → Pre-heat → Distillation → Condensation / Cuts", small))
    story.append(Paragraph(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", small))
    doc.build(story)
    return buf.getvalue()


def build_costing_pdf(req: CostingRequest) -> bytes:
    brand, sub, h, body, small = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    story: list = []
    today = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    _header(
        story,
        brand,
        sub,
        req.title,
        [("As on", req.as_on or today), ("Batch size", _kg(req.batch_size_kg))],
    )

    def _lines(title: str, lines):
        story.append(_section(h, title))
        data = [["Description", "Unit", "Qty", "Rate ₹", "Amount ₹", "Remarks"]]
        total = 0.0
        for ln in lines:
            amt = ln.quantity * ln.rate
            total += amt
            data.append(
                [
                    ln.description,
                    ln.unit,
                    f"{ln.quantity:,.2f}",
                    f"{ln.rate:,.2f}",
                    f"{amt:,.2f}",
                    ln.remarks or "",
                ]
            )
        data.append(["TOTAL", "", "", "", f"{total:,.2f}", ""])
        story.append(_table(data, col_widths=[48 * mm, 18 * mm, 22 * mm, 22 * mm, 28 * mm, 32 * mm]))
        return total

    from app.schemas.commercial import CostingLine

    purchase_lines = req.purchase_lines or [
        CostingLine(description="Waste Oil / Feedstock", unit="kg", quantity=req.batch_size_kg, rate=45),
    ]
    opex_lines = req.opex_lines or [
        CostingLine(description="Electricity", unit="kWh", quantity=500, rate=9),
        CostingLine(description="Labour", unit="day", quantity=3, rate=2500),
        CostingLine(description="Maintenance", unit="ls", quantity=1, rate=5000),
    ]
    a_tot = _lines("A. Purchase Costing", purchase_lines)
    b_tot = _lines("B. Operating Expenses", opex_lines)
    total_cost = a_tot + b_tot
    per_kg = total_cost / req.batch_size_kg if req.batch_size_kg else 0

    story.append(_section(h, "C. Total Cost Summary"))
    story.append(
        _table(
            [
                ["Particulars", "Amount ₹"],
                ["Purchase (A)", f"{a_tot:,.2f}"],
                ["Opex (B)", f"{b_tot:,.2f}"],
                ["Total cost / batch", f"{total_cost:,.2f}"],
                ["Cost per kg", f"{per_kg:,.2f}"],
            ],
            col_widths=[120 * mm, 50 * mm],
        )
    )

    def option(name, yld, rate):
        qty = req.batch_size_kg * yld / 100.0
        rev = qty * rate
        profit = rev - total_cost
        margin = (profit / rev * 100.0) if rev else 0
        return qty, rev, profit, margin

    qa, ra, pa, ma = option(req.option_a_name, req.option_a_yield_pct, req.option_a_sell_rate)
    qb, rb, pb, mb = option(req.option_b_name, req.option_b_yield_pct, req.option_b_sell_rate)

    story.append(_section(h, "G. Profitability Summary"))
    story.append(
        _table(
            [
                ["Metric", req.option_a_name, req.option_b_name],
                ["Yield %", f"{req.option_a_yield_pct}", f"{req.option_b_yield_pct}"],
                ["Qty", f"{qa:,.0f}", f"{qb:,.0f}"],
                ["Sell rate ₹", f"{req.option_a_sell_rate}", f"{req.option_b_sell_rate}"],
                ["Revenue ₹", f"{ra:,.2f}", f"{rb:,.2f}"],
                ["Total cost ₹", f"{total_cost:,.2f}", f"{total_cost:,.2f}"],
                ["Gross profit ₹", f"{pa:,.2f}", f"{pb:,.2f}"],
                ["Margin %", f"{ma:.1f}", f"{mb:.1f}"],
            ],
            col_widths=[50 * mm, 60 * mm, 60 * mm],
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", small))
    doc.build(story)
    return buf.getvalue()


def build_mom_pdf(req: MomRequest) -> bytes:
    brand, sub, h, body, small = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    story: list = []
    _header(
        story,
        brand,
        sub,
        "MINUTES OF MEETING",
        [
            ("Date", req.meeting_date),
            ("Time", req.meeting_time or "—"),
            ("Venue", req.venue),
            ("Objective", req.objective),
        ],
    )

    story.append(_section(h, "Participants"))
    pdata = [["S.No", "Name", "Designation / Role", "Organization"]]
    for i, p in enumerate(req.participants or [], 1):
        pdata.append([str(i), p.name, p.designation or "—", p.organization or "—"])
    if len(pdata) == 1:
        pdata.append(["—", "—", "—", "—"])
    story.append(_table(pdata, col_widths=[15 * mm, 45 * mm, 55 * mm, 55 * mm]))

    story.append(_section(h, "Discussion Points"))
    for i, d in enumerate(req.discussion_points or ["General operations review"], 1):
        story.append(Paragraph(f"{i}. {d}", body))

    story.append(_section(h, "Key Recommendations"))
    rdata = [["Recommendation", "Owner", "Target"]]
    for r in req.recommendations or []:
        rdata.append([r.action, r.owner or "—", r.target_date or "—"])
    if len(rdata) == 1:
        rdata.append(["—", "—", "—"])
    story.append(_table(rdata, col_widths=[90 * mm, 40 * mm, 40 * mm]))

    story.append(_section(h, "Action Points"))
    adata = [["Action", "Responsible", "Target", "Status"]]
    for a in req.action_points or []:
        adata.append([a.action, a.owner or "—", a.target_date or "—", a.status])
    if len(adata) == 1:
        adata.append(["—", "—", "—", "Open"])
    story.append(_table(adata, col_widths=[70 * mm, 35 * mm, 30 * mm, 35 * mm]))

    story.append(Spacer(1, 16))
    story.append(
        Table(
            [["Chairperson", "Secretary", "Attendees ack."], ["____________", "____________", "____________"]],
            colWidths=[56 * mm] * 3,
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", small))
    doc.build(story)
    return buf.getvalue()
