"""Runtime geofence config — DB overrides env defaults."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.system_setting import SystemSetting

KEY_LAT = "geofence.lat"
KEY_LON = "geofence.lon"
KEY_RADIUS = "geofence.radius_m"
KEY_MAX_ACC = "geofence.max_accuracy_m"


@dataclass(frozen=True)
class GeofenceConfig:
    lat: float
    lon: float
    radius_m: float
    max_accuracy_m: float
    source: str  # env | database


def _get(db: Session, key: str) -> str | None:
    row = db.get(SystemSetting, key)
    return row.value if row else None


def env_geofence_config() -> GeofenceConfig:
    settings = get_settings()
    return GeofenceConfig(
        lat=settings.gps_geofence_lat,
        lon=settings.gps_geofence_lon,
        radius_m=settings.gps_geofence_radius_m,
        max_accuracy_m=settings.gps_max_accuracy_m,
        source="env",
    )


def load_geofence_config(db: Session | None = None) -> GeofenceConfig:
    defaults = env_geofence_config()
    own = False
    if db is None:
        from app.core.database import SessionLocal

        db = SessionLocal()
        own = True
    try:
        lat_s = _get(db, KEY_LAT)
        lon_s = _get(db, KEY_LON)
        rad_s = _get(db, KEY_RADIUS)
        acc_s = _get(db, KEY_MAX_ACC)
        if not any([lat_s, lon_s, rad_s, acc_s]):
            return defaults
        return GeofenceConfig(
            lat=float(lat_s) if lat_s is not None else defaults.lat,
            lon=float(lon_s) if lon_s is not None else defaults.lon,
            radius_m=float(rad_s) if rad_s is not None else defaults.radius_m,
            max_accuracy_m=float(acc_s) if acc_s is not None else defaults.max_accuracy_m,
            source="database",
        )
    except Exception:  # noqa: BLE001 — DB down → env defaults
        return defaults
    finally:
        if own:
            db.close()


def _upsert(db: Session, key: str, value: str, user_id: str | None) -> None:
    row = db.get(SystemSetting, key)
    if row is None:
        db.add(SystemSetting(key=key, value=value, updated_by=user_id))
    else:
        row.value = value
        row.updated_by = user_id


def save_geofence_config(
    db: Session,
    *,
    lat: float,
    lon: float,
    radius_m: float,
    max_accuracy_m: float,
    actor_user_id: str | None,
) -> GeofenceConfig:
    _upsert(db, KEY_LAT, str(lat), actor_user_id)
    _upsert(db, KEY_LON, str(lon), actor_user_id)
    _upsert(db, KEY_RADIUS, str(radius_m), actor_user_id)
    _upsert(db, KEY_MAX_ACC, str(max_accuracy_m), actor_user_id)
    db.flush()
    return GeofenceConfig(
        lat=lat,
        lon=lon,
        radius_m=radius_m,
        max_accuracy_m=max_accuracy_m,
        source="database",
    )
