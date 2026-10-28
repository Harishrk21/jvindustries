from app.ai.density_recognition import get_density_recognition_service
from app.ai.vehicle_recognition import get_vehicle_recognition_service
from app.ai.weighbridge_ocr import get_weighbridge_ocr_service
from app.services.calculations import compute_calculated_litres, compute_net_kg


def test_plate_extracted_from_real_ocr_text_not_invented():
    svc = get_vehicle_recognition_service()
    empty = svc.recognize_from_ocr(ocr_text="no plate here")
    assert empty.failed is True
    assert empty.value is None

    hit = svc.recognize_from_ocr(ocr_text="Lorry TN 09 AB 1234 gate 2")
    assert hit.failed is False
    assert hit.value == "TN 09 AB 1234"
    assert hit.provider != "mock"


def test_two_line_indian_yellow_plate():
    """Decorated truck plates often OCR as two lines: AP28 / W4882."""
    from app.ai.vehicle_recognition import extract_plate_candidates

    svc = get_vehicle_recognition_service()
    two_line = svc.recognize_from_ocr(ocr_text="ROAD KING\nAP28\nW4882\nPadmavathi")
    assert two_line.failed is False
    assert two_line.value.replace(" ", "") == "AP28W4882"

    compact = svc.recognize_from_ocr(ocr_text="noise AP28W4882 bumper")
    assert compact.failed is False
    assert compact.value.replace(" ", "") == "AP28W4882"

    cands = extract_plate_candidates("AP 28\nW 4882")
    assert any(p.replace(" ", "") == "AP28W4882" for p, _ in cands)

    # Series letter on first line (RJ 09 G / 4017)
    rj = svc.recognize_from_ocr(ocr_text="I RJ09G |\n| 4017 |")
    assert rj.failed is False
    assert rj.value.replace(" ", "") == "RJ09G4017"

    # Clear device-OCR lines (cloud Groq vision is primary for messy photos)
    ap_clear = svc.recognize_from_ocr(ocr_text="E AP28\nW4882")
    assert ap_clear.failed is False
    assert ap_clear.value.replace(" ", "") == "AP28W4882"


def test_weight_and_litres_sample_business_case():
    ocr = get_weighbridge_ocr_service().recognize_from_ocr(ocr_text="TRUWEIGH\nGROSS\n45,110 KG")
    assert ocr.failed is False
    assert ocr.value_kg == 45110.0

    tare = get_weighbridge_ocr_service().recognize_from_ocr(ocr_text="TARE 11820 kg")
    assert tare.value_kg == 11820.0

    net = compute_net_kg(tare_kg=11820, gross_kg=45110)
    assert net == 33290.0

    dens = get_density_recognition_service().recognize_from_ocr(
        ocr_text="Density 0.845 kg/L Temperature 30°C"
    )
    assert dens.failed is False
    assert dens.density_kg_per_l == 0.845
    assert dens.temperature_c == 30.0

    litres = compute_calculated_litres(net_kg=net, density_kg_per_l=0.845)
    assert litres == 39396.45


def test_gross_less_than_tare_rejected():
    try:
        compute_net_kg(tare_kg=20000, gross_kg=15000)
        assert False, "expected error"
    except ValueError as exc:
        assert "Gross" in str(exc)
