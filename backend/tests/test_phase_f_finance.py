"""Phase F — advances, settlement calc, GST reconcile smoke."""

from app.services.finance_service import compute_settlement_amounts


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_compute_settlement_amounts():
    amounts = compute_settlement_amounts(
        feedstock_kg=100000,
        bleaching_return_kg=10000,
        burner_fuel_kg=5000,
        burner_rate=50,
        retail_kg=0,
        retail_rate=0,
        processing_rate_per_kg=8.4,
        gst_percent=18,
        advance_paid=100000,
        advance_received_back=20000,
    )
    # net feed 90000 * 8.4 = 756000; gst 136080; deductions 250000; net_proc = 642080; + adv bal 80000
    assert amounts["processing_base"] == 756000.0
    assert amounts["gst_amount"] == 136080.0
    assert amounts["deductions_total"] == 250000.0
    assert amounts["net_processing"] == 642080.0
    assert amounts["payable"] == 722080.0


def test_advance_settlement_gst_flow(client):
    headers = _auth(client)

    custs = client.get("/api/v1/customers", headers=headers)
    assert custs.status_code == 200, custs.text
    customers = custs.json()
    if not customers:
        created = client.post(
            "/api/v1/customers",
            headers=headers,
            json={"code": "FIN-T1", "name": "Finance Test Cust", "gstin": "29AAAAA0000A1Z5"},
        )
        assert created.status_code in (200, 201), created.text
        customer_id = created.json()["id"]
    else:
        customer_id = customers[0]["id"]

    adv = client.post(
        "/api/v1/finance/advances",
        headers=headers,
        json={
            "customer_id": customer_id,
            "entry_date": "2026-04-01",
            "direction": "PAID",
            "amount": 50000,
            "reference": "UTR-TEST-1",
        },
    )
    assert adv.status_code == 200, adv.text
    assert adv.json()["amount"] == 50000

    bal = client.get(f"/api/v1/finance/advances/balance?customer_id={customer_id}", headers=headers)
    assert bal.status_code == 200, bal.text
    assert bal.json()["paid_total"] >= 50000
    assert bal.json()["balance"] >= 50000

    settle = client.post(
        "/api/v1/finance/settlements",
        headers=headers,
        json={
            "customer_id": customer_id,
            "period_from": "2026-03-01",
            "period_to": "2026-08-31",
            "auto_fill_yard": True,
            "feedstock_kg": 100000,
            "delivery_kg": 80000,
            "bleaching_return_kg": 5000,
            "burner_fuel_kg": 2000,
            "burner_rate": 55,
            "processing_rate_per_kg": 8.4,
            "gst_percent": 18,
        },
    )
    assert settle.status_code == 200, settle.text
    body = settle.json()
    assert body["report_no"].startswith("SE-")
    assert body["advance_paid"] >= 50000
    assert body["payable"] != 0
    settlement_id = body["id"]

    pdf = client.post(f"/api/v1/finance/settlements/{settlement_id}/supply-expense.pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content[:4] == b"%PDF"

    fin = client.post(f"/api/v1/finance/settlements/{settlement_id}/finalize", headers=headers)
    assert fin.status_code == 200, fin.text
    assert fin.json()["finalized"] is True

    gst = client.post(
        "/api/v1/finance/gst/reconcile?period_from=2026-01-01&period_to=2026-12-31",
        headers=headers,
    )
    assert gst.status_code == 200, gst.text
    assert "run_id" in gst.json()
    assert "rows" in gst.json()
