from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_permissions
from app.models.user import User
from app.schemas.transaction import GeofenceCheckRequest, GeofenceCheckResponse
from app.services.audit_service import write_audit
from app.services.geofence_config import env_geofence_config, load_geofence_config, save_geofence_config
from app.services.geofence_service import GeofenceService, GpsSample

router = APIRouter()


class GeofenceConfigOut(BaseModel):
    lat: float
    lon: float
    radius_m: float
    max_accuracy_m: float
    source: str


class GeofenceConfigUpdate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: float = Field(..., gt=10, le=50000)
    max_accuracy_m: float = Field(..., gt=1, le=5000)


@router.post("/check", response_model=GeofenceCheckResponse)
def check_geofence(
    body: GeofenceCheckRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GeofenceCheckResponse:
    try:
        cfg = load_geofence_config(db)
    except Exception:  # noqa: BLE001 — Aiven blips must not block yard UI
        cfg = env_geofence_config()
    result = GeofenceService(config=cfg).verify(GpsSample(body.lat, body.lon, body.accuracy_m))
    return GeofenceCheckResponse(
        authorized=result.authorized,
        message=result.message,
        distance_m=result.distance_m,
        accuracy_m=result.accuracy_m,
    )


@router.get("/config", response_model=GeofenceConfigOut)
def get_geofence_config(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> GeofenceConfigOut:
    try:
        cfg = load_geofence_config(db)
    except Exception:  # noqa: BLE001
        cfg = env_geofence_config()
    return GeofenceConfigOut(
        lat=cfg.lat,
        lon=cfg.lon,
        radius_m=cfg.radius_m,
        max_accuracy_m=cfg.max_accuracy_m,
        source=cfg.source,
    )


@router.put("/config", response_model=GeofenceConfigOut)
def put_geofence_config(
    body: GeofenceConfigUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions("config.geofence")),
) -> GeofenceConfigOut:
    cfg = save_geofence_config(
        db,
        lat=body.lat,
        lon=body.lon,
        radius_m=body.radius_m,
        max_accuracy_m=body.max_accuracy_m,
        actor_user_id=user.id,
    )
    write_audit(
        db,
        action="GEOFENCE_CONFIG_UPDATED",
        entity_type="system_setting",
        entity_id="geofence",
        actor_user_id=user.id,
        details=f"lat={cfg.lat} lon={cfg.lon} r={cfg.radius_m}m acc={cfg.max_accuracy_m}m",
    )
    db.commit()
    return GeofenceConfigOut(
        lat=cfg.lat,
        lon=cfg.lon,
        radius_m=cfg.radius_m,
        max_accuracy_m=cfg.max_accuracy_m,
        source=cfg.source,
    )
