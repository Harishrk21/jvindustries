GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_repair_out_return_cycle(client):
    headers = _auth(client)
    items = client.get("/api/v1/equipment", headers=headers)
    assert items.status_code == 200
    assert any(e["code"] == "EQ-PUMP-01" for e in items.json())
    eq = next(e for e in items.json() if e["code"] == "EQ-PUMP-01")

    out = client.post(
        "/api/v1/equipment/repair-out",
        headers=headers,
        json={
            "equipment_id": eq["id"],
            "vendor_name": "ABC Motors",
            "reason": "Seal leak",
            "expected_return_date": "2026-11-05",
            "gps": GPS,
        },
    )
    assert out.status_code == 200, out.text
    assert out.json()["equipment"]["status"] == "OUT_FOR_REPAIR"
    assert out.json()["transaction_status"] == "EXIT_PENDING"
    repair_id = out.json()["repair"]["id"]

    dash = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dash.json()["equipment_out"] >= 1

    ret = client.post(
        "/api/v1/equipment/repair-return",
        headers=headers,
        json={"equipment_id": eq["id"], "repair_id": repair_id, "note": "Repaired OK", "gps": GPS},
    )
    assert ret.status_code == 200, ret.text
    assert ret.json()["equipment"]["status"] == "IN_YARD"
    assert ret.json()["repair"]["status"] == "RETURNED"


def test_disposal_requires_approval(client):
    headers = _auth(client)
    # create disposable unit
    created = client.post(
        "/api/v1/equipment",
        headers=headers,
        json={"code": "EQ-SCRAP-99", "name": "Scrap Motor", "category": "MOTOR"},
    )
    assert created.status_code == 201, created.text
    eq_id = created.json()["id"]

    req = client.post(
        "/api/v1/equipment/disposal",
        headers=headers,
        json={"equipment_id": eq_id, "reason": "Beyond economical repair", "gps": GPS},
    )
    assert req.status_code == 200, req.text
    assert req.json()["disposal"]["status"] == "PENDING"
    assert req.json()["transaction_status"] == "APPROVAL_PENDING"
    disposal_id = req.json()["disposal"]["id"]

    notes = client.get("/api/v1/notifications", headers=headers)
    assert any(n["category"] == "APPROVAL" and "disposal" in n["title"].lower() for n in notes.json())

    ok = client.post(
        "/api/v1/equipment/disposal/decide",
        headers=headers,
        json={
            "disposal_id": disposal_id,
            "approve": True,
            "approval_note": "Owner approved scrap",
            "gps": GPS,
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["equipment"]["status"] == "DISPOSED"
    assert ok.json()["disposal"]["status"] == "APPROVED"
