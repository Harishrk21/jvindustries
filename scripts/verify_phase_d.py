"""Go-Live Phase D — search/timeline + approvals/exceptions inbox.

Exit: PHASE_D_OK
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from tests.jpeg_fixture import MINI_JPEG  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
GPS = {"lat": 13.0827, "lon": 80.2707, "accuracy_m": 8}
FAILED: list[str] = []


def ok(name: str) -> None:
    print(f"OK  {name}")


def fail(name: str, detail: str) -> None:
    FAILED.append(name)
    print(f"FAIL {name} - {detail}")


def step(name: str, fn):
    try:
        fn()
        ok(name)
    except Exception as exc:  # noqa: BLE001
        fail(name, str(exc))


def main() -> int:
    print(f"PHASE_D verify base={BASE}")
    client = httpx.Client(base_url=BASE, timeout=60.0)
    token = None
    headers: dict[str, str] = {}

    def login():
        nonlocal token, headers
        r = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"})
        r.raise_for_status()
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

    step("login", login)
    if not token:
        print("PHASE_D_FAIL: cannot login")
        return 1

    plate = "TN 55 DD 4321"
    txn_pk = None
    txn_code = None

    def seed_vehicle_txn():
        nonlocal txn_pk, txn_code
        r = client.post(
            "/api/v1/vehicles/entry/start",
            headers=headers,
            json={
                "client_transaction_id": str(uuid.uuid4()),
                "type": "MATERIAL_LOADING_OUTWARD",
                "gps": GPS,
            },
        )
        r.raise_for_status()
        body = r.json()
        txn_pk = body["id"]
        txn_code = body["transaction_id"]

        data = {
            "transaction_pk": txn_pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": f"Vehicle plate {plate}",
        }
        files = {"image": ("entry.jpg", MINI_JPEG, "image/jpeg")}
        anpr = client.post("/api/v1/vehicles/anpr", headers=headers, data=data, files=files)
        anpr.raise_for_status()
        conf = client.post(
            "/api/v1/vehicles/anpr/confirm",
            headers=headers,
            json={
                "transaction_pk": txn_pk,
                "anpr_result_id": anpr.json()["id"],
                "confirm": True,
                "gps": GPS,
            },
        )
        conf.raise_for_status()
        drv = client.post(
            "/api/v1/vehicles/driver",
            headers=headers,
            json={
                "transaction_pk": txn_pk,
                "driver_name": "Phase D Driver",
                "driver_mobile": "9888777666",
            },
        )
        drv.raise_for_status()

    step("seed-vehicle-txn", seed_vehicle_txn)

    def search_by_plate_and_code():
        assert txn_pk and txn_code
        r = client.get("/api/v1/transactions", headers=headers, params={"q": plate})
        r.raise_for_status()
        body = r.json()
        assert body["total"] >= 1, body
        assert any(i["id"] == txn_pk for i in body["items"]), body

        r = client.get("/api/v1/transactions", headers=headers, params={"q": txn_code})
        r.raise_for_status()
        assert any(i["transaction_id"] == txn_code for i in r.json()["items"]), r.json()

        r = client.get(
            "/api/v1/transactions",
            headers=headers,
            params={"status": "AWAITING_TARE"},
        )
        r.raise_for_status()
        assert r.json()["total"] >= 1, r.json()

    step("search", search_by_plate_and_code)

    def timeline():
        assert txn_pk
        r = client.get(f"/api/v1/transactions/{txn_pk}/timeline", headers=headers)
        r.raise_for_status()
        body = r.json()
        assert body["transaction_id"] == txn_code, body
        assert len(body["events"]) >= 2, body
        statuses = [e["to_status"] for e in body["events"]]
        assert "ENTRY_STARTED" in statuses or "VEHICLE_VERIFIED" in statuses or "AWAITING_TARE" in statuses, statuses

    step("timeline", timeline)

    verification_id = None

    def create_mismatch_approval():
        nonlocal verification_id
        assert txn_pk
        data = {
            "transaction_pk": txn_pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": f"Invoice No INV-D-1 Vehicle TN 01 ZZ 9999 Total 9000",
        }
        files = {"image": ("inv.jpg", MINI_JPEG, "image/jpeg")}
        inv = client.post("/api/v1/documents/invoice/detect", headers=headers, data=data, files=files)
        inv.raise_for_status()
        client.post(
            "/api/v1/documents/invoice/confirm",
            headers=headers,
            json={
                "transaction_pk": txn_pk,
                "invoice_id": inv.json()["id"],
                "gps": GPS,
                "invoice_number": "INV-D-1",
                "vehicle_number": "TN 01 ZZ 9999",
            },
        ).raise_for_status()

        data["ocr_text"] = "E-Way Bill No 111222333444 Vehicle TN 01 ZZ 9999"
        files = {"image": ("ewb.jpg", MINI_JPEG, "image/jpeg")}
        ewb = client.post("/api/v1/documents/eway/detect", headers=headers, data=data, files=files)
        ewb.raise_for_status()
        conf = client.post(
            "/api/v1/documents/eway/confirm",
            headers=headers,
            json={
                "transaction_pk": txn_pk,
                "eway_id": ewb.json()["id"],
                "gps": GPS,
                "eway_bill_number": "111222333444",
                "vehicle_number": "TN 01 ZZ 9999",
            },
        )
        conf.raise_for_status()
        body = conf.json()
        assert body["match_status"] == "MISMATCH", body
        assert body["status"] == "APPROVAL_PENDING", body
        verification_id = body["verification_id"]

    step("create-mismatch", create_mismatch_approval)

    def approvals_inbox():
        assert verification_id and txn_pk
        r = client.get("/api/v1/approvals", headers=headers)
        r.raise_for_status()
        body = r.json()
        assert body["total"] >= 1, body
        hit = next(
            (
                i
                for i in body["items"]
                if i["kind"] == "DOCUMENT_MISMATCH" and i["id"] == verification_id
            ),
            None,
        )
        assert hit is not None, body
        assert hit["transaction_pk"] == txn_pk, hit

    step("approvals-inbox", approvals_inbox)

    def approve_mismatch():
        assert verification_id and txn_pk
        r = client.post(
            "/api/v1/documents/mismatch/approve",
            headers=headers,
            json={
                "transaction_pk": txn_pk,
                "verification_id": verification_id,
                "approval_note": "Phase D verify — temporary trailer",
                "gps": GPS,
            },
        )
        r.raise_for_status()
        assert r.json()["status"] == "DOCUMENTS_VERIFIED", r.json()

        r = client.get("/api/v1/approvals", headers=headers)
        r.raise_for_status()
        leftover = [
            i
            for i in r.json()["items"]
            if i["kind"] == "DOCUMENT_MISMATCH" and i["id"] == verification_id
        ]
        assert leftover == [], leftover

    step("approve-mismatch", approve_mismatch)

    def exceptions_inbox():
        assert txn_pk
        # DOCUMENTS_VERIFIED → EXIT_PENDING → wrong plate confirm → EXCEPTION
        data = {
            "transaction_pk": txn_pk,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": "Exit wrong plate TN 00 XX 1111",
        }
        files = {"image": ("exit.jpg", MINI_JPEG, "image/jpeg")}
        det = client.post("/api/v1/vehicles/exit/detect", headers=headers, data=data, files=files)
        det.raise_for_status()
        anpr = det.json()
        assert anpr["status"] == "MISMATCH", anpr

        conf = client.post(
            "/api/v1/vehicles/exit/confirm",
            headers=headers,
            json={
                "transaction_pk": txn_pk,
                "anpr_result_id": anpr["id"],
                "gps": GPS,
                "complete_transaction": False,
            },
        )
        assert conf.status_code == 409, conf.text

        st = client.get(f"/api/v1/transactions/{txn_pk}", headers=headers)
        st.raise_for_status()
        assert st.json()["status"] == "EXCEPTION", st.json()

        r = client.get("/api/v1/exceptions", headers=headers)
        r.raise_for_status()
        body = r.json()
        assert body["total"] >= 1, body
        assert any(i["transaction_pk"] == txn_pk for i in body["items"]), body

    step("exceptions-inbox", exceptions_inbox)

    client.close()
    if FAILED:
        print(f"PHASE_D_FAIL ({len(FAILED)}): {', '.join(FAILED)}")
        return 1
    print("PHASE_D_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
