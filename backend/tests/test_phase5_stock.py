from tests.jpeg_fixture import MINI_JPEG

GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _docs_verified(client, headers):
    start = client.post(
        "/api/v1/vehicles/entry/start",
        headers=headers,
        json={"type": "MATERIAL_RECEIVING_INWARD", "gps": GPS},
    )
    pk = start.json()["id"]
    plate = "TN 09 AB 1234"
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
        json={
            "transaction_pk": pk,
            "anpr_result_id": anpr.json()["id"],
            "confirm": True,
            "gps": GPS,
            "vehicle_number": plate,
        },
    )
    inv = client.post(
        "/api/v1/documents/invoice/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": f"Invoice No INV/5/1 Vehicle {plate} Total 1",
        },
        files={"image": ("i.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/documents/invoice/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "invoice_id": inv.json()["id"],
            "gps": GPS,
            "invoice_number": "INV/5/1",
            "vehicle_number": plate,
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
            "ocr_text": f"E-Way Bill No 121212121212 Vehicle {plate}",
        },
        files={"image": ("e.jpg", MINI_JPEG, "image/jpeg")},
    )
    conf = client.post(
        "/api/v1/documents/eway/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "eway_id": ewb.json()["id"],
            "gps": GPS,
            "eway_bill_number": "121212121212",
            "vehicle_number": plate,
        },
    )
    assert conf.json()["status"] == "DOCUMENTS_VERIFIED"
    return pk


def test_seed_masters_and_opening_balance(client):
    headers = _auth(client)
    products = client.get("/api/v1/products", headers=headers)
    assert products.status_code == 200
    codes = {p["code"] for p in products.json()}
    assert "FUEL_OIL" in codes

    units = client.get("/api/v1/storage/units", headers=headers)
    assert units.status_code == 200
    assert any(u["code"] == "T-03" for u in units.json())

    bal = client.get("/api/v1/stock/balances", headers=headers)
    assert bal.status_code == 200
    t03 = [b for b in bal.json() if b["storage_code"] == "T-03"]
    assert t03
    assert t03[0]["quantity"] == 100000.0


def test_assign_post_and_balance_math(client):
    headers = _auth(client)
    products = {p["code"]: p for p in client.get("/api/v1/products", headers=headers).json()}
    units = {u["code"]: u for u in client.get("/api/v1/storage/units", headers=headers).json()}
    product_id = products["FUEL_OIL"]["id"]
    tank_id = units["T-03"]["id"]

    pk = _docs_verified(client, headers)

    assigned = client.post(
        "/api/v1/stock/assign",
        headers=headers,
        json={
            "transaction_pk": pk,
            "product_id": product_id,
            "storage_unit_id": tank_id,
            "gps": GPS,
        },
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["product_code"] == "FUEL_OIL"
    assert assigned.json()["storage_code"] == "T-03"

    # Receiving 200,000 L (TEST_PLAN)
    posted = client.post(
        "/api/v1/stock/post",
        headers=headers,
        json={
            "transaction_pk": pk,
            "direction": "IN",
            "use_transaction_qty": False,
            "quantity": 200000,
            "unit": "L",
            "gps": GPS,
        },
    )
    assert posted.status_code == 200, posted.text
    assert posted.json()["stock_posted"] is True

    # Outward load 150,000 via second verified txn
    start = client.post(
        "/api/v1/vehicles/entry/start",
        headers=headers,
        json={"type": "MATERIAL_LOADING_OUTWARD", "gps": GPS},
    )
    pk_out = start.json()["id"]
    plate = "TN 09 AB 1234"
    anpr = client.post(
        "/api/v1/vehicles/anpr",
        headers=headers,
        data={
            "transaction_pk": pk_out,
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
        json={
            "transaction_pk": pk_out,
            "anpr_result_id": anpr.json()["id"],
            "confirm": True,
            "gps": GPS,
            "vehicle_number": plate,
        },
    )
    inv = client.post(
        "/api/v1/documents/invoice/detect",
        headers=headers,
        data={
            "transaction_pk": pk_out,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": f"Invoice No INV/5/OUT Vehicle {plate} Total 1",
        },
        files={"image": ("i.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/documents/invoice/confirm",
        headers=headers,
        json={
            "transaction_pk": pk_out,
            "invoice_id": inv.json()["id"],
            "gps": GPS,
            "invoice_number": "INV/5/OUT",
            "vehicle_number": plate,
        },
    )
    ewb = client.post(
        "/api/v1/documents/eway/detect",
        headers=headers,
        data={
            "transaction_pk": pk_out,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": f"E-Way Bill No 131313131313 Vehicle {plate}",
        },
        files={"image": ("e.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/documents/eway/confirm",
        headers=headers,
        json={
            "transaction_pk": pk_out,
            "eway_id": ewb.json()["id"],
            "gps": GPS,
            "eway_bill_number": "131313131313",
            "vehicle_number": plate,
        },
    )
    client.post(
        "/api/v1/stock/assign",
        headers=headers,
        json={"transaction_pk": pk_out, "product_id": product_id, "storage_unit_id": tank_id, "gps": GPS},
    )
    out = client.post(
        "/api/v1/stock/post",
        headers=headers,
        json={
            "transaction_pk": pk_out,
            "direction": "OUT",
            "use_transaction_qty": False,
            "quantity": 150000,
            "unit": "L",
            "gps": GPS,
        },
    )
    assert out.status_code == 200, out.text

    bal = client.get("/api/v1/stock/balances", headers=headers, params={"storage_unit_id": tank_id})
    assert bal.status_code == 200
    assert bal.json()[0]["quantity"] == 150000.0


def test_adjustment_requires_approval(client):
    headers = _auth(client)
    products = {p["code"]: p for p in client.get("/api/v1/products", headers=headers).json()}
    units = {u["code"]: u for u in client.get("/api/v1/storage/units", headers=headers).json()}
    req = client.post(
        "/api/v1/stock/adjustments",
        headers=headers,
        json={
            "product_id": products["FUEL_OIL"]["id"],
            "storage_unit_id": units["T-03"]["id"],
            "delta_quantity": -500,
            "unit": "L",
            "reason": "Dip stick variance",
            "gps": GPS,
        },
    )
    assert req.status_code == 201, req.text
    adj_id = req.json()["id"]
    decided = client.post(
        f"/api/v1/stock/adjustments/{adj_id}/decide",
        headers=headers,
        json={"approve": True, "approval_note": "Verified against dip"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "APPROVED"
