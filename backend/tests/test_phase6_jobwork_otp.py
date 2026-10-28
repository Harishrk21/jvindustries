GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_jobwork_excess_loss_needs_approval(client):
    headers = _auth(client)
    products = {p["code"]: p for p in client.get("/api/v1/products", headers=headers).json()}
    product_id = products["FUEL_OIL"]["id"]

    created = client.post(
        "/api/v1/job-work/batches",
        headers=headers,
        json={
            "batch_code": "JW-TEST-1",
            "product_id": product_id,
            "customer_name": "ABC Industries",
            "customer_mobile": "9876543210",
            "unit": "KG",
            "gps": GPS,
        },
    )
    assert created.status_code == 201, created.text
    batch_id = created.json()["id"]

    qty = client.post(
        "/api/v1/job-work/batches/quantities",
        headers=headers,
        json={"batch_id": batch_id, "qty_in": 100000, "qty_out": 97500, "gps": GPS},
    )
    assert qty.status_code == 200, qty.text
    loss = qty.json()["loss"]
    assert loss is not None
    assert loss["loss_percent"] == 2.5
    assert loss["requires_approval"] is True
    assert loss["excess_percent"] == 0.5

    approved = client.post(
        "/api/v1/job-work/loss/approve",
        headers=headers,
        json={"loss_id": loss["id"], "approval_note": "Owner accepted excess 0.5%", "gps": GPS},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "CLOSED"
    assert approved.json()["loss"]["approved"] is True


def test_whatsapp_otp_send_preview_and_verify(client):
    headers = _auth(client)
    products = {p["code"]: p for p in client.get("/api/v1/products", headers=headers).json()}
    created = client.post(
        "/api/v1/job-work/batches",
        headers=headers,
        json={
            "batch_code": "JW-OTP-1",
            "product_id": products["FUEL_OIL"]["id"],
            "customer_mobile": "9876543210",
            "gps": GPS,
        },
    )
    pk = created.json()["transaction_pk"]

    sent = client.post(
        "/api/v1/otp/send",
        headers=headers,
        json={
            "transaction_pk": pk,
            "customer_mobile": "9876543210",
            "customer_name": "ABC Industries",
            "gps": GPS,
        },
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["otp_preview"]  # mock/dev preview for perfect working
    assert sent.json()["whatsapp_delivery_status"] in {"MOCKED", "SENT"}
    code = sent.json()["otp_preview"]

    verified = client.post(
        "/api/v1/otp/verify",
        headers=headers,
        json={
            "transaction_pk": pk,
            "otp_id": sent.json()["otp_id"],
            "otp_code": code,
            "gps": GPS,
        },
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["verified"] is True
    assert verified.json()["transaction_status"] == "CUSTOMER_CONFIRMED"
