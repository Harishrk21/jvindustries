"""Phase B — products / parties / calibration masters smoke."""

from tests.jpeg_fixture import MINI_JPEG  # noqa: F401 — keep package import style consistent


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_seeded_masters_and_calibration(client):
    headers = _auth(client)

    products = client.get("/api/v1/products", headers=headers)
    assert products.status_code == 200
    codes = {p["code"] for p in products.json()}
    assert "FUEL_OIL" in codes

    units = client.get("/api/v1/storage/units", headers=headers)
    assert units.status_code == 200
    ucodes = {u["code"] for u in units.json()}
    assert "T-03" in ucodes

    customers = client.get("/api/v1/customers", headers=headers)
    assert customers.status_code == 200
    cust = next(c for c in customers.json() if c["code"] == "CUST-ABC")
    assert cust.get("whatsapp") or cust.get("mobile")
    assert cust.get("gstin")

    cal = client.get("/api/v1/calibration/active", headers=headers)
    assert cal.status_code == 200, cal.text
    assert cal.json()["certificate_no"] == "CTR72521126R0563"
    assert cal.json()["is_active"] is True


def test_create_customer_with_whatsapp_and_address(client):
    headers = _auth(client)
    res = client.post(
        "/api/v1/customers",
        headers=headers,
        json={
            "code": "CUST-PHASEB",
            "name": "Phase B Customer",
            "mobile": "9111122222",
            "whatsapp": "9111122222",
            "gstin": "37CCCCC0000C1Z5",
            "address": "Tirupati Road, Chittoor",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["whatsapp"] == "9111122222"
    assert "Chittoor" in (body["address"] or "")


def test_create_product_density_and_storage_location(client):
    headers = _auth(client)
    prod = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "code": "KEROSENE",
            "name": "Kerosene",
            "hsn": "2710",
            "unit": "L",
            "density_default": 0.8,
            "loss_limit_percent": 1.5,
        },
    )
    assert prod.status_code == 201, prod.text
    pid = prod.json()["id"]

    unit = client.post(
        "/api/v1/storage/units",
        headers=headers,
        json={
            "code": "T-99",
            "name": "Tank T-99",
            "kind": "TANK",
            "capacity": 100000,
            "capacity_unit": "L",
            "product_id": pid,
            "location_label": "Bay 9",
        },
    )
    assert unit.status_code == 201, unit.text
    assert unit.json()["location_label"] == "Bay 9"
    assert unit.json()["product_id"] == pid
