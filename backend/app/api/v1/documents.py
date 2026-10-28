"""Phase 4 — Invoice + E-Way Bill capture, OCR confirm, vehicle mismatch."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.eway_ocr import get_eway_ocr_service
from app.ai.invoice_ocr import get_invoice_ocr_service
from app.ai.vehicle_recognition import normalize_plate
from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.documents import DocumentVerification, EwayBill, Invoice
from app.models.enums import TransactionStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.documents import (
    DocumentStatusOut,
    EwayConfirmRequest,
    EwayDetectOut,
    InvoiceConfirmRequest,
    InvoiceDetectOut,
    MismatchApproveRequest,
)
from app.services.audit_service import write_audit
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.notify_service import create_alert
from app.services.photo_service import store_evidence_photo
from app.services.transaction_flow import transition
from app.services.vehicle_match import compare_vehicles

router = APIRouter()

_DOC_CAPTURE_STATUSES = {
    TransactionStatus.VEHICLE_VERIFIED.value,
    TransactionStatus.AWAITING_TARE.value,
    TransactionStatus.TARE_COMPLETED.value,
    TransactionStatus.LOADING.value,
    TransactionStatus.UNLOADING.value,
    TransactionStatus.GROSS_COMPLETED.value,
    TransactionStatus.DENSITY_PENDING.value,
    TransactionStatus.DOCUMENTS_PENDING.value,
    TransactionStatus.APPROVAL_PENDING.value,
    TransactionStatus.EXCEPTION.value,
}


def _gps_ok(lat: float, lon: float, acc: float) -> None:
    result = GeofenceService().verify(GpsSample(lat, lon, acc))
    if not result.authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.message)


def _txn(db: Session, pk: str) -> Transaction:
    txn = db.get(Transaction, pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return txn


def _ensure_documents_pending(db: Session, txn: Transaction, user: User, device_id: str | None, gps) -> None:
    if txn.status == TransactionStatus.DOCUMENTS_PENDING.value:
        return
    if txn.status not in _DOC_CAPTURE_STATUSES:
        raise HTTPException(status_code=400, detail=f"Documents not allowed in status {txn.status}.")
    # Only pull into DOCUMENTS_PENDING after weigh/density — never steal AWAITING_TARE / LOADING.
    if txn.status in {
        TransactionStatus.GROSS_COMPLETED.value,
        TransactionStatus.DENSITY_PENDING.value,
    }:
        try:
            transition(
                db,
                txn,
                to_status=TransactionStatus.DOCUMENTS_PENDING.value,
                actor_user_id=user.id,
                device_id=device_id,
                reason="Post-load document capture started",
                lat=gps.lat if gps else None,
                lon=gps.lon if gps else None,
                gps_accuracy_m=gps.accuracy_m if gps else None,
            )
        except ValueError:
            pass


def _latest_invoice(db: Session, txn_pk: str) -> Invoice | None:
    return (
        db.execute(
            select(Invoice).where(Invoice.transaction_pk == txn_pk).order_by(Invoice.created_at.desc())
        )
        .scalars()
        .first()
    )


def _latest_eway(db: Session, txn_pk: str) -> EwayBill | None:
    return (
        db.execute(
            select(EwayBill).where(EwayBill.transaction_pk == txn_pk).order_by(EwayBill.created_at.desc())
        )
        .scalars()
        .first()
    )


def _run_verification(db: Session, txn: Transaction, user: User, device_id: str | None) -> DocumentVerification:
    inv = _latest_invoice(db, txn.id)
    ewb = _latest_eway(db, txn.id)
    result = compare_vehicles(
        anpr_vehicle=txn.vehicle_number,
        invoice_vehicle=inv.vehicle_number if inv and inv.confirmed else None,
        eway_vehicle=ewb.vehicle_number if ewb and ewb.confirmed else None,
    )
    row = DocumentVerification(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        anpr_vehicle=result.anpr_vehicle,
        invoice_vehicle=result.invoice_vehicle,
        eway_vehicle=result.eway_vehicle,
        match_status=result.match_status,
        mismatch_reason=result.reason,
        approved=result.match_status == "MATCH",
    )
    db.add(row)
    db.flush()

    inv_ok = bool(inv and inv.confirmed)
    ewb_ok = bool(ewb and ewb.confirmed)

    if inv_ok and ewb_ok:
        if result.match_status == "MATCH":
            if txn.status in {
                TransactionStatus.DOCUMENTS_PENDING.value,
                TransactionStatus.EXCEPTION.value,
                TransactionStatus.APPROVAL_PENDING.value,
            }:
                if txn.status != TransactionStatus.DOCUMENTS_PENDING.value:
                    # from EXCEPTION/APPROVAL may need path — try direct
                    pass
                try:
                    if txn.status == TransactionStatus.DOCUMENTS_PENDING.value:
                        transition(
                            db,
                            txn,
                            to_status=TransactionStatus.DOCUMENTS_VERIFIED.value,
                            actor_user_id=user.id,
                            device_id=device_id,
                            reason="Invoice + E-Way verified; vehicles MATCH",
                        )
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
        elif result.match_status == "MISMATCH":
            create_alert(
                db,
                category="APPROVAL",
                severity="CRITICAL",
                title="Vehicle document mismatch",
                body=result.reason or "ANPR / invoice / E-Way vehicle numbers do not match.",
                transaction_pk=txn.id,
                transaction_id=txn.transaction_id,
                entity_type="document_verification",
                entity_id=row.id,
                created_by=user.id,
                send_whatsapp=True,
            )
            target = TransactionStatus.APPROVAL_PENDING.value
            try:
                if txn.status == TransactionStatus.DOCUMENTS_PENDING.value:
                    transition(
                        db,
                        txn,
                        to_status=target,
                        actor_user_id=user.id,
                        device_id=device_id,
                        reason=result.reason or "Vehicle document mismatch",
                    )
                elif txn.status not in {TransactionStatus.APPROVAL_PENDING.value, TransactionStatus.EXCEPTION.value}:
                    transition(
                        db,
                        txn,
                        to_status=TransactionStatus.EXCEPTION.value,
                        actor_user_id=user.id,
                        device_id=device_id,
                        reason=result.reason or "Vehicle document mismatch",
                    )
            except ValueError:
                txn.status = TransactionStatus.APPROVAL_PENDING.value

    write_audit(
        db,
        action="DOCUMENT_VEHICLE_CHECK",
        entity_type="document_verification",
        entity_id=row.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=device_id,
        details=f"{result.match_status} {result.reason or ''}".strip(),
    )
    return row


@router.post("/invoice/detect", response_model=InvoiceDetectOut)
async def detect_invoice(
    transaction_pk: str = Form(...),
    gps_lat: float = Form(...),
    gps_lon: float = Form(...),
    gps_accuracy_m: float = Form(...),
    capture_source: str = Form("LIVE_CAMERA"),
    ocr_text: str = Form(...),
    device_id: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("document.invoice.capture", "transaction.create")),
) -> InvoiceDetectOut:
    _gps_ok(gps_lat, gps_lon, gps_accuracy_m)
    txn = _txn(db, transaction_pk)
    class _G:
        lat = gps_lat
        lon = gps_lon
        accuracy_m = gps_accuracy_m

    _ensure_documents_pending(db, txn, user, device_id, _G)

    photo, _image_bytes = await store_evidence_photo(
        db,
        txn=txn,
        user=user,
        upload=image,
        file_type="INVOICE",
        capture_source=capture_source,
        device_id=device_id,
        lat=gps_lat,
        lon=gps_lon,
        accuracy_m=gps_accuracy_m,
    )
    ocr = get_invoice_ocr_service().recognize_from_ocr(ocr_text=ocr_text)
    inv = Invoice(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        photo_id=photo.id,
        invoice_number=ocr.fields.get("invoice_number"),
        invoice_date=ocr.fields.get("invoice_date"),
        supplier_name=ocr.fields.get("supplier_name"),
        customer_name=ocr.fields.get("customer_name"),
        gstin=ocr.fields.get("gstin"),
        product_name=ocr.fields.get("product_name"),
        hsn=ocr.fields.get("hsn"),
        quantity=ocr.fields.get("quantity"),
        unit=ocr.fields.get("unit"),
        rate=ocr.fields.get("rate"),
        tax=ocr.fields.get("tax"),
        total=ocr.fields.get("total"),
        vehicle_number=ocr.fields.get("vehicle_number"),
        ocr_raw_text=ocr.raw_ocr_text,
        ocr_confidence=ocr.confidence,
        ocr_provider=ocr.provider,
        confirmed=False,
    )
    db.add(inv)
    write_audit(
        db,
        action="INVOICE_OCR",
        entity_type="invoice",
        entity_id=inv.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"failed={ocr.failed} inv={inv.invoice_number}",
    )
    db.commit()
    db.refresh(inv)
    return InvoiceDetectOut(
        id=inv.id,
        transaction_id=txn.transaction_id,
        photo_id=photo.id,
        fields=ocr.fields,
        confidence=ocr.confidence,
        provider=ocr.provider,
        failed=ocr.failed,
        message=ocr.message,
        vehicle_candidates=ocr.vehicle_candidates,
        ocr_raw_preview=(ocr.raw_ocr_text or "")[:500],
    )


@router.post("/invoice/confirm", response_model=DocumentStatusOut)
def confirm_invoice(
    body: InvoiceConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("document.invoice.capture", "document.confirm", "transaction.create")),
) -> DocumentStatusOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = _txn(db, body.transaction_pk)
    inv = db.get(Invoice, body.invoice_id)
    if inv is None or inv.transaction_pk != txn.id:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    inv.invoice_number = body.invoice_number or inv.invoice_number
    inv.invoice_date = body.invoice_date or inv.invoice_date
    inv.supplier_name = body.supplier_name or inv.supplier_name
    inv.customer_name = body.customer_name or inv.customer_name
    inv.gstin = body.gstin or inv.gstin
    inv.product_name = body.product_name or inv.product_name
    inv.hsn = body.hsn or inv.hsn
    inv.quantity = body.quantity or inv.quantity
    inv.unit = body.unit or inv.unit
    inv.rate = body.rate or inv.rate
    inv.tax = body.tax or inv.tax
    inv.total = body.total or inv.total
    if body.vehicle_number:
        inv.vehicle_number = normalize_plate(body.vehicle_number)
    inv.confirmed = True
    inv.confirmed_by = user.id

    if not inv.invoice_number:
        raise HTTPException(status_code=400, detail="Invoice number is required to confirm.")

    ver = _run_verification(db, txn, user, body.device_id)
    write_audit(
        db,
        action="INVOICE_CONFIRMED",
        entity_type="invoice",
        entity_id=inv.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=inv.invoice_number,
    )
    db.commit()
    return _status(db, txn, ver)


@router.post("/eway/detect", response_model=EwayDetectOut)
async def detect_eway(
    transaction_pk: str = Form(...),
    gps_lat: float = Form(...),
    gps_lon: float = Form(...),
    gps_accuracy_m: float = Form(...),
    capture_source: str = Form("LIVE_CAMERA"),
    ocr_text: str = Form(...),
    device_id: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("document.eway.capture", "transaction.create")),
) -> EwayDetectOut:
    _gps_ok(gps_lat, gps_lon, gps_accuracy_m)
    txn = _txn(db, transaction_pk)

    class _G:
        lat = gps_lat
        lon = gps_lon
        accuracy_m = gps_accuracy_m

    _ensure_documents_pending(db, txn, user, device_id, _G)

    photo, _image_bytes = await store_evidence_photo(
        db,
        txn=txn,
        user=user,
        upload=image,
        file_type="EWAY_BILL",
        capture_source=capture_source,
        device_id=device_id,
        lat=gps_lat,
        lon=gps_lon,
        accuracy_m=gps_accuracy_m,
    )
    ocr = get_eway_ocr_service().recognize_from_ocr(ocr_text=ocr_text)
    ewb = EwayBill(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        photo_id=photo.id,
        eway_bill_number=ocr.fields.get("eway_bill_number"),
        eway_date=ocr.fields.get("eway_date"),
        validity=ocr.fields.get("validity"),
        supplier_name=ocr.fields.get("supplier_name"),
        consignee_name=ocr.fields.get("consignee_name"),
        gstin=ocr.fields.get("gstin"),
        vehicle_number=ocr.fields.get("vehicle_number"),
        product_name=ocr.fields.get("product_name"),
        hsn=ocr.fields.get("hsn"),
        quantity=ocr.fields.get("quantity"),
        transporter_name=ocr.fields.get("transporter_name"),
        from_place=ocr.fields.get("from_place"),
        to_place=ocr.fields.get("to_place"),
        ocr_raw_text=ocr.raw_ocr_text,
        ocr_confidence=ocr.confidence,
        ocr_provider=ocr.provider,
        confirmed=False,
    )
    db.add(ewb)
    write_audit(
        db,
        action="EWAY_OCR",
        entity_type="eway_bill",
        entity_id=ewb.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"failed={ocr.failed} ewb={ewb.eway_bill_number}",
    )
    db.commit()
    db.refresh(ewb)
    return EwayDetectOut(
        id=ewb.id,
        transaction_id=txn.transaction_id,
        photo_id=photo.id,
        fields=ocr.fields,
        confidence=ocr.confidence,
        provider=ocr.provider,
        failed=ocr.failed,
        message=ocr.message,
        vehicle_candidates=ocr.vehicle_candidates,
        ocr_raw_preview=(ocr.raw_ocr_text or "")[:500],
    )


@router.post("/eway/confirm", response_model=DocumentStatusOut)
def confirm_eway(
    body: EwayConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("document.eway.capture", "document.confirm", "transaction.create")),
) -> DocumentStatusOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = _txn(db, body.transaction_pk)
    ewb = db.get(EwayBill, body.eway_id)
    if ewb is None or ewb.transaction_pk != txn.id:
        raise HTTPException(status_code=404, detail="E-Way Bill not found.")

    ewb.eway_bill_number = body.eway_bill_number or ewb.eway_bill_number
    ewb.eway_date = body.eway_date or ewb.eway_date
    ewb.validity = body.validity or ewb.validity
    ewb.supplier_name = body.supplier_name or ewb.supplier_name
    ewb.consignee_name = body.consignee_name or ewb.consignee_name
    ewb.gstin = body.gstin or ewb.gstin
    if body.vehicle_number:
        ewb.vehicle_number = normalize_plate(body.vehicle_number)
    ewb.product_name = body.product_name or ewb.product_name
    ewb.hsn = body.hsn or ewb.hsn
    ewb.quantity = body.quantity or ewb.quantity
    ewb.transporter_name = body.transporter_name or ewb.transporter_name
    ewb.from_place = body.from_place or ewb.from_place
    ewb.to_place = body.to_place or ewb.to_place
    ewb.confirmed = True
    ewb.confirmed_by = user.id

    if not ewb.eway_bill_number:
        raise HTTPException(status_code=400, detail="E-Way Bill number is required to confirm.")

    ver = _run_verification(db, txn, user, body.device_id)
    write_audit(
        db,
        action="EWAY_CONFIRMED",
        entity_type="eway_bill",
        entity_id=ewb.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=ewb.eway_bill_number,
    )
    db.commit()
    return _status(db, txn, ver)


@router.post("/mismatch/approve", response_model=DocumentStatusOut)
def approve_mismatch(
    body: MismatchApproveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("approval.act")),
) -> DocumentStatusOut:
    txn = _txn(db, body.transaction_pk)
    ver = db.get(DocumentVerification, body.verification_id)
    if ver is None or ver.transaction_pk != txn.id:
        raise HTTPException(status_code=404, detail="Verification record not found.")
    if ver.match_status != "MISMATCH":
        raise HTTPException(status_code=400, detail="Only MISMATCH records need approval.")

    ver.approved = True
    ver.approved_by = user.id
    ver.approval_note = body.approval_note

    if txn.status in {
        TransactionStatus.APPROVAL_PENDING.value,
        TransactionStatus.EXCEPTION.value,
        TransactionStatus.DOCUMENTS_PENDING.value,
    }:
        transition(
            db,
            txn,
            to_status=TransactionStatus.DOCUMENTS_VERIFIED.value,
            actor_user_id=user.id,
            device_id=body.device_id,
            reason=f"Owner/Supervisor approved mismatch: {body.approval_note}",
        )

    write_audit(
        db,
        action="DOCUMENT_MISMATCH_APPROVED",
        entity_type="document_verification",
        entity_id=ver.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=body.approval_note,
    )
    db.commit()
    return _status(db, txn, ver)


@router.get("/status/{transaction_pk}", response_model=DocumentStatusOut)
def document_status(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("transaction.view")),
) -> DocumentStatusOut:
    txn = _txn(db, transaction_pk)
    ver = (
        db.execute(
            select(DocumentVerification)
            .where(DocumentVerification.transaction_pk == txn.id)
            .order_by(DocumentVerification.created_at.desc())
        )
        .scalars()
        .first()
    )
    return _status(db, txn, ver)


def _status(db: Session, txn: Transaction, ver: DocumentVerification | None) -> DocumentStatusOut:
    inv = _latest_invoice(db, txn.id)
    ewb = _latest_eway(db, txn.id)
    return DocumentStatusOut(
        transaction_id=txn.transaction_id,
        status=txn.status,
        invoice_confirmed=bool(inv and inv.confirmed),
        eway_confirmed=bool(ewb and ewb.confirmed),
        anpr_vehicle=txn.vehicle_number,
        invoice_vehicle=inv.vehicle_number if inv else None,
        eway_vehicle=ewb.vehicle_number if ewb else None,
        match_status=ver.match_status if ver else None,
        mismatch_reason=ver.mismatch_reason if ver else None,
        verification_id=ver.id if ver else None,
    )
