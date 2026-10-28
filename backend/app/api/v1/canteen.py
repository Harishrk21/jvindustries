"""Phase 9 — Canteen purchase OCR confirm + stock."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.canteen_ocr import parse_canteen_ocr
from app.core.database import get_db
from app.core.deps import require_any_permission
from app.models.canteen import CanteenItem, CanteenPurchase, CanteenPurchaseLine, CanteenStockMovement
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.canteen import (
    CanteenBalanceOut,
    CanteenConfirmRequest,
    CanteenDetectOut,
    CanteenItemOut,
    CanteenPurchaseOut,
)
from app.services.audit_service import write_audit
from app.services.canteen_stock import compute_balances
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.photo_service import store_evidence_photo
from app.services.transaction_flow import transition
from app.services.transaction_id import next_transaction_id

router = APIRouter()


def _gps_ok(lat: float, lon: float, acc: float) -> None:
    result = GeofenceService().verify(GpsSample(lat, lon, acc))
    if not result.authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.message)


def _item_by_code(db: Session, code: str) -> CanteenItem | None:
    return db.execute(select(CanteenItem).where(CanteenItem.code == code.upper())).scalar_one_or_none()


def _purchase_out(db: Session, purchase: CanteenPurchase, txn: Transaction) -> CanteenPurchaseOut:
    lines = list(
        db.execute(select(CanteenPurchaseLine).where(CanteenPurchaseLine.purchase_id == purchase.id))
        .scalars()
        .all()
    )
    stocked = (
        db.execute(
            select(CanteenStockMovement).where(CanteenStockMovement.purchase_id == purchase.id).limit(1)
        ).scalar_one_or_none()
        is not None
    )
    return CanteenPurchaseOut(
        id=purchase.id,
        transaction_id=txn.transaction_id,
        transaction_pk=txn.id,
        status=purchase.status,
        invoice_number=purchase.invoice_number,
        supplier_name=purchase.supplier_name,
        invoice_total=purchase.invoice_total,
        photo_id=purchase.photo_id,
        lines=[
            {
                "item_id": ln.item_id,
                "item_code": ln.item_code,
                "item_name": ln.item_name,
                "quantity": ln.quantity,
                "unit": ln.unit,
            }
            for ln in lines
        ],
        stock_posted=stocked,
        created_at=purchase.created_at,
    )


@router.get("/items", response_model=list[CanteenItemOut])
def list_items(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("canteen.purchase", "canteen.stock")),
) -> list[CanteenItem]:
    return list(db.execute(select(CanteenItem).where(CanteenItem.active.is_(True)).order_by(CanteenItem.code)).scalars().all())


@router.get("/balances", response_model=list[CanteenBalanceOut])
def balances(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("canteen.stock", "canteen.purchase")),
) -> list[CanteenBalanceOut]:
    return [CanteenBalanceOut(**b.__dict__) for b in compute_balances(db)]


@router.post("/purchase/start", response_model=dict, status_code=status.HTTP_201_CREATED)
def start_purchase(
    gps_lat: float = Form(...),
    gps_lon: float = Form(...),
    gps_accuracy_m: float = Form(...),
    device_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("canteen.purchase", "transaction.create")),
) -> dict:
    _gps_ok(gps_lat, gps_lon, gps_accuracy_m)
    txn = Transaction(
        transaction_id=next_transaction_id(db),
        type=TransactionType.CANTEEN_PURCHASE.value,
        status=TransactionStatus.DRAFT.value,
        created_by=user.id,
        device_id=device_id,
        geofence_ok=True,
        last_lat=gps_lat,
        last_lon=gps_lon,
        last_gps_accuracy_m=gps_accuracy_m,
    )
    db.add(txn)
    db.flush()
    transition(
        db,
        txn,
        to_status=TransactionStatus.ENTRY_STARTED.value,
        actor_user_id=user.id,
        device_id=device_id,
        reason="Canteen purchase started",
        lat=gps_lat,
        lon=gps_lon,
        gps_accuracy_m=gps_accuracy_m,
    )
    write_audit(
        db,
        action="CANTEEN_PURCHASE_STARTED",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
    )
    db.commit()
    db.refresh(txn)
    return {"id": txn.id, "transaction_id": txn.transaction_id, "status": txn.status}


@router.post("/purchase/detect", response_model=CanteenDetectOut)
async def detect_purchase(
    transaction_pk: str = Form(...),
    gps_lat: float = Form(...),
    gps_lon: float = Form(...),
    gps_accuracy_m: float = Form(...),
    capture_source: str = Form("LIVE_CAMERA"),
    ocr_text: str = Form(...),
    device_id: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("canteen.purchase", "photo.live")),
) -> CanteenDetectOut:
    _gps_ok(gps_lat, gps_lon, gps_accuracy_m)
    txn = db.get(Transaction, transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if txn.type != TransactionType.CANTEEN_PURCHASE.value:
        raise HTTPException(status_code=400, detail="Not a canteen purchase transaction.")

    photo, _image_bytes = await store_evidence_photo(
        db,
        txn=txn,
        user=user,
        upload=image,
        file_type="CANTEEN_INVOICE",
        capture_source=capture_source,
        device_id=device_id,
        lat=gps_lat,
        lon=gps_lon,
        accuracy_m=gps_accuracy_m,
    )
    ocr = parse_canteen_ocr(ocr_text)
    purchase = CanteenPurchase(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        photo_id=photo.id,
        supplier_name=ocr.supplier_name,
        invoice_number=ocr.invoice_number,
        invoice_total=ocr.invoice_total,
        ocr_raw_text=ocr.raw_ocr_text,
        ocr_confidence=ocr.confidence,
        ocr_provider=ocr.provider,
        status="DETECTED",
        created_by=user.id,
    )
    db.add(purchase)
    db.flush()

    line_dicts = []
    for ln in ocr.lines:
        item = _item_by_code(db, ln.item_code)
        row = CanteenPurchaseLine(
            purchase_id=purchase.id,
            item_id=item.id if item else None,
            item_code=ln.item_code,
            item_name=ln.item_name,
            quantity=ln.quantity,
            unit=ln.unit,
            ocr_matched=item is not None,
        )
        db.add(row)
        line_dicts.append(
            {
                "item_id": item.id if item else None,
                "item_code": ln.item_code,
                "item_name": ln.item_name,
                "quantity": ln.quantity,
                "unit": ln.unit,
            }
        )

    write_audit(
        db,
        action="CANTEEN_OCR",
        entity_type="canteen_purchase",
        entity_id=purchase.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"lines={len(line_dicts)} failed={ocr.failed}",
    )
    db.commit()
    db.refresh(purchase)
    return CanteenDetectOut(
        purchase_id=purchase.id,
        transaction_id=txn.transaction_id,
        transaction_pk=txn.id,
        photo_id=photo.id,
        invoice_number=purchase.invoice_number,
        supplier_name=purchase.supplier_name,
        invoice_total=purchase.invoice_total,
        lines=line_dicts,
        confidence=ocr.confidence,
        provider=ocr.provider,
        failed=ocr.failed,
        message=ocr.message,
        ocr_raw_preview=(ocr.raw_ocr_text or "")[:500],
    )


@router.post("/purchase/confirm", response_model=CanteenPurchaseOut)
def confirm_purchase(
    body: CanteenConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("canteen.purchase", "canteen.stock")),
) -> CanteenPurchaseOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = db.get(Transaction, body.transaction_pk)
    purchase = db.get(CanteenPurchase, body.purchase_id)
    if txn is None or purchase is None or purchase.transaction_pk != txn.id:
        raise HTTPException(status_code=404, detail="Purchase not found.")
    if purchase.status == "CONFIRMED":
        raise HTTPException(status_code=400, detail="Purchase already confirmed.")
    if not body.lines:
        raise HTTPException(status_code=400, detail="At least one confirmed line is required.")

    purchase.invoice_number = body.invoice_number or purchase.invoice_number
    purchase.supplier_name = body.supplier_name or purchase.supplier_name
    purchase.invoice_total = body.invoice_total or purchase.invoice_total
    purchase.status = "CONFIRMED"
    purchase.confirmed_by = user.id

    # Replace lines with confirmed set
    old = db.execute(select(CanteenPurchaseLine).where(CanteenPurchaseLine.purchase_id == purchase.id)).scalars().all()
    for o in old:
        db.delete(o)
    db.flush()

    for ln in body.lines:
        item = None
        if ln.item_id:
            item = db.get(CanteenItem, ln.item_id)
        elif ln.item_code:
            item = _item_by_code(db, ln.item_code)
        if item is None:
            raise HTTPException(status_code=400, detail=f"Unknown canteen item for line {ln.item_name}.")
        row = CanteenPurchaseLine(
            purchase_id=purchase.id,
            item_id=item.id,
            item_code=item.code,
            item_name=ln.item_name or item.name,
            quantity=float(ln.quantity),
            unit=(ln.unit or item.unit).upper(),
            ocr_matched=True,
        )
        db.add(row)
        db.add(
            CanteenStockMovement(
                item_id=item.id,
                transaction_pk=txn.id,
                transaction_id=txn.transaction_id,
                purchase_id=purchase.id,
                direction="IN",
                quantity=float(ln.quantity),
                unit=(ln.unit or item.unit).upper(),
                note=f"Purchase {purchase.invoice_number or purchase.id}",
                created_by=user.id,
            )
        )

    # Complete canteen txn (ENTRY_STARTED → COMPLETED allowed for equipment; same for canteen)
    try:
        if txn.status == TransactionStatus.ENTRY_STARTED.value:
            transition(
                db,
                txn,
                to_status=TransactionStatus.COMPLETED.value,
                actor_user_id=user.id,
                device_id=body.device_id,
                reason="Canteen purchase confirmed; stock posted",
                lat=body.gps.lat,
                lon=body.gps.lon,
                gps_accuracy_m=body.gps.accuracy_m,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    write_audit(
        db,
        action="CANTEEN_PURCHASE_CONFIRMED",
        entity_type="canteen_purchase",
        entity_id=purchase.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        details=f"lines={len(body.lines)} inv={purchase.invoice_number}",
    )
    db.commit()
    db.refresh(purchase)
    db.refresh(txn)
    return _purchase_out(db, purchase, txn)


@router.get("/purchase/{purchase_id}", response_model=CanteenPurchaseOut)
def get_purchase(
    purchase_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("canteen.purchase", "canteen.stock")),
) -> CanteenPurchaseOut:
    purchase = db.get(CanteenPurchase, purchase_id)
    if purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found.")
    txn = db.get(Transaction, purchase.transaction_pk)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return _purchase_out(db, purchase, txn)
