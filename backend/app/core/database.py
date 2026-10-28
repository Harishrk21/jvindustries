from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _mysql_connect_args(settings) -> dict:
    """Aiven and other cloud MySQL require SSL (ssl-mode=REQUIRED)."""
    args: dict = {}
    if not settings.mysql_ssl_required:
        return args

    ssl: dict = {}
    ca = (settings.mysql_ssl_ca or "").strip()
    if ca:
        ca_path = Path(ca)
        if not ca_path.is_absolute():
            ca_path = Path(__file__).resolve().parents[2] / ca
        if ca_path.exists():
            ssl["ca"] = str(ca_path)
    # Empty ssl dict still enables TLS for PyMySQL (required by Aiven)
    args["ssl"] = ssl
    return args


def _engine():
    settings = get_settings()
    url = settings.database_url
    if not url.startswith("mysql"):
        raise RuntimeError(
            "JV-OMS supports MySQL only. Set DATABASE_URL=mysql+pymysql://user:pass@host:port/db?charset=utf8mb4"
        )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=28000,
        pool_size=5,
        max_overflow=10,
        connect_args=_mysql_connect_args(settings),
    )


engine = _engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
