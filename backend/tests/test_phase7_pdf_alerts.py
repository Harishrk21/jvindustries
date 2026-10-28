GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_excess_loss_creates_notification(client):
    headers = _auth(client)
    products = {p["code"]: p for p in client.get("/api/v1/products", headers=headers).json()}
    created = client.post(
        "/api/v1/job-work/batches",
        headers=headers,
        json={
            "batch_code": "JW-ALERT-1",
            "product_id": products["FUEL_OIL"]["id"],
            "gps": GPS,
        },
    )
    client.post(
        "/api/v1/job-work/batches/quantities",
        headers=headers,
        json={
            "batch_id": created.json()["id"],
            "qty_in": 100000,
            "qty_out": 97500,
            "gps": GPS,
        },
    )
    notes = client.get("/api/v1/notifications", headers=headers)
    assert notes.status_code == 200
    assert any(n["category"] == "LOSS" for n in notes.json())


def test_transaction_pdf_bytes(client):
    headers = _auth(client)
    products = {p["code"]: p for p in client.get("/api/v1/products", headers=headers).json()}
    created = client.post(
        "/api/v1/job-work/batches",
        headers=headers,
        json={"batch_code": "JW-PDF-1", "product_id": products["FUEL_OIL"]["id"], "gps": GPS},
    )
    pk = created.json()["transaction_pk"]
    pdf = client.get(f"/api/v1/pdfs/transaction/{pk}", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"


def test_manual_alert_and_whatsapp_log(client):
    headers = _auth(client)
    alert = client.post(
        "/api/v1/notifications/alert",
        headers=headers,
        json={
            "title": "Yard check",
            "body": "Supervisor walkthrough due",
            "category": "SYSTEM",
            "severity": "INFO",
            "send_whatsapp": True,
        },
    )
    assert alert.status_code == 201, alert.text
    msgs = client.get("/api/v1/whatsapp/messages", headers=headers)
    assert msgs.status_code == 200
    assert len(msgs.json()) >= 1
