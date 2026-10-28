"""Stock engine — balances from movements only; assign + post from verified txns."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.enums import TransactionStatus, TransactionType
from app.models.stock import Product, StockAdjustment, StockMovement, StorageUnit
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.stock import (
    AdjustmentApproveRequest,
    AdjustmentOut,
    AdjustmentRequest,
    AssignStorageRequest,
    BalanceOut,
    MovementOut,
    PostMovementRequest,
    TransferRequest,
    TxnStockOut,
)
from app.services.audit_service import write_audit
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.stock_engine import balance_for, compute_balance

router = APIRouter()

_ASSIGN_OK = {
    TransactionStatus.VEHICLE_VERIFIED.value,
    TransactionStatus.AWAITING_TARE.value,
    TransactionStatus.TARE_COMPLETED.value,
    TransactionStatus.LOADING.value,
    TransactionStatus.UNLOADING.value,
    TransactionStatus.GROSS_COMPLETED.value,
    TransactionStatus.DENSITY_PENDING.value,
    TransactionStatus.DOCUMENTS_PENDING.value,
    TransactionStatus.DOCUMENTS_VERIFIED.value,
    TransactionStatus.APPROVED.value,
    TransactionStatus.EXIT_PENDING.value,
}

_POST_OK = {
    TransactionStatus.DOCUMENTS_VERIFIED.value,
    TransactionStatus.APPROVED.value,
    TransactionStatus.EXIT_PENDING.value,
    TransactionStatus.CUSTOMER_CONFIRMED.value,
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


def _movement_out(m: StockMovement) -> MovementOut:
    return MovementOut.model_validate(m)


def _txn_stock(db: Session, txn: Transaction) -> TxnStockOut:
    product = db.get(Product, txn.product_id) if txn.product_id else None
    unit = db.get(StorageUnit, txn.storage_unit_id) if txn.storage_unit_id else None
    moves = list(
        db.execute(
            select(StockMovement)
            .where(StockMovement.transaction_pk == txn.id)
            .order_by(StockMovement.created_at)
        )
        .scalars()
        .all()
    )
    return TxnStockOut(
        transaction_id=txn.transaction_id,
        status=txn.status,
        product_id=txn.product_id,
        product_code=product.code if product else None,
        storage_unit_id=txn.storage_unit_id,
        storage_code=unit.code if unit else None,
        net_kg=txn.net_kg,
        calculated_litres=txn.calculated_litres,
        stock_posted=bool(txn.stock_posted) or len(moves) > 0,
        movements=[_movement_out(m) for m in moves],
    )


@router.get("/balances", response_model=list[BalanceOut])
def get_balances(
    product_id: str | None = None,
    storage_unit_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("stock.view", "storage.select")),
) -> list[BalanceOut]:
    rows = compute_balance(db, product_id=product_id, storage_unit_id=storage_unit_id)
    return [BalanceOut(**r.__dict__) for r in rows]


@router.get("/movements", response_model=list[MovementOut])
def list_movements(
    product_id: str | None = None,
    storage_unit_id: str | None = None,
    transaction_pk: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("stock.view", "storage.select")),
) -> list[MovementOut]:
    q = select(StockMovement).order_by(StockMovement.created_at.desc()).limit(limit)
    if product_id:
        q = q.where(StockMovement.product_id == product_id)
    if storage_unit_id:
        q = q.where(StockMovement.storage_unit_id == storage_unit_id)
    if transaction_pk:
        q = q.where(StockMovement.transaction_pk == transaction_pk)
    return [_movement_out(m) for m in db.execute(q).scalars().all()]


@router.get("/txn/{transaction_pk}", response_model=TxnStockOut)
def txn_stock_status(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("stock.view", "storage.select", "transaction.view")),
) -> TxnStockOut:
    return _txn_stock(db, _txn(db, transaction_pk))


@router.post("/assign", response_model=TxnStockOut)
def assign_storage(
    body: AssignStorageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("storage.select", "stock.view")),
) -> TxnStockOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = _txn(db, body.transaction_pk)
    if txn.status not in _ASSIGN_OK:
        raise HTTPException(status_code=400, detail=f"Cannot assign storage in status {txn.status}.")
    product = db.get(Product, body.product_id)
    unit = db.get(StorageUnit, body.storage_unit_id)
    if product is None or not product.active:
        raise HTTPException(status_code=400, detail="Product not found or inactive.")
    if unit is None or not unit.active:
        raise HTTPException(status_code=400, detail="Storage unit not found or inactive.")
    if unit.product_id and unit.product_id != product.id:
        raise HTTPException(
            status_code=400,
            detail=f"Storage {unit.code} is reserved for a different product.",
        )

    txn.product_id = product.id
    txn.storage_unit_id = unit.id
    txn.last_lat = body.gps.lat
    txn.last_lon = body.gps.lon
    txn.last_gps_accuracy_m = body.gps.accuracy_m
    txn.geofence_ok = True

    write_audit(
        db,
        action="STORAGE_ASSIGNED",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=body.device_id,
        details=f"{product.code} → {unit.kind} {unit.code}",
    )
    db.commit()
    db.refresh(txn)
    return _txn_stock(db, txn)


@router.post("/post", response_model=TxnStockOut)
def post_stock(
    body: PostMovementRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("storage.select", "stock.view")),
) -> TxnStockOut:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    txn = _txn(db, body.transaction_pk)
    if txn.status not in _POST_OK:
        raise HTTPException(
            status_code=400,
            detail=f"Stock post requires documents verified (status={txn.status}).",
        )
    if txn.stock_posted:
        raise HTTPException(status_code=400, detail="Stock already posted for this transaction.")

    product_id = body.product_id or txn.product_id
    storage_unit_id = body.storage_unit_id or txn.storage_unit_id
    if not product_id or not storage_unit_id:
        raise HTTPException(status_code=400, detail="Assign product and storage before posting stock.")

    product = db.get(Product, product_id)
    unit = db.get(StorageUnit, storage_unit_id)
    if product is None or unit is None:
        raise HTTPException(status_code=400, detail="Product or storage unit not found.")

    # Direction from txn type if client sent generic IN/OUT
    direction = body.direction.upper()
    if txn.type == TransactionType.MATERIAL_RECEIVING_INWARD.value:
        direction = "IN"
    elif txn.type == TransactionType.MATERIAL_LOADING_OUTWARD.value:
        direction = "OUT"

    qty = body.quantity
    unit_code = (body.unit or product.unit).upper()
    qty_kg = None
    qty_l = None

    if body.use_transaction_qty or qty is None:
        if product.unit == "L" or unit_code == "L":
            if txn.calculated_litres is None:
                raise HTTPException(
                    status_code=400,
                    detail="Server calculated litres required to post liquid stock.",
                )
            qty = float(txn.calculated_litres)
            unit_code = "L"
            qty_l = qty
            qty_kg = float(txn.net_kg) if txn.net_kg is not None else None
        else:
            if txn.net_kg is None:
                raise HTTPException(status_code=400, detail="Server net_kg required to post stock.")
            qty = float(txn.net_kg)
            unit_code = "KG"
            qty_kg = qty
            qty_l = float(txn.calculated_litres) if txn.calculated_litres is not None else None

    assert qty is not None and qty > 0

    if direction == "OUT" and not body.allow_negative:
        bal = balance_for(db, product_id=product.id, storage_unit_id=unit.id)
        if bal < qty:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock in {unit.code}: balance {bal} {unit_code}, need {qty}.",
            )

    move = StockMovement(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        product_id=product.id,
        storage_unit_id=unit.id,
        direction=direction,
        quantity=float(qty),
        unit=unit_code,
        quantity_kg=qty_kg,
        quantity_litres=qty_l,
        note=body.note,
        created_by=user.id,
        device_id=body.device_id,
        lat=body.gps.lat,
        lon=body.gps.lon,
        gps_accuracy_m=body.gps.accuracy_m,
    )
    db.add(move)
    txn.product_id = product.id
    txn.storage_unit_id = unit.id
    txn.stock_posted = True

    write_audit(
        db,
        action="STOCK_POSTED",
        entity_type="stock_movement",
        entity_id=move.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=body.device_id,
        details=f"{direction} {qty} {unit_code} {product.code}@{unit.code}",
    )
    db.commit()
    db.refresh(txn)
    return _txn_stock(db, txn)


@router.post("/transfer", response_model=list[MovementOut])
def transfer_stock(
    body: TransferRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("storage.select", "stock.view")),
) -> list[MovementOut]:
    _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    if body.from_storage_unit_id == body.to_storage_unit_id:
        raise HTTPException(status_code=400, detail="From and to storage must differ.")
    product = db.get(Product, body.product_id)
    src = db.get(StorageUnit, body.from_storage_unit_id)
    dst = db.get(StorageUnit, body.to_storage_unit_id)
    if product is None or src is None or dst is None:
        raise HTTPException(status_code=400, detail="Product or storage unit not found.")

    bal = balance_for(db, product_id=product.id, storage_unit_id=src.id)
    if bal < body.quantity:
        raise HTTPException(status_code=400, detail=f"Insufficient stock in {src.code}: {bal}.")

    txn = db.get(Transaction, body.transaction_pk) if body.transaction_pk else None
    common = dict(
        transaction_pk=txn.id if txn else None,
        transaction_id=txn.transaction_id if txn else None,
        product_id=product.id,
        quantity=float(body.quantity),
        unit=body.unit.upper(),
        note=body.note,
        created_by=user.id,
        device_id=body.device_id,
        lat=body.gps.lat,
        lon=body.gps.lon,
        gps_accuracy_m=body.gps.accuracy_m,
    )
    out_m = StockMovement(storage_unit_id=src.id, direction="TRANSFER_OUT", **common)
    in_m = StockMovement(storage_unit_id=dst.id, direction="TRANSFER_IN", **common)
    db.add(out_m)
    db.add(in_m)
    write_audit(
        db,
        action="STOCK_TRANSFER",
        entity_type="stock_movement",
        entity_id=out_m.id,
        transaction_id=txn.transaction_id if txn else None,
        actor_user_id=user.id,
        details=f"{body.quantity} {body.unit} {product.code} {src.code}→{dst.code}",
    )
    db.commit()
    db.refresh(out_m)
    db.refresh(in_m)
    return [_movement_out(out_m), _movement_out(in_m)]


@router.post("/adjustments", response_model=AdjustmentOut, status_code=status.HTTP_201_CREATED)
def request_adjustment(
    body: AdjustmentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("stock.adjust")),
) -> StockAdjustment:
    if body.gps:
        _gps_ok(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
    if db.get(Product, body.product_id) is None or db.get(StorageUnit, body.storage_unit_id) is None:
        raise HTTPException(status_code=400, detail="Product or storage unit not found.")
    row = StockAdjustment(
        product_id=body.product_id,
        storage_unit_id=body.storage_unit_id,
        requested_quantity=float(body.delta_quantity),
        unit=body.unit.upper(),
        reason=body.reason,
        status="PENDING",
        requested_by=user.id,
    )
    db.add(row)
    write_audit(
        db,
        action="STOCK_ADJUST_REQUESTED",
        entity_type="stock_adjustment",
        entity_id=row.id,
        actor_user_id=user.id,
        details=f"delta={body.delta_quantity} {body.unit}",
    )
    db.commit()
    db.refresh(row)
    return row


@router.post("/adjustments/{adjustment_id}/decide", response_model=AdjustmentOut)
def decide_adjustment(
    adjustment_id: str,
    body: AdjustmentApproveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("approval.act")),
) -> StockAdjustment:
    row = db.get(StockAdjustment, adjustment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Adjustment not found.")
    if row.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Adjustment already {row.status}.")

    if not body.approve:
        row.status = "REJECTED"
        row.approved_by = user.id
        row.approval_note = body.approval_note
        write_audit(
            db,
            action="STOCK_ADJUST_REJECTED",
            entity_type="stock_adjustment",
            entity_id=row.id,
            actor_user_id=user.id,
            details=body.approval_note,
        )
        db.commit()
        db.refresh(row)
        return row

    move = StockMovement(
        product_id=row.product_id,
        storage_unit_id=row.storage_unit_id,
        direction="ADJUST",
        quantity=float(row.requested_quantity),  # signed
        unit=row.unit,
        note=f"Approved adjust: {row.reason}",
        created_by=user.id,
    )
    db.add(move)
    db.flush()
    row.status = "APPROVED"
    row.approved_by = user.id
    row.approval_note = body.approval_note
    row.movement_id = move.id
    write_audit(
        db,
        action="STOCK_ADJUST_APPROVED",
        entity_type="stock_adjustment",
        entity_id=row.id,
        actor_user_id=user.id,
        details=body.approval_note,
    )
    db.commit()
    db.refresh(row)
    return row
