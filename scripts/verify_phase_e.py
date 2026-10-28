"""Go-Live Phase E — customers/suppliers masters + closure blockers.

Exit: PHASE_E_OK
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
    print(f"PHASE_E verify base={BASE}")
    client = httpx.Client(base_url=BASE, timeout=90.0)
    headers: dict[str, str] = {}
    customer_id = None
    supplier_id = None
    out_pk = None
    plate = "TN 77 EE 7788"

    def login():
        nonlocal headers
        r = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"})
        r.raise_for_status()
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    step("login", login)
    if not headers:
        print("PHASE_E_FAIL: cannot login")
        return 1

    def masters_crud():
        nonlocal customer_id, supplier_id
        suffix = uuid.uuid4().hex[:6].upper()
        c = client.post(
            "/api/v1/customers",
            headers=headers,
            json={
                "code": f"CUST-E-{suffix}",
                "name": "Phase E Customer",
                "mobile": "9876500001",
                "gstin": "33CCCCC0000C1Z5",
            },
        )
        c.raise_for_status()
        customer_id = c.json()["id"]

        s = client.post(
            "/api/v1/suppliers",
            headers=headers,
            json={
                "code": f"SUP-E-{suffix}",
                "name": "Phase E Supplier",
                "mobile": "9876500002",
                "gstin": "33DDDDD0000D1Z5",
            },
        )
        s.raise_for_status()
        supplier_id = s.json()["id"]

        cl = client.get("/api/v1/customers", headers=headers)
        cl.raise_for_status()
        assert any(x["id"] == customer_id for x in cl.json()), cl.json()
        sl = client.get("/api/v1/suppliers", headers=headers)
        sl.raise_for_status()
        assert any(x["id"] == supplier_id for x in sl.json()), sl.json()

    step("masters-crud", masters_crud)

    def multipart(extra: dict, filename: str, ocr: str):
        data = {
            **extra,
            "gps_lat": str(GPS["lat"]),
            "gps_lon": str(GPS["lon"]),
            "gps_accuracy_m": str(GPS["accuracy_m"]),
            "capture_source": "LIVE_CAMERA",
            "ocr_text": ocr,
        }
        files = {"image": (filename, MINI_JPEG, "image/jpeg")}
        return data, files

    def outward_seed_and_block():
        nonlocal out_pk
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
        out_pk = r.json()["id"]

        data, files = multipart({"transaction_pk": out_pk}, "e.jpg", f"Vehicle plate {plate}")
        anpr = client.post("/api/v1/vehicles/anpr", headers=headers, data=data, files=files)
        anpr.raise_for_status()
        client.post(
            "/api/v1/vehicles/anpr/confirm",
            headers=headers,
            json={"transaction_pk": out_pk, "anpr_result_id": anpr.json()["id"], "confirm": True, "gps": GPS},
        ).raise_for_status()
        client.post(
            "/api/v1/vehicles/driver",
            headers=headers,
            json={"transaction_pk": out_pk, "driver_name": "E Driver", "driver_mobile": "9000111222"},
        ).raise_for_status()

        chk = client.get(f"/api/v1/transactions/{out_pk}/closure-check", headers=headers)
        chk.raise_for_status()
        body = chk.json()
        assert body["can_complete"] is False, body
        assert any("Invoice" in b or "OTP" in b or "Customer" in b or "Gate" in b for b in body["blockers"]), body

        # Attempt early complete via exit — should 409 after EXIT_COMPLETED or refuse
        data, files = multipart({"transaction_pk": out_pk}, "ex.jpg", f"Exit {plate}")
        det = client.post("/api/v1/vehicles/exit/detect", headers=headers, data=data, files=files)
        det.raise_for_status()
        conf = client.post(
            "/api/v1/vehicles/exit/confirm",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "anpr_result_id": det.json()["id"],
                "gps": GPS,
                "complete_transaction": True,
            },
        )
        assert conf.status_code == 409, conf.text
        assert "Cannot complete" in conf.text
        st = client.get(f"/api/v1/transactions/{out_pk}", headers=headers)
        st.raise_for_status()
        assert st.json()["status"] == "EXIT_COMPLETED", st.json()

    step("outward-block-incomplete", outward_seed_and_block)

    def outward_complete_after_checklist():
        assert out_pk and customer_id
        # New txn — previous is EXIT_COMPLETED incomplete
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
        pk = r.json()["id"]
        data, files = multipart({"transaction_pk": pk}, "e2.jpg", f"Vehicle plate {plate}")
        anpr = client.post("/api/v1/vehicles/anpr", headers=headers, data=data, files=files)
        anpr.raise_for_status()
        client.post(
            "/api/v1/vehicles/anpr/confirm",
            headers=headers,
            json={"transaction_pk": pk, "anpr_result_id": anpr.json()["id"], "confirm": True, "gps": GPS},
        ).raise_for_status()
        client.post(
            "/api/v1/vehicles/driver",
            headers=headers,
            json={"transaction_pk": pk, "driver_name": "E Driver 2", "driver_mobile": "9000111333"},
        ).raise_for_status()

        # Weigh path required before docs → DOCUMENTS_VERIFIED → OTP
        data, files = multipart({"transaction_pk": pk, "kind": "TARE"}, "tare.jpg", "TARE 12,000 KG")
        tare = client.post("/api/v1/weighments/detect", headers=headers, data=data, files=files)
        tare.raise_for_status()
        client.post(
            "/api/v1/weighments/confirm",
            headers=headers,
            json={
                "transaction_pk": pk,
                "kind": "TARE",
                "photo_id": tare.json()["photo_id"],
                "confirmed_weight_kg": 12000,
                "ocr_weight_kg": 12000,
                "gps": GPS,
                "after_tare_mode": "LOADING",
            },
        ).raise_for_status()
        data, files = multipart({"transaction_pk": pk, "kind": "GROSS"}, "gross.jpg", "GROSS 40,000 KG")
        gross = client.post("/api/v1/weighments/detect", headers=headers, data=data, files=files)
        gross.raise_for_status()
        client.post(
            "/api/v1/weighments/confirm",
            headers=headers,
            json={
                "transaction_pk": pk,
                "kind": "GROSS",
                "photo_id": gross.json()["photo_id"],
                "confirmed_weight_kg": 40000,
                "ocr_weight_kg": 40000,
                "gps": GPS,
            },
        ).raise_for_status()

        # docs match
        data, files = multipart(
            {"transaction_pk": pk},
            "inv.jpg",
            f"Tax Invoice No INV/E/1 Vehicle {plate} GSTIN 33AAAAA0000A1Z5 Total 1000",
        )
        inv = client.post("/api/v1/documents/invoice/detect", headers=headers, data=data, files=files)
        inv.raise_for_status()
        client.post(
            "/api/v1/documents/invoice/confirm",
            headers=headers,
            json={
                "transaction_pk": pk,
                "invoice_id": inv.json()["id"],
                "gps": GPS,
                "invoice_number": "INV/E/1",
                "vehicle_number": plate,
            },
        ).raise_for_status()
        data, files = multipart(
            {"transaction_pk": pk},
            "ewb.jpg",
            f"E-Way Bill No 555666777888 Vehicle {plate}",
        )
        ewb = client.post("/api/v1/documents/eway/detect", headers=headers, data=data, files=files)
        ewb.raise_for_status()
        client.post(
            "/api/v1/documents/eway/confirm",
            headers=headers,
            json={
                "transaction_pk": pk,
                "eway_id": ewb.json()["id"],
                "gps": GPS,
                "eway_bill_number": "555666777888",
                "vehicle_number": plate,
            },
        ).raise_for_status()

        otp = client.post(
            "/api/v1/otp/send",
            headers=headers,
            json={
                "transaction_pk": pk,
                "customer_mobile": "9876500001",
                "customer_name": "Phase E Customer",
                "gps": GPS,
            },
        )
        otp.raise_for_status()
        preview = otp.json()["otp_preview"]
        client.post(
            "/api/v1/otp/verify",
            headers=headers,
            json={
                "transaction_pk": pk,
                "otp_id": otp.json()["otp_id"],
                "otp_code": preview,
                "gps": GPS,
            },
        ).raise_for_status()

        client.post(
            "/api/v1/gate-passes",
            headers=headers,
            json={"transaction_pk": pk, "pass_type": "OUTWARD_LOADING", "direction": "OUTWARD"},
        ).raise_for_status()

        client.post(
            f"/api/v1/transactions/{pk}/parties",
            headers=headers,
            json={"customer_id": customer_id},
        ).raise_for_status()

        chk = client.get(f"/api/v1/transactions/{pk}/closure-check", headers=headers)
        chk.raise_for_status()
        assert chk.json()["can_complete"] is True, chk.json()

        data, files = multipart({"transaction_pk": pk}, "ex2.jpg", f"Exit {plate}")
        det = client.post("/api/v1/vehicles/exit/detect", headers=headers, data=data, files=files)
        det.raise_for_status()
        conf = client.post(
            "/api/v1/vehicles/exit/confirm",
            headers=headers,
            json={
                "transaction_pk": pk,
                "anpr_result_id": det.json()["id"],
                "gps": GPS,
                "complete_transaction": True,
            },
        )
        conf.raise_for_status()
        assert conf.json()["status"] == "COMPLETED", conf.json()

    step("outward-complete-ok", outward_complete_after_checklist)

    def inward_needs_supplier():
        assert supplier_id
        in_plate = "TN 88 FF 8899"
        r = client.post(
            "/api/v1/vehicles/entry/start",
            headers=headers,
            json={
                "client_transaction_id": str(uuid.uuid4()),
                "type": "MATERIAL_RECEIVING_INWARD",
                "gps": GPS,
            },
        )
        r.raise_for_status()
        pk = r.json()["id"]
        data, files = multipart({"transaction_pk": pk}, "in.jpg", f"Vehicle {in_plate}")
        anpr = client.post("/api/v1/vehicles/anpr", headers=headers, data=data, files=files)
        anpr.raise_for_status()
        client.post(
            "/api/v1/vehicles/anpr/confirm",
            headers=headers,
            json={"transaction_pk": pk, "anpr_result_id": anpr.json()["id"], "confirm": True, "gps": GPS},
        ).raise_for_status()
        client.post(
            "/api/v1/vehicles/driver",
            headers=headers,
            json={"transaction_pk": pk, "driver_name": "In Driver", "driver_mobile": "9000222333"},
        ).raise_for_status()

        data, files = multipart(
            {"transaction_pk": pk},
            "in-inv.jpg",
            f"Tax Invoice No INV/IN/E Vehicle {in_plate} Total 2000",
        )
        inv = client.post("/api/v1/documents/invoice/detect", headers=headers, data=data, files=files)
        inv.raise_for_status()
        client.post(
            "/api/v1/documents/invoice/confirm",
            headers=headers,
            json={
                "transaction_pk": pk,
                "invoice_id": inv.json()["id"],
                "gps": GPS,
                "invoice_number": "INV/IN/E",
                "vehicle_number": in_plate,
            },
        ).raise_for_status()
        data, files = multipart(
            {"transaction_pk": pk},
            "in-ewb.jpg",
            f"E-Way Bill No 121212121212 Vehicle {in_plate}",
        )
        ewb = client.post("/api/v1/documents/eway/detect", headers=headers, data=data, files=files)
        ewb.raise_for_status()
        client.post(
            "/api/v1/documents/eway/confirm",
            headers=headers,
            json={
                "transaction_pk": pk,
                "eway_id": ewb.json()["id"],
                "gps": GPS,
                "eway_bill_number": "121212121212",
                "vehicle_number": in_plate,
            },
        ).raise_for_status()

        client.post(
            "/api/v1/gate-passes",
            headers=headers,
            json={"transaction_pk": pk, "pass_type": "INWARD_MATERIAL", "direction": "INWARD"},
        ).raise_for_status()

        chk = client.get(f"/api/v1/transactions/{pk}/closure-check", headers=headers)
        chk.raise_for_status()
        assert chk.json()["can_complete"] is False, chk.json()
        assert any("Supplier" in b for b in chk.json()["blockers"]), chk.json()

        client.post(
            f"/api/v1/transactions/{pk}/parties",
            headers=headers,
            json={"supplier_id": supplier_id},
        ).raise_for_status()

        chk = client.get(f"/api/v1/transactions/{pk}/closure-check", headers=headers)
        chk.raise_for_status()
        assert chk.json()["can_complete"] is True, chk.json()

        data, files = multipart({"transaction_pk": pk}, "in-ex.jpg", f"Exit {in_plate}")
        det = client.post("/api/v1/vehicles/exit/detect", headers=headers, data=data, files=files)
        det.raise_for_status()
        conf = client.post(
            "/api/v1/vehicles/exit/confirm",
            headers=headers,
            json={
                "transaction_pk": pk,
                "anpr_result_id": det.json()["id"],
                "gps": GPS,
                "complete_transaction": True,
            },
        )
        conf.raise_for_status()
        assert conf.json()["status"] == "COMPLETED", conf.json()

    step("inward-supplier-closure", inward_needs_supplier)

    client.close()
    if FAILED:
        print(f"PHASE_E_FAIL ({len(FAILED)}): {', '.join(FAILED)}")
        return 1
    print("PHASE_E_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
