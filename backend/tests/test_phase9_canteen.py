from tests.jpeg_fixture import MINI_JPEG

GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_canteen_purchase_ocr_stock(client):
    headers = _auth(client)
    items = client.get("/api/v1/canteen/items", headers=headers)
    assert items.status_code == 200
    assert {i["code"] for i in items.json()} >= {"RICE", "DAL", "OIL"}

    before = {b["item_code"]: b["quantity"] for b in client.get("/api/v1/canteen/balances", headers=headers).json()}

    start = client.post(
        "/api/v1/canteen/purchase/start",
        headers=headers,
        data={
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
        },
    )
    assert start.status_code == 201, start.text
    pk = start.json()["id"]

    det = client.post(
        "/api/v1/canteen/purchase/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "Invoice No CN/2026/1 Supplier Fresh Foods Rice 50 kg Dal 25 kg Oil 10 L Total 18000",
        },
        files={"image": ("inv.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert det.status_code == 200, det.text
    assert len(det.json()["lines"]) == 3

    conf = client.post(
        "/api/v1/canteen/purchase/confirm",
        headers=headers,
        json={
            "purchase_id": det.json()["purchase_id"],
            "transaction_pk": pk,
            "gps": GPS,
            "invoice_number": det.json()["invoice_number"] or "CN/2026/1",
            "supplier_name": "Fresh Foods",
            "lines": det.json()["lines"],
        },
    )
    assert conf.status_code == 200, conf.text
    assert conf.json()["status"] == "CONFIRMED"
    assert conf.json()["stock_posted"] is True
    assert conf.json()["photo_id"]  # original retained via photo_id

    after = {b["item_code"]: b["quantity"] for b in client.get("/api/v1/canteen/balances", headers=headers).json()}
    assert after["RICE"] == before.get("RICE", 0) + 50
    assert after["DAL"] == before.get("DAL", 0) + 25
    assert after["OIL"] == before.get("OIL", 0) + 10
