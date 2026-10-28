import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Tests run against MySQL (same engine family as production).
os.environ.setdefault(
    "DATABASE_URL",
    "mysql+pymysql://jvoms:JvOms%402026@127.0.0.1:3306/jvoms_test?charset=utf8mb4",
)
os.environ["JWT_SECRET"] = "test-secret-key-not-for-production"
os.environ["GPS_GEOFENCE_LAT"] = "13.0827"
os.environ["GPS_GEOFENCE_LON"] = "80.2707"
os.environ["GPS_GEOFENCE_RADIUS_M"] = "300"
os.environ["GPS_MAX_ACCURACY_M"] = "50"
os.environ["GPS_ENFORCE"] = "true"

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.db.seed import seed_reference_data
import app.models  # noqa: F401 — register ORM tables
from app.main import create_app

get_settings.cache_clear()


def _ensure_test_database(admin_url: str, db_name: str) -> None:
    """Create jvoms_test if missing (connect without schema)."""
    root = admin_url.rsplit("/", 1)[0]
    engine = create_engine(root + "/", isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    engine.dispose()


@pytest.fixture()
def client():
    settings = get_settings()
    url = settings.database_url
    db_name = url.rsplit("/", 1)[-1].split("?")[0]
    try:
        _ensure_test_database(url, db_name)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"MySQL not available for tests: {exc}")

    engine = create_engine(url, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_reference_data(db)
    db.close()

    app = create_app()

    def _override_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
