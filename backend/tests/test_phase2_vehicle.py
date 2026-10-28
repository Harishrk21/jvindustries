from tests.jpeg_fixture import MINI_JPEG

GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}


def _auth(client):
    login = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _anpr(client, headers, pk, ocr_text: str):
    return client.post(
        "/api/v1/vehicles/anpr",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": ocr_text,
        },
        files={"image": ("entry.jpg", MINI_JPEG, "image/jpeg")},
    )


def test_vehicle_entry_ocr_anpr_gate_exit_flow(client):
    headers = _auth(client)

    start = client.post(
        "/api/v1/vehicles/entry/start",
        headers=headers,
        json={
            "client_transaction_id": "22222222-2222-2222-2222-222222222222",
            "type": "MATERIAL_LOADING_OUTWARD",
            "gps": GPS,
        },
    )
    assert start.status_code == 201, start.text
    txn = start.json()
    assert txn["status"] == "ENTRY_STARTED"
    pk = txn["id"]

    bad_gps = client.post(
        "/api/v1/vehicles/anpr",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": "12.0",
            "gps_lon": "80.0",
            "gps_accuracy_m": "8",
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "TN 09 AB 1234",
        },
        files={"image": ("entry.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert bad_gps.status_code == 403

    anpr = _anpr(client, headers, pk, "Vehicle plate TN 09 AB 1234")
    assert anpr.status_code == 200, anpr.text
    body = anpr.json()
    assert body["provider"] == "ocr_text_parser"
    assert body["vehicle_number"] == "TN 09 AB 1234"
    assert body["photo_id"]

    confirm = client.post(
        "/api/v1/vehicles/anpr/confirm",
        headers=headers,
        json={"transaction_pk": pk, "anpr_result_id": body["id"], "confirm": True, "gps": GPS},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "VEHICLE_VERIFIED"

    driver = client.post(
        "/api/v1/vehicles/driver",
        headers=headers,
        json={
            "transaction_pk": pk,
            "driver_name": "Ravi Kumar",
            "driver_mobile": "9876543210",
            "transporter_name": "ABC Transport",
        },
    )
    assert driver.status_code == 200
    assert driver.json()["status"] == "AWAITING_TARE"

    gp = client.post(
        "/api/v1/gate-passes",
        headers=headers,
        json={"transaction_pk": pk, "pass_type": "OUTWARD_LOADING", "direction": "INWARD"},
    )
    assert gp.status_code == 201, gp.text
    assert gp.json()["gate_pass_number"].startswith("JV/GP/")

    exit_det = client.post(
        "/api/v1/vehicles/exit/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "Exit TN 09 AB 1234",
        },
        files={"image": ("exit.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert exit_det.status_code == 200, exit_det.text

    exit_ok = client.post(
        "/api/v1/vehicles/exit/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "anpr_result_id": exit_det.json()["id"],
            "gps": GPS,
            "complete_transaction": True,
        },
    )
    assert exit_ok.status_code == 200, exit_ok.text
    assert exit_ok.json()["status"] == "COMPLETED"


def test_anpr_fails_without_plate_in_ocr(client):
    headers = _auth(client)
    start = client.post(
        "/api/v1/vehicles/entry/start",
        headers=headers,
        json={"type": "MATERIAL_RECEIVING_INWARD", "gps": GPS},
    )
    pk = start.json()["id"]
    anpr = _anpr(client, headers, pk, "blurry image no readable plate")
    assert anpr.status_code == 200
    assert anpr.json()["status"] == "FAILED"
    assert anpr.json()["vehicle_number"] is None

    bad = client.post(
        "/api/v1/vehicles/anpr/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "anpr_result_id": anpr.json()["id"],
            "confirm": True,
            "vehicle_number": "TN 01 ZZ 9999",
            "gps": GPS,
        },
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/v1/vehicles/anpr/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "anpr_result_id": anpr.json()["id"],
            "confirm": True,
            "vehicle_number": "TN 01 ZZ 9999",
            "manual_reason": "OCR failed — plate read visually from vehicle",
            "gps": GPS,
        },
    )
    assert ok.status_code == 200
    assert ok.json()["vehicle_number"] == "TN 01 ZZ 9999"
