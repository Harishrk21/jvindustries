from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_any_permission, require_permissions
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction, TransactionEvent
from app.models.user import User
from app.schemas.transaction import (
    TimelineResponse,
    TransactionCreateRequest,
    TransactionEventOut,
    TransactionListItem,
    TransactionOut,
    TransactionSearchResponse,
)
from app.services.audit_service import write_audit
from app.services.geofence_service import GeofenceService, GpsSample
from app.services.transaction_id import next_transaction_id

router = APIRouter()


@router.get("", response_model=TransactionSearchResponse)
def search_transactions(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("transaction.search", "transaction.view")),
    q: str | None = Query(None, description="Match transaction_id, vehicle, driver"),
    status_filter: str | None = Query(None, alias="status"),
    type_filter: str | None = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TransactionSearchResponse:
    stmt = select(Transaction)
    count_stmt = select(func.count()).select_from(Transaction)

    if q and q.strip():
        term = f"%{q.strip()}%"
        clause = or_(
            Transaction.transaction_id.ilike(term),
            Transaction.vehicle_number.ilike(term),
            Transaction.driver_name.ilike(term),
            Transaction.driver_mobile.ilike(term),
            Transaction.transporter_name.ilike(term),
            Transaction.notes.ilike(term),
        )
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if status_filter:
        stmt = stmt.where(Transaction.status == status_filter)
        count_stmt = count_stmt.where(Transaction.status == status_filter)

    if type_filter:
        stmt = stmt.where(Transaction.type == type_filter)
        count_stmt = count_stmt.where(Transaction.type == type_filter)

    total = int(db.execute(count_stmt).scalar_one())
    rows = (
        db.execute(
            stmt.order_by(Transaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return TransactionSearchResponse(
        items=[TransactionListItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("transaction.create")),
) -> TransactionOut:
    try:
        TransactionType(body.type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown transaction type.",
        ) from exc

    if body.client_transaction_id:
        existing = db.execute(
            select(Transaction).where(Transaction.client_transaction_id == body.client_transaction_id)
        ).scalar_one_or_none()
        if existing:
            return TransactionOut.model_validate(existing)

    geofence_ok = None
    lat = lon = acc = None
    if body.gps is not None:
        result = GeofenceService().verify(
            GpsSample(body.gps.lat, body.gps.lon, body.gps.accuracy_m)
        )
        geofence_ok = result.authorized
        lat, lon, acc = body.gps.lat, body.gps.lon, body.gps.accuracy_m
        if body.require_geofence and not result.authorized:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.message)

    txn_code = next_transaction_id(db)
    txn = Transaction(
        transaction_id=txn_code,
        client_transaction_id=body.client_transaction_id,
        type=body.type,
        status=TransactionStatus.DRAFT.value,
        created_by=user.id,
        device_id=body.device_id,
        geofence_ok=geofence_ok,
        last_lat=lat,
        last_lon=lon,
        last_gps_accuracy_m=acc,
        notes=body.notes,
    )
    db.add(txn)
    db.flush()

    event = TransactionEvent(
        transaction_pk=txn.id,
        from_status=None,
        to_status=TransactionStatus.DRAFT.value,
        actor_user_id=user.id,
        device_id=body.device_id,
        reason="Transaction created",
        lat=lat,
        lon=lon,
        gps_accuracy_m=acc,
    )
    db.add(event)

    write_audit(
        db,
        action="TRANSACTION_CREATED",
        entity_type="transaction",
        entity_id=txn.id,
        transaction_id=txn.transaction_id,
        actor_user_id=user.id,
        device_id=body.device_id,
        details=f"Created {txn.transaction_id} type={txn.type}",
    )
    db.commit()
    db.refresh(txn)
    return TransactionOut.model_validate(txn)


@router.get("/by-code/{transaction_id}", response_model=TransactionOut)
def get_by_code(
    transaction_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("transaction.view")),
) -> TransactionOut:
    txn = db.execute(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    ).scalar_one_or_none()
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    return TransactionOut.model_validate(txn)


@router.get("/{transaction_pk}/timeline", response_model=TimelineResponse)
def get_timeline(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("transaction.view", "transaction.search", "audit.view")),
) -> TimelineResponse:
    txn = db.get(Transaction, transaction_pk)
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    events = (
        db.execute(
            select(TransactionEvent)
            .where(TransactionEvent.transaction_pk == txn.id)
            .order_by(TransactionEvent.created_at.asc())
        )
        .scalars()
        .all()
    )
    return TimelineResponse(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        type=txn.type,
        status=txn.status,
        vehicle_number=txn.vehicle_number,
        events=[TransactionEventOut.model_validate(e) for e in events],
    )


@router.get("/{transaction_pk}", response_model=TransactionOut)
def get_transaction(
    transaction_pk: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("transaction.view")),
) -> TransactionOut:
    txn = db.get(Transaction, transaction_pk)
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    return TransactionOut.model_validate(txn)
