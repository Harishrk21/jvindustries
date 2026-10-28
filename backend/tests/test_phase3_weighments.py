import pytest

from tests.jpeg_fixture import MINI_JPEG

GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}


def _auth(client):
    token = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _ready_for_tare(client, headers):
    start = client.post(
        "/api/v1/vehicles/entry/start",
        headers=headers,
        json={"type": "MATERIAL_LOADING_OUTWARD", "gps": GPS},
    )
    pk = start.json()["id"]
    anpr = client.post(
        "/api/v1/vehicles/anpr",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "TN 09 AB 1234",
        },
        files={"image": ("e.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/vehicles/anpr/confirm",
        headers=headers,
        json={"transaction_pk": pk, "anpr_result_id": anpr.json()["id"], "confirm": True, "gps": GPS},
    )
    client.post(
        "/api/v1/vehicles/driver",
        headers=headers,
        json={"transaction_pk": pk, "driver_name": "Ravi", "driver_mobile": "9876543210"},
    )
    return pk


def test_tare_gross_net_density_litres(client):
    headers = _auth(client)
    pk = _ready_for_tare(client, headers)

    tare_det = client.post(
        "/api/v1/weighments/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "kind": "TARE",
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "TARE 11,820 KG",
        },
        files={"image": ("tare.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert tare_det.status_code == 200, tare_det.text
    assert tare_det.json()["detected_weight_kg"] == 11820.0
    tare_photo = tare_det.json()["photo_id"]

    tare_ok = client.post(
        "/api/v1/weighments/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "kind": "TARE",
            "photo_id": tare_photo,
            "confirmed_weight_kg": 11820,
            "ocr_weight_kg": 11820,
            "ocr_confidence": tare_det.json()["confidence"],
            "ocr_provider": tare_det.json()["provider"],
            "ocr_raw_text": "TARE 11,820 KG",
            "gps": GPS,
            "after_tare_mode": "LOADING",
        },
    )
    assert tare_ok.status_code == 200, tare_ok.text
    assert tare_ok.json()["tare_kg"] == 11820
    assert tare_ok.json()["status"] == "LOADING"

    gross_det = client.post(
        "/api/v1/weighments/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "kind": "GROSS",
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "GROSS 45,110 KG",
        },
        files={"image": ("gross.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert gross_det.status_code == 200
    assert gross_det.json()["detected_weight_kg"] == 45110.0

    gross_ok = client.post(
        "/api/v1/weighments/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "kind": "GROSS",
            "photo_id": gross_det.json()["photo_id"],
            "confirmed_weight_kg": 45110,
            "ocr_weight_kg": 45110,
            "gps": GPS,
        },
    )
    assert gross_ok.status_code == 200, gross_ok.text
    assert gross_ok.json()["net_kg"] == 33290.0
    assert gross_ok.json()["status"] == "DENSITY_PENDING"

    dens_det = client.post(
        "/api/v1/weighments/density/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "0.845 kg/L 30°C",
        },
        files={"image": ("dens.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert dens_det.status_code == 200, dens_det.text
    assert dens_det.json()["detected_density"] == 0.845

    dens_ok = client.post(
        "/api/v1/weighments/density/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "photo_id": dens_det.json()["photo_id"],
            "confirmed_density": 0.845,
            "confirmed_temperature_c": 30,
            "ocr_density": 0.845,
            "ocr_temperature": 30,
            "ocr_confidence": dens_det.json()["confidence"],
            "gps": GPS,
        },
    )
    assert dens_ok.status_code == 200, dens_ok.text
    assert dens_ok.json()["calculated_litres"] == pytest.approx(39396.45, abs=0.1)

    summary = client.get(f"/api/v1/weighments/summary/{pk}", headers=headers)
    assert summary.json()["calculated_litres"] == pytest.approx(39396.45, abs=0.1)
    assert summary.json()["calculated_quantity_label"] == "CALCULATED QUANTITY"

def _ready_inward(client, headers):
    start = client.post(
        "/api/v1/vehicles/entry/start",
        headers=headers,
        json={"type": "MATERIAL_RECEIVING_INWARD", "gps": GPS},
    )
    pk = start.json()["id"]
    anpr = client.post(
        "/api/v1/vehicles/anpr",
        headers=headers,
        data={
            "transaction_pk": pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "TN 09 AB 5678",
        },
        files={"image": ("e.jpg", MINI_JPEG, "image/jpeg")},
    )
    client.post(
        "/api/v1/vehicles/anpr/confirm",
        headers=headers,
        json={"transaction_pk": pk, "anpr_result_id": anpr.json()["id"], "confirm": True, "gps": GPS},
    )
    client.post(
        "/api/v1/vehicles/driver",
        headers=headers,
        json={
            "transaction_pk": pk,
            "driver_name": "Kumar",
            "driver_mobile": "9876501234",
            "vehicle_type": "Tanker",
        },
    )
    return pk


def test_inward_gross_then_tare_net(client):
    """Inward arrives loaded: gross first, then empty tare ? net."""
    headers = _auth(client)
    pk = _ready_inward(client, headers)

    gross_det = client.post(
        "/api/v1/weighments/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "kind": "GROSS",
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "GROSS 45,110 KG",
        },
        files={"image": ("gross.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert gross_det.status_code == 200, gross_det.text

    gross_ok = client.post(
        "/api/v1/weighments/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "kind": "GROSS",
            "photo_id": gross_det.json()["photo_id"],
            "confirmed_weight_kg": 45110,
            "gps": GPS,
        },
    )
    assert gross_ok.status_code == 200, gross_ok.text
    assert gross_ok.json()["gross_kg"] == 45110
    assert gross_ok.json()["net_kg"] is None
    assert gross_ok.json()["status"] == "UNLOADING"

    tare_det = client.post(
        "/api/v1/weighments/detect",
        headers=headers,
        data={
            "transaction_pk": pk,
            "kind": "TARE",
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "TARE 11,820 KG",
        },
        files={"image": ("tare.jpg", MINI_JPEG, "image/jpeg")},
    )
    assert tare_det.status_code == 200, tare_det.text

    tare_ok = client.post(
        "/api/v1/weighments/confirm",
        headers=headers,
        json={
            "transaction_pk": pk,
            "kind": "TARE",
            "photo_id": tare_det.json()["photo_id"],
            "confirmed_weight_kg": 11820,
            "gps": GPS,
        },
    )
    assert tare_ok.status_code == 200, tare_ok.text
    assert tare_ok.json()["tare_kg"] == 11820
    assert tare_ok.json()["net_kg"] == 33290.0
    assert tare_ok.json()["status"] == "DENSITY_PENDING"
