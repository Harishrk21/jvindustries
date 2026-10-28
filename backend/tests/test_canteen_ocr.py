from app.ai.canteen_ocr import parse_canteen_ocr


def test_extracts_rice_dal_oil():
    ocr = parse_canteen_ocr(
        "Bill No CN/88 Supplier Fresh Foods "
        "Rice 50 kg Dal 25 kg Oil 10 L Total 12500"
    )
    assert ocr.failed is False
    codes = {ln.item_code: ln.quantity for ln in ocr.lines}
    assert codes["RICE"] == 50
    assert codes["DAL"] == 25
    assert codes["OIL"] == 10
    assert ocr.invoice_number is not None


def test_empty_fails():
    ocr = parse_canteen_ocr("   ")
    assert ocr.failed is True
