from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import Device, User
from app.schemas.auth import DeviceOut, DeviceRegisterRequest
from app.services.audit_service import write_audit

router = APIRouter()


@router.post("/register", response_model=DeviceOut)
def register_device(
    body: DeviceRegisterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeviceOut:
    device = db.execute(select(Device).where(Device.device_uid == body.device_uid)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if device is None:
        device = Device(
            user_id=user.id,
            device_uid=body.device_uid,
            device_name=body.device_name,
            platform=body.platform,
            app_version=body.app_version,
            last_seen_at=now,
        )
        db.add(device)
        action = "DEVICE_REGISTERED"
    else:
        device.user_id = user.id
        device.device_name = body.device_name or device.device_name
        device.platform = body.platform
        device.app_version = body.app_version
        device.is_active = True
        device.last_seen_at = now
        action = "DEVICE_REBOUND"

    write_audit(
        db,
        action=action,
        entity_type="device",
        entity_id=device.device_uid,
        actor_user_id=user.id,
        device_id=device.id if device.id else None,
        details=f"Device {body.device_uid} for user {user.user_code}",
    )
    db.commit()
    db.refresh(device)
    return DeviceOut.model_validate(device)
