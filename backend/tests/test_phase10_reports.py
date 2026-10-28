def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_daily_summary_and_exports(client):
    headers = _auth(client)
    summary = client.get("/api/v1/reports/summary", headers=headers, params={"period": "daily"})
    assert summary.status_code == 200, summary.text
    assert summary.json()["report_type"] == "DAILY"
    assert "transactions" in summary.json()["summary"]

    pdf = client.get("/api/v1/reports/export", headers=headers, params={"period": "daily", "format": "pdf"})
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"

    xlsx = client.get("/api/v1/reports/export", headers=headers, params={"period": "monthly", "format": "xlsx"})
    assert xlsx.status_code == 200
    assert xlsx.content[:2] == b"PK"

    exports = client.get("/api/v1/reports/exports", headers=headers)
    assert exports.status_code == 200
    assert len(exports.json()) >= 2
