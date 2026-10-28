"""DoD gap coverage — geofence config, PDF variants, users API."""


def _auth(client, user="owner", password="Owner@123"):
    login = client.post("/api/v1/auth/login", json={"user_id": user, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_geofence_config_get_put(client):
    headers = _auth(client)
    got = client.get("/api/v1/geofence/config", headers=headers)
    assert got.status_code == 200
    body = got.json()
    assert "lat" in body and "radius_m" in body

    put = client.put(
        "/api/v1/geofence/config",
        headers=headers,
        json={
            "lat": 13.1,
            "lon": 80.3,
            "radius_m": 250,
            "max_accuracy_m": 40,
        },
    )
    assert put.status_code == 200
    assert put.json()["source"] == "database"
    assert put.json()["radius_m"] == 250


def test_pdf_variant_query(client):
    headers = _auth(client)
    # create a draft via sync so we have a txn pk
    cid = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
    push = client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={"drafts": [{"client_transaction_id": cid, "type": "OTHER_MOVEMENT"}]},
    )
    assert push.status_code == 200
    pk = push.json()["results"][0]["transaction_pk"]

    for variant in ("customer", "internal"):
        pdf = client.get(f"/api/v1/pdfs/transaction/{pk}?variant={variant}", headers=headers)
        assert pdf.status_code == 200
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content[:4] == b"%PDF"


def test_users_list_and_create(client):
    headers = _auth(client)
    roles = client.get("/api/v1/users/roles", headers=headers)
    assert roles.status_code == 200
    assert "SECURITY" in roles.json()

    listed = client.get("/api/v1/users", headers=headers)
    assert listed.status_code == 200
    assert any(u["user_code"] == "owner" for u in listed.json())

    created = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "user_code": "gate1",
            "full_name": "Gate One",
            "password": "Gate@12345",
            "role_codes": ["SECURITY"],
        },
    )
    assert created.status_code == 201
    assert created.json()["user_code"] == "gate1"
