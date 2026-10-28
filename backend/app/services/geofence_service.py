"""GPS / geofence verification abstraction."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.services.geofence_config import GeofenceConfig, load_geofence_config


@dataclass(frozen=True)
class GpsSample:
    latitude: float
    longitude: float
    accuracy_m: float


@dataclass(frozen=True)
class GeofenceResult:
    authorized: bool
    message: str
    distance_m: float
    accuracy_m: float


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class GeofenceService:
    def __init__(
        self,
        settings: Settings | None = None,
        config: GeofenceConfig | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.config = config

    def _cfg(self) -> GeofenceConfig:
        if self.config is not None:
            return self.config
        try:
            return load_geofence_config()
        except Exception:  # noqa: BLE001 — fall back to env if DB unavailable
            return GeofenceConfig(
                lat=self.settings.gps_geofence_lat,
                lon=self.settings.gps_geofence_lon,
                radius_m=self.settings.gps_geofence_radius_m,
                max_accuracy_m=self.settings.gps_max_accuracy_m,
                source="env",
            )

    def verify(self, sample: GpsSample) -> GeofenceResult:
        cfg = self._cfg()
        distance = haversine_m(sample.latitude, sample.longitude, cfg.lat, cfg.lon)

        # Local / off-site testing — still return distance & accuracy for the banner.
        if not self.settings.gps_enforce:
            return GeofenceResult(
                authorized=True,
                message=(
                    "GPS soft-check (enforcement off). "
                    f"±{sample.accuracy_m:.0f} m · {distance:.0f} m from fence centre."
                ),
                distance_m=distance,
                accuracy_m=sample.accuracy_m,
            )

        if distance > cfg.radius_m:
            return GeofenceResult(
                authorized=False,
                message="OPERATION NOT AUTHORIZED. Please move inside JV Industries premises.",
                distance_m=distance,
                accuracy_m=sample.accuracy_m,
            )

        # Inside the fence: do not hard-block on moderate browser/Wi-Fi accuracy noise.
        # Only reject when the fix is so coarse that the operator might not actually be on site.
        soft_ceiling = max(cfg.max_accuracy_m, cfg.radius_m)
        if sample.accuracy_m > soft_ceiling:
            return GeofenceResult(
                authorized=False,
                message=(
                    "OPERATION NOT AUTHORIZED. GPS accuracy is too low. "
                    "Please wait for a better signal inside JV Industries premises."
                ),
                distance_m=distance,
                accuracy_m=sample.accuracy_m,
            )

        return GeofenceResult(
            authorized=True,
            message="GPS verified inside authorized premises.",
            distance_m=distance,
            accuracy_m=sample.accuracy_m,
        )
