"""Phase D — branded weighment slip + gate pass PDFs."""

from tests.jpeg_fixture import MINI_JPEG

GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _txn_with_gate(client, headers):
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
            "ocr_text": "TN 09 ZZ 9999",
        },
        files={"image": ("e.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/vehicles/anpr/confirm",
        headers=headers,
        json={"transaction_pk": pk, "anpr_result_id": anpr.json()["id"], "confirm": True, "gps": GPS},
    )
    client.post(
        "/api/v1/vehicles/driver",
        headers=headers,
        json={
            "transaction_pk": pk,
            "driver_name": "Ravi",
            "driver_mobile": "9876543210",
            "vehicle_type": "Tanker",
            "transporter_name": "JV Fleet",
        },
    )
    products = client.get("/api/v1/products", headers=headers).json()
    units = client.get("/api/v1/storage/units", headers=headers).json()
    client.post(
        "/api/v1/stock/assign",
        headers=headers,
        json={
            "transaction_pk": pk,
            "product_id": products[0]["id"],
            "storage_unit_id": units[0]["id"],
            "gps": GPS,
        },
    )
    gp = client.post(
        "/api/v1/gate-passes",
        headers=headers,
        json={
            "transaction_pk": pk,
            "pass_type": "OUTWARD_LOADING",
            "direction": "OUTWARD",
            "purpose": "OUTWARD",
            "material_description": products[0]["name"],
            "from_location": "JV yard",
            "to_location": "Customer site",
            "vehicle_checked": True,
            "goods_verified": True,
            "documents_verified": False,
        },
    )
    assert gp.status_code == 201, gp.text
    return pk, gp.json()["gate_pass_number"]


def test_gate_pass_pdf_branded(client):
    headers = _auth(client)
    pk, gp_no = _txn_with_gate(client, headers)
    res = client.get(f"/api/v1/pdfs/gate-pass/{pk}", headers=headers)
    assert res.status_code == 200, res.text
    assert res.content[:4] == b"%PDF"
    assert len(res.content) > 1500
    assert "pdf" in res.headers.get("content-type", "")
    assert gp_no in (res.headers.get("content-disposition") or "")


def test_weighment_slip_pdf_branded(client):
    headers = _auth(client)
    pk, _ = _txn_with_gate(client, headers)
    # Set weights directly via confirm path after tare/gross for outward
    tare = client.post(
        "/api/v1/weighments/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "kind": "TARE",
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "10000 KG",
        },
        files={"image": ("t.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/weighments/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "kind": "TARE",
            "photo_id": tare.json()["photo_id"],
            "confirmed_weight_kg": 10000,
            "gps": GPS,
            "after_tare_mode": "LOADING",
        },
    )
    gross = client.post(
        "/api/v1/weighments/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "kind": "GROSS",
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "25000 KG",
        },
        files={"image": ("g.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/weighments/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "kind": "GROSS",
            "photo_id": gross.json()["photo_id"],
            "confirmed_weight_kg": 25000,
            "gps": GPS,
        },
    )

    res = client.get(f"/api/v1/pdfs/transaction/{pk}?variant=customer", headers=headers)
    assert res.status_code == 200, res.text
    assert res.content[:4] == b"%PDF"
    assert "weighment-slip" in (res.headers.get("content-disposition") or "")
    assert len(res.content) > 2000

    alias = client.get(f"/api/v1/pdfs/weighment-slip/{pk}", headers=headers)
    assert alias.status_code == 200
    assert alias.content[:4] == b"%PDF"
