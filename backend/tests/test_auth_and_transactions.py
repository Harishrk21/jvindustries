def test_login_and_me(client):
    bad = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "wrong"})
    assert bad.status_code == 401

    ok = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"})
    assert ok.status_code == 200
    data = ok.json()
    assert "access_token" in data
    assert "OWNER_ADMIN" in data["user"]["roles"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["user_code"] == "owner"


def test_device_register_and_transaction(client):
    login = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    device = client.post(
        "/api/v1/devices/register",
        headers=headers,
        json={
            "device_uid": "test-device-001",
            "device_name": "Pixel Test",
            "platform": "android",
            "app_version": "0.1.0",
        },
    )
    assert device.status_code == 200
    device_id = device.json()["id"]

    create = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "client_transaction_id": "11111111-1111-1111-1111-111111111111",
            "type": "MATERIAL_LOADING_OUTWARD",
            "device_id": device_id,
            "gps": {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8},
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["transaction_id"].startswith("JV-")
    assert body["status"] == "DRAFT"

    # Idempotent re-create with same client id
    again = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "client_transaction_id": "11111111-1111-1111-1111-111111111111",
            "type": "MATERIAL_LOADING_OUTWARD",
            "device_id": device_id,
        },
    )
    assert again.status_code == 201
    assert again.json()["transaction_id"] == body["transaction_id"]

    dash = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dash.status_code == 200
    assert "vehicles_in" in dash.json()


def test_unauthorized_without_token(client):
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 401
