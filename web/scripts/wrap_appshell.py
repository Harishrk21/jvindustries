from pathlib import Path

root = Path(__file__).resolve().parents[1] / "src" / "pages"

pages = {
    "VehicleEntryPage.tsx": None,  # special
    "WeighmentPage.tsx": ("Weighbridge", "Live TRUWEIGH evidence · server net & litres"),
    "DocumentsPage.tsx": ("Documents", "Live invoice · E-Way · vehicle match"),
    "StockPage.tsx": ("Storage & Stock", "Tanks · barrels · IBC · ledger balances"),
    "JobWorkPage.tsx": ("Job Work & OTP", "Batches · loss limits · WhatsApp OTP"),
    "AlertsPage.tsx": ("Alerts & PDFs", "WhatsApp log · management inbox · downloads"),
    "EquipmentPage.tsx": ("Equipment", "Repair · return · transfer · disposal"),
    "CanteenPage.tsx": ("Canteen", "Purchase OCR · confirm · stock"),
    "ReportsPage.tsx": ("Reports", "Daily · monthly · custom · PDF/Excel"),
}

for name, meta in pages.items():
    path = root / name
    text = path.read_text(encoding="utf-8")
    if 'from "../components/AppShell"' not in text:
        lines = text.splitlines(True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import "):
                insert_at = i + 1
        lines.insert(insert_at, 'import { AppShell } from "../components/AppShell";\n')
        text = "".join(lines)

    start = text.find('<div className="app-shell">')
    main = text.find('<main className="page stack"', start)
    if start < 0 or main < 0:
        print("SKIP structure", name)
        continue
    main_gt = text.find(">", main) + 1

    if name == "VehicleEntryPage.tsx":
        open_shell = (
            '<AppShell\n'
            '      title="Vehicle Entry"\n'
            '      subtitle={txn ? `${txn.transaction_id} · ${txn.status}` : "New inbound / loading movement"}\n'
            '      backTo="/"\n'
            "      wide\n"
            "    >"
        )
    else:
        title, subtitle = meta
        open_shell = f'<AppShell title="{title}" subtitle="{subtitle}" backTo="/more" wide>'

    text = text[:start] + open_shell + text[main_gt:]

    old_close = "</main>\n    </div>"
    if old_close not in text:
        print("CLOSE FAIL", name)
        continue
    text = text.replace(old_close, "</AppShell>", 1)
    path.write_text(text, encoding="utf-8")
    print("OK", name)

print("done")
