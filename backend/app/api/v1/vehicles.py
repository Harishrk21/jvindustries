"""Vehicle entry / ANPR from real OCR text + live evidence photo / exit."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.groq_plate_vision import recognize_plate_with_groq
from app.ai.vehicle_recognition import get_vehicle_recognition_service, normalize_plate
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_permissions
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction, TransactionEvent
from app.models.user import User
from app.models.vehicle import AnprResult, Driver, Vehicle
from app.schemas.vehicle import (
    AnprConfirmRequest,
    AnprResultOut,
    DriverDetailsRequest,
    VehicleEntryStartRequest,
    VehicleExitJsonRequest,
    VehicleTxnOut,
)
from app.services.audit_service import write_audit
from app.services.closure_service import closure_blockers
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.photo_service import store_evidence_photo
from app.services.transaction_flow import transition
from app.services.transaction_id import next_transaction_id

router = APIRouter()
_PLATE_NORMALIZE = re.compile(r"\s+")


def _require_gps(gps_lat: float, gps_lon: float, accuracy: float) -> None:
    result = GeofenceService().verify(GpsSample(gps_lat, gps_lon, accuracy))
    if not result.authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.message)


def _txn_out(txn: Transaction) -> VehicleTxnOut:
    return VehicleTxnOut.model_validate(txn)


def _get_txn(db: Session, pk: str) -> Transaction:
    txn = db.get(Transaction, pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return txn


@router.post("/entry/start", response_model=VehicleTxnOut, status_code=201)
def start_vehicle_entry(
    body: VehicleEntryStartRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("vehicle.entry")),
) -> VehicleTxnOut:
    try:
        TransactionType(body.type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unknown transaction type.") from exc

    _require_gps(body.gps.lat, body.gps.lon, body.gps.accuracy_m)

    if body.client_transaction_id:
        existing = db.execute(
            select(Transaction).where(Transaction.client_transaction_id == body.client_transaction_id)
        ).scalar_one_or_none()
        if existing:
            return _txn_out(existing)

    code = next_transaction_id(db)
    txn = Transaction(
        transaction_id=code,
        client_transaction_id=body.client_transaction_id,
        type=body.type,
        status=TransactionStatus.DRAFT.value,
        created_by=user.id,
        device_id=body.device_id,
        geofence_ok=True,
        last_lat=body.gps.lat,
        last_lon=body.gps.lon,
        last_gps_accuracy_m=body.gps.accuracy_m,
        notes=body.notes,
    )
    db.add(txn)
    db.flush()
    db.add(
        TransactionEvent(
            transaction_pk=txn.id,
            from_status=None,
            to_status=TransactionStatus.DRAFT.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason="Vehicle entry draft",
            lat=body.gps.lat,
            lon=body.gps.lon,
            gps_accuracy_m=body.gps.accuracy_m,
        )
    )
    transition(
        db,
        txn,
        to_status=TransactionStatus.ENTRY_STARTED.value,
        actor_user_id=user.id,
        device_id=body.device_id,
        reason="Vehicle entry started",
        lat=body.gps.lat,
        lon=body.gps.lon,
        gps_accuracy_m=body.gps.accuracy_m,
    )
    write_audit(
        db,
        action="VEHICLE_ENTRY_STARTED",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=body.device_id,
        details="Entry started with GPS verified",
    )
    db.commit()
    db.refresh(txn)
    return _txn_out(txn)


@router.post("/anpr", response_model=AnprResultOut)
async def run_anpr(
    transaction_pk: str = Form(...),
    gps_lat: float = Form(...),
    gps_lon: float = Form(...),
    gps_accuracy_m: float = Form(...),
    capture_source: str = Form("LIVE_CAMERA"),
    ocr_text: str = Form(...),
    device_id: str | None = Form(None),
    preferred_candidate: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("vehicle.anpr")),
) -> AnprResultOut:
    """Store live evidence + parse plate candidates from real on-device OCR text."""
    _require_gps(gps_lat, gps_lon, gps_accuracy_m)
    txn = _get_txn(db, transaction_pk)
    if txn.status not in {TransactionStatus.ENTRY_STARTED.value, TransactionStatus.EXIT_PENDING.value}:
        raise HTTPException(status_code=400, detail=f"ANPR not allowed in status {txn.status}.")

    file_type = "ENTRY_VEHICLE" if txn.status == TransactionStatus.ENTRY_STARTED.value else "EXIT_VEHICLE"
    photo, image_bytes = await store_evidence_photo(
        db,
        txn=txn,
        user=user,
        upload=image,
        file_type=file_type,
        capture_source=capture_source,
        device_id=device_id,
        lat=gps_lat,
        lon=gps_lon,
        accuracy_m=gps_accuracy_m,
    )
    if file_type == "ENTRY_VEHICLE":
        txn.entry_photo_id = photo.id
    else:
        txn.exit_photo_id = photo.id

    recognition = None
    if get_settings().groq_api_key or (get_settings().ai_provider or "").lower().startswith("groq"):
        recognition = recognize_plate_with_groq(image_bytes, ocr_text=ocr_text)
    if recognition is None:
        recognition = get_vehicle_recognition_service().recognize_from_ocr(
            ocr_text=ocr_text,
            preferred_candidate=preferred_candidate,
        )
    anpr = AnprResult(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        photo_id=photo.id,
        vehicle_number=recognition.value,
        confidence=recognition.confidence,
        provider=recognition.provider,
        status="FAILED" if recognition.failed else "DETECTED",
        actor_user_id=user.id,
    )
    db.add(anpr)
    write_audit(
        db,
        action="ANPR_RUN",
        entity_type="anpr_result",
        entity_id=anpr.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=device_id,
        details=(
            f"provider={recognition.provider} failed={recognition.failed} "
            f"plate={recognition.value} candidates={list(recognition.candidates)}"
        ),
    )
    db.commit()
    db.refresh(anpr)
    return AnprResultOut(
        id=anpr.id,
        transaction_id=anpr.transaction_id,
        vehicle_number=anpr.vehicle_number,
        confidence=anpr.confidence,
        provider=anpr.provider,
        status=anpr.status,
        message=recognition.message,
        candidates=list(recognition.candidates),
        photo_id=photo.id,
        ocr_raw_preview=(recognition.raw_ocr_text or "")[:500],
    )


@router.post("/anpr/confirm", response_model=VehicleTxnOut)
def confirm_anpr(
    body: AnprConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("vehicle.entry")),
) -> VehicleTxnOut:
    txn = _get_txn(db, body.transaction_pk)
    anpr = db.get(AnprResult, body.anpr_result_id)
    if anpr is None or anpr.transaction_pk != txn.id:
        raise HTTPException(status_code=404, detail="ANPR result not found for this transaction.")

    if body.gps:
        _require_gps(body.gps.lat, body.gps.lon, body.gps.accuracy_m)

    if not body.confirm:
        anpr.status = "RETAKE"
        write_audit(
            db,
            action="ANPR_RETAKE",
            entity_type="anpr_result",
            entity_id=anpr.id,
            transaction_id=txn.transaction_id,
            actor_user_id=user.id,
            details="Operator requested retake",
        )
        db.commit()
        db.refresh(txn)
        return _txn_out(txn)

    plate = body.vehicle_number or anpr.vehicle_number
    if not plate:
        raise HTTPException(
            status_code=400,
            detail="Vehicle number required. OCR found none — enter manually with reason.",
        )
    plate = normalize_plate(plate)
    manual = body.vehicle_number is not None and (
        anpr.vehicle_number is None or normalize_plate(anpr.vehicle_number) != plate
    )
    if (manual or anpr.status == "FAILED") and not body.manual_reason:
        raise HTTPException(
            status_code=400,
            detail="Manual vehicle override requires a reason (audit).",
        )

    vehicle = db.execute(select(Vehicle).where(Vehicle.vehicle_number == plate)).scalar_one_or_none()
    if vehicle is None:
        vehicle = Vehicle(vehicle_number=plate)
        db.add(vehicle)
        db.flush()

    anpr.confirmed_vehicle_number = plate
    anpr.status = "MANUAL" if manual or anpr.status == "FAILED" else "CONFIRMED"
    anpr.manual_reason = body.manual_reason
    txn.vehicle_id = vehicle.id
    txn.vehicle_number = plate

    if txn.status == TransactionStatus.ENTRY_STARTED.value:
        transition(
            db,
            txn,
            to_status=TransactionStatus.VEHICLE_VERIFIED.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason=body.manual_reason or "Vehicle confirmed",
            lat=body.gps.lat if body.gps else None,
            lon=body.gps.lon if body.gps else None,
            gps_accuracy_m=body.gps.accuracy_m if body.gps else None,
        )

    write_audit(
        db,
        action="VEHICLE_CONFIRMED",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=body.device_id,
        details=f"plate={plate} manual={anpr.status == 'MANUAL'}",
    )
    db.commit()
    db.refresh(txn)
    return _txn_out(txn)


@router.post("/driver", response_model=VehicleTxnOut)
def save_driver(
    body: DriverDetailsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("vehicle.entry")),
) -> VehicleTxnOut:
    txn = _get_txn(db, body.transaction_pk)
    if txn.status not in {
        TransactionStatus.VEHICLE_VERIFIED.value,
        TransactionStatus.ENTRY_STARTED.value,
    }:
        raise HTTPException(status_code=400, detail=f"Driver capture not allowed in status {txn.status}.")

    license = (body.license_no or "").strip() or None
    driver = Driver(
        name=body.driver_name.strip(),
        mobile=body.driver_mobile.strip(),
        license_no=license,
    )
    db.add(driver)
    db.flush()
    txn.driver_id = driver.id
    txn.driver_name = driver.name
    txn.driver_mobile = driver.mobile
    txn.transporter_name = body.transporter_name
    if body.vehicle_type:
        txn.vehicle_type = body.vehicle_type.strip()[:40]
    if body.customer_whatsapp:
        txn.customer_whatsapp = body.customer_whatsapp.strip()[:20]

    if txn.status == TransactionStatus.VEHICLE_VERIFIED.value:
        reason = (
            "Driver recorded; awaiting loaded gross"
            if txn.type == TransactionType.MATERIAL_RECEIVING_INWARD.value
            else "Driver recorded; awaiting tare"
        )
        transition(
            db,
            txn,
            to_status=TransactionStatus.AWAITING_TARE.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason=reason,
        )

    write_audit(
        db,
        action="DRIVER_RECORDED",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=body.device_id,
        details=f"{driver.name} / {driver.mobile}",
    )
    db.commit()
    db.refresh(txn)
    return _txn_out(txn)


@router.post("/exit/detect", response_model=AnprResultOut)
async def exit_detect(
    transaction_pk: str = Form(...),
    gps_lat: float = Form(...),
    gps_lon: float = Form(...),
    gps_accuracy_m: float = Form(...),
    capture_source: str = Form("LIVE_CAMERA"),
    ocr_text: str = Form(...),
    device_id: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("vehicle.exit")),
) -> AnprResultOut:
    _require_gps(gps_lat, gps_lon, gps_accuracy_m)
    txn = _get_txn(db, transaction_pk)

    if txn.status in {
        TransactionStatus.VEHICLE_VERIFIED.value,
        TransactionStatus.AWAITING_TARE.value,
        TransactionStatus.TARE_COMPLETED.value,
        TransactionStatus.LOADING.value,
        TransactionStatus.UNLOADING.value,
        TransactionStatus.GROSS_COMPLETED.value,
        TransactionStatus.DENSITY_PENDING.value,
        TransactionStatus.DOCUMENTS_PENDING.value,
        TransactionStatus.DOCUMENTS_VERIFIED.value,
        TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value,
        TransactionStatus.CUSTOMER_CONFIRMED.value,
        TransactionStatus.APPROVED.value,
    }:
        transition(
            db,
            txn,
            to_status=TransactionStatus.EXIT_PENDING.value,
            actor_user_id=user.id,
            device_id=device_id,
            reason="Moved to exit pending",
            lat=gps_lat,
            lon=gps_lon,
            gps_accuracy_m=gps_accuracy_m,
        )

    if txn.status != TransactionStatus.EXIT_PENDING.value:
        raise HTTPException(status_code=400, detail=f"Exit not allowed in status {txn.status}.")

    photo, image_bytes = await store_evidence_photo(
        db,
        txn=txn,
        user=user,
        upload=image,
        file_type="EXIT_VEHICLE",
        capture_source=capture_source,
        device_id=device_id,
        lat=gps_lat,
        lon=gps_lon,
        accuracy_m=gps_accuracy_m,
    )
    txn.exit_photo_id = photo.id
    recognition = None
    if get_settings().groq_api_key or (get_settings().ai_provider or "").lower().startswith("groq"):
        recognition = recognize_plate_with_groq(image_bytes, ocr_text=ocr_text)
    if recognition is None:
        recognition = get_vehicle_recognition_service().recognize_from_ocr(ocr_text=ocr_text)
    anpr = AnprResult(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        photo_id=photo.id,
        vehicle_number=recognition.value,
        confidence=recognition.confidence,
        provider=recognition.provider,
        status="FAILED" if recognition.failed else "DETECTED",
        actor_user_id=user.id,
    )
    if (
        not recognition.failed
        and txn.vehicle_number
        and recognition.value
        and normalize_plate(recognition.value) != normalize_plate(txn.vehicle_number)
    ):
        anpr.status = "MISMATCH"
    db.add(anpr)
    write_audit(
        db,
        action="EXIT_ANPR_RUN",
        entity_type="anpr_result",
        entity_id=anpr.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"status={anpr.status} plate={recognition.value}",
    )
    db.commit()
    db.refresh(anpr)
    return AnprResultOut(
        id=anpr.id,
        transaction_id=anpr.transaction_id,
        vehicle_number=anpr.vehicle_number,
        confidence=anpr.confidence,
        provider=anpr.provider,
        status=anpr.status,
        message=recognition.message,
        candidates=list(recognition.candidates),
        photo_id=photo.id,
        ocr_raw_preview=(recognition.raw_ocr_text or "")[:500],
    )


@router.post("/exit/confirm", response_model=VehicleTxnOut)
def exit_confirm(
    body: VehicleExitJsonRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("vehicle.exit")),
) -> VehicleTxnOut:
    _require_gps(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = _get_txn(db, body.transaction_pk)
    if txn.status != TransactionStatus.EXIT_PENDING.value:
        raise HTTPException(status_code=400, detail=f"Exit confirm not allowed in status {txn.status}.")

    if body.anpr_result_id:
        anpr = db.get(AnprResult, body.anpr_result_id)
        if anpr and anpr.status == "MISMATCH":
            transition(
                db,
                txn,
                to_status=TransactionStatus.EXCEPTION.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason="Exit ANPR vehicle mismatch",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
            db.commit()
            raise HTTPException(
                status_code=409,
                detail="Exit ANPR does not match entry vehicle. Supervisor approval required.",
            )

    transition(
        db,
        txn,
        to_status=TransactionStatus.EXIT_COMPLETED.value,
        actor_user_id=user.id,
        device_id=body.device_id,
        reason="Exit photo + ANPR recorded",
        lat=body.gps.lat,
        lon=body.gps.lon,
        gps_accuracy_m=body.gps.accuracy_m,
    )

    blocked_complete = False
    block_detail = ""
    if body.complete_transaction:
        blockers = closure_blockers(db, txn)
        if blockers:
            blocked_complete = True
            block_detail = "Cannot complete transaction: " + " | ".join(blockers)
            write_audit(
                db,
                action="CLOSURE_BLOCKED",
                entity_type="transaction",
                entity_id=txn.id,
                transaction_id=txn.transaction_id,
                actor_user_id=user.id,
                device_id=body.device_id,
                details=block_detail,
            )
        else:
            transition(
                db,
                txn,
                to_status=TransactionStatus.COMPLETED.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason="Exit complete — closure checklist passed",
            )

    write_audit(
        db,
        action="VEHICLE_EXIT",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=body.device_id,
        details="Exit confirmed",
    )
    db.commit()
    db.refresh(txn)
    if blocked_complete:
        raise HTTPException(status_code=409, detail=block_detail)
    return _txn_out(txn)


@router.get("/open", response_model=list[VehicleTxnOut])
def list_open_vehicles(
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("transaction.view")),
) -> list[VehicleTxnOut]:
    open_statuses = [
        s.value
        for s in TransactionStatus
        if s
        not in {
            TransactionStatus.COMPLETED,
            TransactionStatus.CANCELLED,
            TransactionStatus.REJECTED,
        }
    ]
    rows = (
        db.execute(
            select(Transaction)
            .where(Transaction.status.in_(open_statuses))
            .order_by(Transaction.created_at.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )
    return [_txn_out(r) for r in rows]
