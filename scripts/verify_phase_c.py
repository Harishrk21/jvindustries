"""Go-Live Phase C — live API dry-run: outward loading + inward receiving.

Uses miniature JPEG evidence + OCR text fixtures (no phone camera required).
Exit: PHASE_C_OK
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import httpx

# Reuse test JPEG bytes
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
    print(f"PHASE_C verify base={BASE}")
    client = httpx.Client(base_url=BASE, timeout=60.0)

    token = None

    def login():
        nonlocal token
        r = client.post("/api/v1/auth/login", json={"user_id": "owner", "password": "Owner@123"})
        r.raise_for_status()
        token = r.json()["access_token"]

    step("login", login)
    if not token:
        print("PHASE_C_FAIL: cannot login")
        return 1

    headers = {"Authorization": f"Bearer {token}"}

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

    # ---------- OUTWARD ----------
    out_pk = None
    plate = "TN 09 AB 1234"

    def outward_entry():
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
        body = r.json()
        assert body["status"] == "ENTRY_STARTED", body
        out_pk = body["id"]

    def outward_anpr_driver():
        data, files = multipart({"transaction_pk": out_pk}, "entry.jpg", f"Vehicle plate {plate}")
        r = client.post("/api/v1/vehicles/anpr", headers=headers, data=data, files=files)
        r.raise_for_status()
        anpr = r.json()
        r = client.post(
            "/api/v1/vehicles/anpr/confirm",
            headers=headers,
            json={"transaction_pk": out_pk, "anpr_result_id": anpr["id"], "confirm": True, "gps": GPS},
        )
        r.raise_for_status()
        assert r.json()["status"] == "VEHICLE_VERIFIED", r.json()
        r = client.post(
            "/api/v1/vehicles/driver",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "driver_name": "Ravi Kumar",
                "driver_mobile": "9876543210",
                "transporter_name": "ABC Transport",
            },
        )
        r.raise_for_status()
        assert r.json()["status"] == "AWAITING_TARE", r.json()

    def outward_weigh_density():
        data, files = multipart({"transaction_pk": out_pk, "kind": "TARE"}, "tare.jpg", "TARE 11,820 KG")
        r = client.post("/api/v1/weighments/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        tare = r.json()
        r = client.post(
            "/api/v1/weighments/confirm",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "kind": "TARE",
                "photo_id": tare["photo_id"],
                "confirmed_weight_kg": 11820,
                "ocr_weight_kg": 11820,
                "ocr_confidence": tare["confidence"],
                "ocr_provider": tare["provider"],
                "ocr_raw_text": "TARE 11,820 KG",
                "gps": GPS,
                "after_tare_mode": "LOADING",
            },
        )
        r.raise_for_status()
        assert r.json()["tare_kg"] == 11820, r.json()

        data, files = multipart({"transaction_pk": out_pk, "kind": "GROSS"}, "gross.jpg", "GROSS 45,110 KG")
        r = client.post("/api/v1/weighments/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        gross = r.json()
        r = client.post(
            "/api/v1/weighments/confirm",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "kind": "GROSS",
                "photo_id": gross["photo_id"],
                "confirmed_weight_kg": 45110,
                "ocr_weight_kg": 45110,
                "gps": GPS,
            },
        )
        r.raise_for_status()
        assert r.json()["net_kg"] == 33290.0, r.json()

        data, files = multipart({"transaction_pk": out_pk}, "dens.jpg", "0.845 kg/L 30C")
        r = client.post("/api/v1/weighments/density/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        dens = r.json()
        r = client.post(
            "/api/v1/weighments/density/confirm",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "photo_id": dens["photo_id"],
                "confirmed_density": 0.845,
                "confirmed_temperature_c": 30,
                "ocr_density": 0.845,
                "ocr_temperature": 30,
                "ocr_confidence": dens["confidence"],
                "gps": GPS,
            },
        )
        r.raise_for_status()
        dens_out = r.json()
        # Server rounds litres (33290 / 0.845 ≈ 39396.45 → 39396.4)
        assert abs(float(dens_out["calculated_litres"]) - 39396.45) < 0.1, dens_out
        assert float(dens_out["density_kg_per_l"]) == 0.845, dens_out

    def outward_documents():
        data, files = multipart(
            {"transaction_pk": out_pk},
            "inv.jpg",
            f"Tax Invoice No INV/2026/C001 Date 01/10/2026 GSTIN 33AAAAA0000A1Z5 Vehicle {plate} Total 100000",
        )
        r = client.post("/api/v1/documents/invoice/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        inv = r.json()
        r = client.post(
            "/api/v1/documents/invoice/confirm",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "invoice_id": inv["id"],
                "gps": GPS,
                "invoice_number": inv["fields"].get("invoice_number") or "INV/2026/C001",
                "vehicle_number": plate,
            },
        )
        r.raise_for_status()

        data, files = multipart(
            {"transaction_pk": out_pk},
            "ewb.jpg",
            f"E-Way Bill No 123456789012 Vehicle {plate} From Chennai To Coimbatore",
        )
        r = client.post("/api/v1/documents/eway/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        ewb = r.json()
        r = client.post(
            "/api/v1/documents/eway/confirm",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "eway_id": ewb["id"],
                "gps": GPS,
                "eway_bill_number": ewb["fields"].get("eway_bill_number") or "123456789012",
                "vehicle_number": plate,
            },
        )
        r.raise_for_status()
        assert r.json()["match_status"] == "MATCH", r.json()
        assert r.json()["status"] == "DOCUMENTS_VERIFIED", r.json()

    def outward_otp():
        r = client.post(
            "/api/v1/otp/send",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "customer_mobile": "9876543210",
                "customer_name": "ABC Industries",
                "gps": GPS,
            },
        )
        r.raise_for_status()
        body = r.json()
        assert body["status"] == "SENT", body
        assert body.get("otp_preview"), "mock preview required for automated verify"
        r = client.post(
            "/api/v1/otp/verify",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "otp_id": body["otp_id"],
                "otp_code": body["otp_preview"],
                "gps": GPS,
            },
        )
        r.raise_for_status()
        assert r.json()["verified"] is True, r.json()

    def outward_gate_pdf_exit():
        r = client.post(
            "/api/v1/gate-passes",
            headers=headers,
            json={"transaction_pk": out_pk, "pass_type": "OUTWARD_LOADING", "direction": "OUTWARD"},
        )
        r.raise_for_status()
        assert r.json()["gate_pass_number"].startswith("JV/GP/"), r.json()

        for variant in ("customer", "internal"):
            r = client.get(
                f"/api/v1/pdfs/transaction/{out_pk}",
                headers=headers,
                params={"variant": variant},
            )
            r.raise_for_status()
            assert r.content[:4] == b"%PDF", variant

        r = client.get(f"/api/v1/pdfs/gate-pass/{out_pk}", headers=headers)
        r.raise_for_status()
        assert r.content[:4] == b"%PDF"

        # Phase E: outward close requires linked customer master
        custs = client.get("/api/v1/customers", headers=headers)
        custs.raise_for_status()
        cust = next((c for c in custs.json() if c.get("active", True)), None)
        if cust is None:
            created = client.post(
                "/api/v1/customers",
                headers=headers,
                json={"code": f"CUST-C-{uuid.uuid4().hex[:6].upper()}", "name": "Phase C Customer", "mobile": "9876543210"},
            )
            created.raise_for_status()
            cust = created.json()
        client.post(
            f"/api/v1/transactions/{out_pk}/parties",
            headers=headers,
            json={"customer_id": cust["id"]},
        ).raise_for_status()

        data, files = multipart({"transaction_pk": out_pk}, "exit.jpg", f"Exit {plate}")
        r = client.post("/api/v1/vehicles/exit/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        exit_anpr = r.json()
        r = client.post(
            "/api/v1/vehicles/exit/confirm",
            headers=headers,
            json={
                "transaction_pk": out_pk,
                "anpr_result_id": exit_anpr["id"],
                "gps": GPS,
                "complete_transaction": True,
            },
        )
        r.raise_for_status()
        assert r.json()["status"] == "COMPLETED", r.json()

    step("outward-entry", outward_entry)
    if out_pk:
        step("outward-anpr-driver", outward_anpr_driver)
        step("outward-weigh-density", outward_weigh_density)
        step("outward-documents", outward_documents)
        step("outward-otp", outward_otp)
        step("outward-gate-pdf-exit", outward_gate_pdf_exit)

    # ---------- INWARD ----------
    in_pk = None
    in_plate = "TN 22 CD 5678"

    def inward_entry_docs_weigh():
        nonlocal in_pk
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
        in_pk = r.json()["id"]

        data, files = multipart({"transaction_pk": in_pk}, "in-entry.jpg", f"Vehicle {in_plate}")
        r = client.post("/api/v1/vehicles/anpr", headers=headers, data=data, files=files)
        r.raise_for_status()
        anpr = r.json()
        r = client.post(
            "/api/v1/vehicles/anpr/confirm",
            headers=headers,
            json={"transaction_pk": in_pk, "anpr_result_id": anpr["id"], "confirm": True, "gps": GPS},
        )
        r.raise_for_status()
        r = client.post(
            "/api/v1/vehicles/driver",
            headers=headers,
            json={"transaction_pk": in_pk, "driver_name": "Kumar", "driver_mobile": "9000000001"},
        )
        r.raise_for_status()

        # Inward: documents early
        data, files = multipart(
            {"transaction_pk": in_pk},
            "in-inv.jpg",
            f"Tax Invoice No INV/IN/100 Vehicle {in_plate} GSTIN 33BBBBB0000B1Z5 Total 50000",
        )
        r = client.post("/api/v1/documents/invoice/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        inv = r.json()
        r = client.post(
            "/api/v1/documents/invoice/confirm",
            headers=headers,
            json={
                "transaction_pk": in_pk,
                "invoice_id": inv["id"],
                "gps": GPS,
                "invoice_number": inv["fields"].get("invoice_number") or "INV/IN/100",
                "vehicle_number": in_plate,
            },
        )
        r.raise_for_status()

        data, files = multipart(
            {"transaction_pk": in_pk},
            "in-ewb.jpg",
            f"E-Way Bill No 998877665544 Vehicle {in_plate}",
        )
        r = client.post("/api/v1/documents/eway/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        ewb = r.json()
        r = client.post(
            "/api/v1/documents/eway/confirm",
            headers=headers,
            json={
                "transaction_pk": in_pk,
                "eway_id": ewb["id"],
                "gps": GPS,
                "eway_bill_number": ewb["fields"].get("eway_bill_number") or "998877665544",
                "vehicle_number": in_plate,
            },
        )
        r.raise_for_status()
        assert r.json()["match_status"] == "MATCH", r.json()

        # Tare / gross for receiving
        data, files = multipart({"transaction_pk": in_pk, "kind": "TARE"}, "in-tare.jpg", "TARE 12,000 KG")
        r = client.post("/api/v1/weighments/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        tare = r.json()
        r = client.post(
            "/api/v1/weighments/confirm",
            headers=headers,
            json={
                "transaction_pk": in_pk,
                "kind": "TARE",
                "photo_id": tare["photo_id"],
                "confirmed_weight_kg": 12000,
                "ocr_weight_kg": 12000,
                "gps": GPS,
                "after_tare_mode": "UNLOADING",
            },
        )
        r.raise_for_status()

        data, files = multipart({"transaction_pk": in_pk, "kind": "GROSS"}, "in-gross.jpg", "GROSS 40,000 KG")
        r = client.post("/api/v1/weighments/detect", headers=headers, data=data, files=files)
        r.raise_for_status()
        gross = r.json()
        r = client.post(
            "/api/v1/weighments/confirm",
            headers=headers,
            json={
                "transaction_pk": in_pk,
                "kind": "GROSS",
                "photo_id": gross["photo_id"],
                "confirmed_weight_kg": 40000,
                "ocr_weight_kg": 40000,
                "gps": GPS,
            },
        )
        r.raise_for_status()
        assert r.json()["net_kg"] == 28000.0, r.json()

        r = client.post(
            "/api/v1/gate-passes",
            headers=headers,
            json={"transaction_pk": in_pk, "pass_type": "INWARD_MATERIAL", "direction": "INWARD"},
        )
        r.raise_for_status()

        # Phase E: inward close requires supplier (PDF path only here — link for future complete)
        sups = client.get("/api/v1/suppliers", headers=headers)
        sups.raise_for_status()
        sup = next((s for s in sups.json() if s.get("active", True)), None)
        if sup is None:
            created = client.post(
                "/api/v1/suppliers",
                headers=headers,
                json={"code": f"SUP-C-{uuid.uuid4().hex[:6].upper()}", "name": "Phase C Supplier", "mobile": "9000000001"},
            )
            created.raise_for_status()
            sup = created.json()
        client.post(
            f"/api/v1/transactions/{in_pk}/parties",
            headers=headers,
            json={"supplier_id": sup["id"]},
        ).raise_for_status()

        r = client.get(
            f"/api/v1/pdfs/transaction/{in_pk}",
            headers=headers,
            params={"variant": "customer"},
        )
        r.raise_for_status()
        assert r.content[:4] == b"%PDF"

    step("inward-entry-docs-weigh-pdf", inward_entry_docs_weigh)

    client.close()
    if FAILED:
        print(f"PHASE_C_FAIL ({len(FAILED)}): {', '.join(FAILED)}")
        return 1
    print("PHASE_C_OK")
    print("NOTE: Camera/GPS on physical device still required for operator acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
