"""Phase C — ops reports smoke (stock / tank / customer / jobwork / audit)."""


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_ops_stock_and_tank(client):
    headers = _auth(client)
    stock = client.get("/api/v1/reports/ops/stock?period=monthly", headers=headers)
    assert stock.status_code == 200, stock.text
    body = stock.json()
    assert body["title"]
    assert "Opening" in body["columns"]
    assert body["row_count"] >= 1  # seeded T-03 opening

    tank = client.get("/api/v1/reports/ops/tank", headers=headers)
    assert tank.status_code == 200, tank.text
    assert tank.json()["row_count"] >= 1
    assert "Balance" in tank.json()["columns"]


def test_ops_customer_jobwork_audit(client):
    headers = _auth(client)
    cust = client.get("/api/v1/reports/ops/customer?period=monthly", headers=headers)
    assert cust.status_code == 200, cust.text
    assert "Customer" in cust.json()["columns"]

    jw = client.get("/api/v1/reports/ops/jobwork?period=monthly", headers=headers)
    assert jw.status_code == 200, jw.text
    assert "Loss %" in jw.json()["columns"]

    audit = client.get("/api/v1/reports/ops/audit?period=monthly", headers=headers)
    assert audit.status_code == 200, audit.text
    assert "Action" in audit.json()["columns"]


def test_ops_export_xlsx(client):
    headers = _auth(client)
    res = client.get("/api/v1/reports/ops/tank/export?format=xlsx&period=monthly", headers=headers)
    assert res.status_code == 200, res.text
    assert "spreadsheetml" in res.headers.get("content-type", "")
    assert len(res.content) > 100
