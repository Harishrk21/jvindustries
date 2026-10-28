"""Phase 3 — tare / gross / net / density / calculated litres (server-authoritative)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.density_recognition import get_density_recognition_service
from app.ai.weighbridge_hardware import get_weighbridge_hardware_client
from app.ai.weighbridge_ocr import get_weighbridge_ocr_service
from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.models.weighment import DensityReading, Weighment
from app.schemas.weighment import (
    DensityConfirmRequest,
    DensityDetectOut,
    DensityOut,
    NetWeightOut,
    WeighmentConfirmRequest,
    WeighmentDetectOut,
    WeighmentOut,
    WeighmentSummaryOut,
)
from app.services.audit_service import write_audit
from app.services.calculations import CalculationError, compute_calculated_litres, compute_net_kg
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.photo_service import store_evidence_photo
from app.services.transaction_flow import transition

router = APIRouter()


def _gps_ok(lat: float, lon: float, acc: float) -> None:
    result = GeofenceService().verify(GpsSample(lat, lon, acc))
    if not result.authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.message)


def _txn(db: Session, pk: str) -> Transaction:
    txn = db.get(Transaction, pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return txn


@router.post("/detect", response_model=WeighmentDetectOut)
async def detect_weighment(
    transaction_pk: str = Form(...),
    kind: str = Form(...),
    gps_lat: float = Form(...),
    gps_lon: float = Form(...),
    gps_accuracy_m: float = Form(...),
    capture_source: str = Form("LIVE_CAMERA"),
    ocr_text: str = Form(...),
    device_id: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("weighment.tare", "weighment.gross")),
) -> WeighmentDetectOut:
    kind = kind.upper()
    if kind not in {"TARE", "GROSS"}:
        raise HTTPException(status_code=400, detail="kind must be TARE or GROSS.")
    if kind == "GROSS":
        # same permission family; gross also allowed for weighbridge operators
        pass

    _gps_ok(gps_lat, gps_lon, gps_accuracy_m)
    txn = _txn(db, transaction_pk)

    inward = txn.type == TransactionType.MATERIAL_RECEIVING_INWARD.value
    if kind == "TARE":
        tare_ok = txn.status in {
            TransactionStatus.AWAITING_TARE.value,
            TransactionStatus.VEHICLE_VERIFIED.value,
        }
        # Inward: empty weigh after loaded gross (status UNLOADING, gross already set)
        if inward and txn.status == TransactionStatus.UNLOADING.value and txn.gross_kg is not None:
            tare_ok = True
        if not tare_ok:
            raise HTTPException(status_code=400, detail=f"Tare not allowed in status {txn.status}.")
    if kind == "GROSS":
        gross_ok = txn.status in {
            TransactionStatus.LOADING.value,
            TransactionStatus.UNLOADING.value,
            TransactionStatus.TARE_COMPLETED.value,
        }
        # Inward: loaded weigh first (before tare)
        if inward and txn.status in {
            TransactionStatus.AWAITING_TARE.value,
            TransactionStatus.VEHICLE_VERIFIED.value,
        }:
            gross_ok = True
        if not gross_ok:
            raise HTTPException(status_code=400, detail=f"Gross not allowed in status {txn.status}.")

    photo, _image_bytes = await store_evidence_photo(
        db,
        txn=txn,
        user=user,
        upload=image,
        file_type=f"WEIGHBRIDGE_{kind}",
        capture_source=capture_source,
        device_id=device_id,
        lat=gps_lat,
        lon=gps_lon,
        accuracy_m=gps_accuracy_m,
    )

    hw = get_weighbridge_hardware_client().read_weight()
    ocr = get_weighbridge_ocr_service().recognize_from_ocr(ocr_text=ocr_text)

    write_audit(
        db,
        action="WEIGHBRIDGE_OCR",
        entity_type="photo",
        entity_id=photo.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=device_id,
        details=f"kind={kind} failed={ocr.failed} detected={ocr.value_kg} hw={hw.weight_kg if hw else None}",
    )
    db.commit()

    return WeighmentDetectOut(
        transaction_id=txn.transaction_id,
        kind=kind,
        detected_weight_kg=ocr.value_kg if not ocr.failed else None,
        confidence=ocr.confidence,
        provider=ocr.provider,
        failed=ocr.failed,
        message=ocr.message,
        candidates_kg=list(ocr.candidates_kg),
        photo_id=photo.id,
        hardware_weight_kg=hw.weight_kg if hw else None,
        ocr_raw_preview=(ocr.raw_ocr_text or "")[:500],
    )


@router.post("/confirm", response_model=WeighmentSummaryOut)
def confirm_weighment(
    body: WeighmentConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("weighment.tare", "weighment.gross")),
) -> WeighmentSummaryOut:
    kind = body.kind.upper()
    if kind not in {"TARE", "GROSS"}:
        raise HTTPException(status_code=400, detail="kind must be TARE or GROSS.")

    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = _txn(db, body.transaction_pk)

    existing = db.execute(
        select(Weighment).where(Weighment.transaction_pk == txn.id, Weighment.kind == kind)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"{kind} already confirmed. Corrections require supervisor approval workflow.",
        )

    row = Weighment(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        kind=kind,
        weight_kg=float(body.confirmed_weight_kg),
        ocr_weight_kg=body.ocr_weight_kg,
        ocr_confidence=body.ocr_confidence,
        ocr_provider=body.ocr_provider,
        ocr_raw_text=body.ocr_raw_text,
        photo_id=body.photo_id,
        confirmed_by=user.id,
    )
    db.add(row)

    inward = txn.type == TransactionType.MATERIAL_RECEIVING_INWARD.value

    if kind == "TARE":
        txn.tare_kg = row.weight_kg
        # Inward path: tare after loaded gross → compute net and finish weigh pair
        if inward and txn.gross_kg is not None:
            try:
                net = compute_net_kg(tare_kg=row.weight_kg, gross_kg=txn.gross_kg)
            except CalculationError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            txn.net_kg = net
            if txn.status == TransactionStatus.UNLOADING.value:
                transition(
                    db,
                    txn,
                    to_status=TransactionStatus.TARE_COMPLETED.value,
                    actor_user_id=user.id,
                    device_id=body.device_id,
                    reason=f"Inward tare (empty) {row.weight_kg} kg",
                    lat=body.gps.lat,
                    lon=body.gps.lon,
                    gps_accuracy_m=body.gps.accuracy_m,
                )
            transition(
                db,
                txn,
                to_status=TransactionStatus.GROSS_COMPLETED.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason=f"Inward net={net} kg (gross={txn.gross_kg}, tare={row.weight_kg})",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
            transition(
                db,
                txn,
                to_status=TransactionStatus.DENSITY_PENDING.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason="Awaiting density for calculated litres",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
        else:
            if txn.status == TransactionStatus.VEHICLE_VERIFIED.value:
                transition(
                    db,
                    txn,
                    to_status=TransactionStatus.AWAITING_TARE.value,
                    actor_user_id=user.id,
                    device_id=body.device_id,
                    reason="Preparing tare",
                    lat=body.gps.lat,
                    lon=body.gps.lon,
                    gps_accuracy_m=body.gps.accuracy_m,
                )
            transition(
                db,
                txn,
                to_status=TransactionStatus.TARE_COMPLETED.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason=f"Tare confirmed {row.weight_kg} kg",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
            mode = (body.after_tare_mode or "LOADING").upper()
            if mode not in {"LOADING", "UNLOADING"}:
                mode = "LOADING"
            next_status = (
                TransactionStatus.LOADING.value if mode == "LOADING" else TransactionStatus.UNLOADING.value
            )
            transition(
                db,
                txn,
                to_status=next_status,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason=f"After tare → {mode}",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
    else:
        # GROSS
        if inward and txn.tare_kg is None:
            # Loaded arrival: record gross, wait for empty tare after unload
            txn.gross_kg = row.weight_kg
            if txn.status == TransactionStatus.VEHICLE_VERIFIED.value:
                transition(
                    db,
                    txn,
                    to_status=TransactionStatus.AWAITING_TARE.value,
                    actor_user_id=user.id,
                    device_id=body.device_id,
                    reason="Preparing inward gross",
                    lat=body.gps.lat,
                    lon=body.gps.lon,
                    gps_accuracy_m=body.gps.accuracy_m,
                )
            transition(
                db,
                txn,
                to_status=TransactionStatus.UNLOADING.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason=f"Inward gross (loaded) {row.weight_kg} kg; unload then tare",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
        else:
            if txn.tare_kg is None:
                raise HTTPException(status_code=400, detail="Tare must be completed before gross.")
            try:
                net = compute_net_kg(tare_kg=txn.tare_kg, gross_kg=row.weight_kg)
            except CalculationError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            txn.gross_kg = row.weight_kg
            txn.net_kg = net
            transition(
                db,
                txn,
                to_status=TransactionStatus.GROSS_COMPLETED.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason=f"Gross confirmed {row.weight_kg} kg; net={net}",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
            transition(
                db,
                txn,
                to_status=TransactionStatus.DENSITY_PENDING.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason="Awaiting density for calculated litres",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )

    write_audit(
        db,
        action=f"WEIGHMENT_{kind}_CONFIRMED",
        entity_type="weighment",
        entity_id=row.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=body.device_id,
        details=f"{kind}={row.weight_kg} net={txn.net_kg}",
    )
    db.commit()
    db.refresh(txn)
    return _summary(txn)


@router.post("/density/detect", response_model=DensityDetectOut)
async def detect_density(
    transaction_pk: str = Form(...),
    gps_lat: float = Form(...),
    gps_lon: float = Form(...),
    gps_accuracy_m: float = Form(...),
    capture_source: str = Form("LIVE_CAMERA"),
    ocr_text: str = Form(...),
    device_id: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("weighment.tare", "weighment.gross")),
) -> DensityDetectOut:
    _gps_ok(gps_lat, gps_lon, gps_accuracy_m)
    txn = _txn(db, transaction_pk)
    if txn.status not in {
        TransactionStatus.DENSITY_PENDING.value,
        TransactionStatus.GROSS_COMPLETED.value,
    }:
        raise HTTPException(status_code=400, detail=f"Density not allowed in status {txn.status}.")

    photo, _image_bytes = await store_evidence_photo(
        db,
        txn=txn,
        user=user,
        upload=image,
        file_type="DENSITY_HYDROMETER",
        capture_source=capture_source,
        device_id=device_id,
        lat=gps_lat,
        lon=gps_lon,
        accuracy_m=gps_accuracy_m,
    )
    ocr = get_density_recognition_service().recognize_from_ocr(ocr_text=ocr_text)
    write_audit(
        db,
        action="DENSITY_OCR",
        entity_type="photo",
        entity_id=photo.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"failed={ocr.failed} density={ocr.density_kg_per_l} temp={ocr.temperature_c}",
    )
    db.commit()
    return DensityDetectOut(
        transaction_id=txn.transaction_id,
        detected_density=ocr.density_kg_per_l,
        detected_temperature_c=ocr.temperature_c,
        confidence=ocr.confidence,
        provider=ocr.provider,
        failed=ocr.failed,
        message=ocr.message,
        photo_id=photo.id,
        ocr_raw_preview=(ocr.raw_ocr_text or "")[:500],
    )


@router.post("/density/confirm", response_model=DensityOut)
def confirm_density(
    body: DensityConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("weighment.tare", "weighment.gross", "approval.act")),
) -> DensityOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = _txn(db, body.transaction_pk)
    if txn.net_kg is None:
        raise HTTPException(status_code=400, detail="Net weight required before density confirmation.")

    if body.require_supervisor_if_low_confidence and body.ocr_confidence is not None and body.ocr_confidence < 0.55:
        perms = user.permission_codes()
        if "approval.act" not in perms and "owner.full" not in perms:
            raise HTTPException(
                status_code=403,
                detail="Low OCR confidence — supervisor confirmation required.",
            )

    try:
        litres = compute_calculated_litres(net_kg=txn.net_kg, density_kg_per_l=body.confirmed_density)
    except CalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    reading = DensityReading(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        density_kg_per_l=body.confirmed_density,
        temperature_c=body.confirmed_temperature_c,
        calculated_litres=litres,
        net_kg_snapshot=txn.net_kg,
        ocr_density=body.ocr_density,
        ocr_temperature=body.ocr_temperature,
        ocr_confidence=body.ocr_confidence,
        ocr_provider=body.ocr_provider,
        ocr_raw_text=body.ocr_raw_text,
        photo_id=body.photo_id,
        confirmed_by=user.id,
    )
    db.add(reading)
    txn.density_kg_per_l = reading.density_kg_per_l
    txn.temperature_c = reading.temperature_c
    txn.calculated_litres = litres

    if txn.status == TransactionStatus.GROSS_COMPLETED.value:
        transition(
            db,
            txn,
            to_status=TransactionStatus.DENSITY_PENDING.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason="Density capture",
            lat=body.gps.lat,
            lon=body.gps.lon,
            gps_accuracy_m=body.gps.accuracy_m,
        )
    if txn.status == TransactionStatus.DENSITY_PENDING.value:
        transition(
            db,
            txn,
            to_status=TransactionStatus.DOCUMENTS_PENDING.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason=f"Density confirmed; calculated litres={litres} (CALCULATED QUANTITY)",
            lat=body.gps.lat,
            lon=body.gps.lon,
            gps_accuracy_m=body.gps.accuracy_m,
        )

    write_audit(
        db,
        action="DENSITY_CONFIRMED",
        entity_type="density_reading",
        entity_id=reading.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"density={reading.density_kg_per_l} temp={reading.temperature_c} litres={litres}",
    )
    db.commit()
    db.refresh(reading)
    return DensityOut.model_validate(reading)


@router.get("/summary/{transaction_pk}", response_model=WeighmentSummaryOut)
def weighment_summary(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("transaction.view")),
) -> WeighmentSummaryOut:
    return _summary(_txn(db, transaction_pk))


@router.get("/net/{transaction_pk}", response_model=NetWeightOut)
def net_weight(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("transaction.view")),
) -> NetWeightOut:
    txn = _txn(db, transaction_pk)
    if txn.tare_kg is None or txn.gross_kg is None or txn.net_kg is None:
        raise HTTPException(status_code=400, detail="Tare and gross not both confirmed yet.")
    # Recalculate server-side to prove authority
    net = compute_net_kg(tare_kg=txn.tare_kg, gross_kg=txn.gross_kg)
    if abs(net - txn.net_kg) > 0.001:
        txn.net_kg = net
        db.commit()
    return NetWeightOut(
        transaction_id=txn.transaction_id,
        tare_kg=txn.tare_kg,
        gross_kg=txn.gross_kg,
        net_kg=net,
        status=txn.status,
    )


def _summary(txn: Transaction) -> WeighmentSummaryOut:
    return WeighmentSummaryOut(
        transaction_id=txn.transaction_id,
        status=txn.status,
        tare_kg=txn.tare_kg,
        gross_kg=txn.gross_kg,
        net_kg=txn.net_kg,
        density_kg_per_l=txn.density_kg_per_l,
        temperature_c=txn.temperature_c,
        calculated_litres=txn.calculated_litres,
    )
