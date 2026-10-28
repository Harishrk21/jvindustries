from app.ai.eway_ocr import get_eway_ocr_service
from app.ai.invoice_ocr import get_invoice_ocr_service
from app.services.vehicle_match import compare_vehicles


def test_invoice_parser_extracts_real_fields():
    ocr = get_invoice_ocr_service().recognize_from_ocr(
        ocr_text="TAX INVOICE No INV/2026/88 Date 12/10/2026 GSTIN 33AAAAA0000A1Z5 HSN 2710 Qty 100 kg Total 25000 TN 09 AB 1234"
    )
    assert ocr.failed is False
    assert ocr.fields["invoice_number"] is not None
    assert ocr.fields["gstin"] is not None
    assert ocr.fields["vehicle_number"] == "TN 09 AB 1234"


def test_eway_parser_and_match():
    ocr = get_eway_ocr_service().recognize_from_ocr(
        ocr_text="E-Way Bill No 123456789012 From Chennai To Madurai Vehicle TN 09 AB 1234"
    )
    assert ocr.failed is False
    assert ocr.fields["eway_bill_number"] == "123456789012"

    match = compare_vehicles(
        anpr_vehicle="TN 09 AB 1234",
        invoice_vehicle="TN09AB1234",
        eway_vehicle="TN 09 AB 1234",
    )
    assert match.match_status == "MATCH"

    bad = compare_vehicles(
        anpr_vehicle="TN 09 AB 1234",
        invoice_vehicle="TN 01 ZZ 9999",
        eway_vehicle="TN 01 ZZ 9999",
    )
    assert bad.match_status == "MISMATCH"
