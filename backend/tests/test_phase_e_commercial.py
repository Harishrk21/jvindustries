"""Phase E — commercial PDF statements smoke."""


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_supply_expense_pdf(client):
    headers = _auth(client)
    res = client.post(
        "/api/v1/commercial/supply-expense.pdf",
        headers=headers,
        json={
            "customer_name": "SAI PETRO",
            "customer_address": "Andhra Pradesh",
            "report_no": "SE-TEST-1",
            "period_from": "2026-03-24",
            "period_to": "2026-08-20",
            "feedstock_kg": 395630,
            "delivery_kg": 331090,
            "bleaching_return_kg": 24000,
            "burner_fuel_kg": 21000,
            "burner_rate": 55,
            "processing_rate_per_kg": 8.4,
            "gst_percent": 18,
            "advance_paid": 50000,
        },
    )
    assert res.status_code == 200, res.text
    assert res.content[:4] == b"%PDF"
    assert len(res.content) > 2000


def test_distillation_costing_mom_pdfs(client):
    headers = _auth(client)

    d = client.post(
        "/api/v1/commercial/distillation.pdf",
        headers=headers,
        json={
            "report_no": "DR-TEST",
            "period_from": "2026-03-01",
            "period_to": "2026-03-31",
            "customer_name": "Test",
            "total_feed_kg": 400000,
            "bleaching_return_kg": 20000,
            "first_cut_kg": 180000,
            "second_cut_kg": 90000,
            "bottom_cut_kg": 70000,
            "boiler_fuel_kg": 20000,
            "vapor_loss_kg": 10000,
            "water_loss_kg": 10000,
            "fuel_cost": 100000,
            "power_cost": 40000,
            "labour_cost": 50000,
            "other_cost": 10000,
        },
    )
    assert d.status_code == 200, d.text
    assert d.content[:4] == b"%PDF"

    c = client.post(
        "/api/v1/commercial/costing.pdf",
        headers=headers,
        json={"batch_size_kg": 60000},
    )
    assert c.status_code == 200, c.text
    assert c.content[:4] == b"%PDF"

    m = client.post(
        "/api/v1/commercial/minutes.pdf",
        headers=headers,
        json={
            "meeting_date": "2026-10-16",
            "objective": "Review",
            "participants": [{"name": "Owner", "organization": "JV"}],
            "action_points": [{"action": "Follow up rates", "owner": "Commercial", "status": "Open"}],
        },
    )
    assert m.status_code == 200, m.text
    assert m.content[:4] == b"%PDF"
