from app.core.config import Settings
from app.services.geofence_service import GeofenceService, GpsSample


def test_inside_geofence():
    settings = Settings(
        gps_geofence_lat=13.0827,
        gps_geofence_lon=80.2707,
        gps_geofence_radius_m=300,
        gps_max_accuracy_m=50,
        gps_enforce=True,
    )
    svc = GeofenceService(settings)
    result = svc.verify(GpsSample(13.0827, 80.2707, 10))
    assert result.authorized is True


def test_outside_geofence():
    settings = Settings(
        gps_geofence_lat=13.0827,
        gps_geofence_lon=80.2707,
        gps_geofence_radius_m=300,
        gps_max_accuracy_m=50,
        gps_enforce=True,
    )
    svc = GeofenceService(settings)
    result = svc.verify(GpsSample(12.0, 80.0, 10))
    assert result.authorized is False
    assert "NOT AUTHORIZED" in result.message


def test_moderate_accuracy_inside_allowed():
    """Browser GPS often reports 60–200 m; still allow when clearly inside the fence."""
    settings = Settings(
        gps_geofence_lat=13.0827,
        gps_geofence_lon=80.2707,
        gps_geofence_radius_m=300,
        gps_max_accuracy_m=50,
        gps_enforce=True,
    )
    svc = GeofenceService(settings)
    result = svc.verify(GpsSample(13.0827, 80.2707, 120))
    assert result.authorized is True


def test_extreme_accuracy_inside_rejected():
    settings = Settings(
        gps_geofence_lat=13.0827,
        gps_geofence_lon=80.2707,
        gps_geofence_radius_m=300,
        gps_max_accuracy_m=50,
        gps_enforce=True,
    )
    svc = GeofenceService(settings)
    result = svc.verify(GpsSample(13.0827, 80.2707, 5000))
    assert result.authorized is False
    assert "accuracy" in result.message.lower()


def test_enforce_off_allows_offsite():
    settings = Settings(
        gps_geofence_lat=13.0827,
        gps_geofence_lon=80.2707,
        gps_geofence_radius_m=300,
        gps_max_accuracy_m=50,
        gps_enforce=False,
    )
    svc = GeofenceService(settings)
    result = svc.verify(GpsSample(12.0, 80.0, 500))
    assert result.authorized is True
    assert "soft-check" in result.message.lower() or "enforcement off" in result.message.lower()
