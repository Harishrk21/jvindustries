from tests.jpeg_fixture import MINI_JPEG

GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _txn_with_vehicle(client, headers, plate="TN 09 AB 1234"):
    start = client.post(
        "/api/v1/vehicles/entry/start",
        headers=headers,
        json={"type": "MATERIAL_LOADING_OUTWARD", "gps": GPS},
    )
    pk = start.json()["id"]
    anpr = client.post(
        "/api/v1/vehicles/anpr",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": f"Vehicle {plate}",
        },
        files={"image": ("e.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/vehicles/anpr/confirm",
        headers=headers,
        json={"transaction_pk": pk, "anpr_result_id": anpr.json()["id"], "confirm": True, "gps": GPS},
    )
    return pk, plate


def test_invoice_eway_match_verifies(client):
    headers = _auth(client)
    pk, plate = _txn_with_vehicle(client, headers)

    inv = client.post(
        "/api/v1/documents/invoice/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": f"Tax Invoice No INV/2026/001 Date 01/10/2026 GSTIN 33AAAAA0000A1Z5 Vehicle {plate} Total 100000",
        },
        files={"image": ("inv.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert inv.status_code == 200, inv.text
    assert inv.json()["fields"]["invoice_number"] is not None

    conf_inv = client.post(
        "/api/v1/documents/invoice/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "invoice_id": inv.json()["id"],
            "gps": GPS,
            "invoice_number": inv.json()["fields"]["invoice_number"],
            "vehicle_number": plate,
        },
    )
    assert conf_inv.status_code == 200, conf_inv.text
    assert conf_inv.json()["invoice_confirmed"] is True

    ewb = client.post(
        "/api/v1/documents/eway/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": f"E-Way Bill No 123456789012 Vehicle {plate} From Chennai To Coimbatore",
        },
        files={"image": ("ewb.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert ewb.status_code == 200, ewb.text

    conf_ewb = client.post(
        "/api/v1/documents/eway/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "eway_id": ewb.json()["id"],
            "gps": GPS,
            "eway_bill_number": ewb.json()["fields"]["eway_bill_number"] or "123456789012",
            "vehicle_number": plate,
        },
    )
    assert conf_ewb.status_code == 200, conf_ewb.text
    assert conf_ewb.json()["match_status"] == "MATCH"
    assert conf_ewb.json()["status"] == "DOCUMENTS_VERIFIED"


def test_vehicle_mismatch_needs_approval(client):
    headers = _auth(client)
    pk, _ = _txn_with_vehicle(client, headers, plate="TN 09 AB 1234")

    inv = client.post(
        "/api/v1/documents/invoice/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "Invoice No INV99 Vehicle TN 01 ZZ 9999 Total 5000",
        },
        files={"image": ("inv.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/documents/invoice/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "invoice_id": inv.json()["id"],
            "gps": GPS,
            "invoice_number": "INV99",
            "vehicle_number": "TN 01 ZZ 9999",
        },
    )

    ewb = client.post(
        "/api/v1/documents/eway/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "E-Way Bill No 999888777666 Vehicle TN 01 ZZ 9999",
        },
        files={"image": ("ewb.jpg", MINI_JPEG, "image/jpeg")},
    )
    conf = client.post(
        "/api/v1/documents/eway/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "eway_id": ewb.json()["id"],
            "gps": GPS,
            "eway_bill_number": "999888777666",
            "vehicle_number": "TN 01 ZZ 9999",
        },
    )
    assert conf.status_code == 200
    assert conf.json()["match_status"] == "MISMATCH"
    assert conf.json()["status"] == "APPROVAL_PENDING"

    approved = client.post(
        "/api/v1/documents/mismatch/approve",
        headers=headers,
        json={
            "transaction_pk": pk,
            "verification_id": conf.json()["verification_id"],
            "approval_note": "Verified physical documents — temporary trailer change",
            "gps": GPS,
        },
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "DOCUMENTS_VERIFIED"
