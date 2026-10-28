import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.production_readiness import (
    ReadinessIssue,
    assert_production_ready,
    check_production_settings,
)
from app.db.schema_patch import ensure_phase5_columns
from app.db.seed import seed_reference_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("jvoms")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    assert_production_ready(settings)
    for issue in check_production_settings(settings):
        log = logger.error if issue.severity == "ERROR" else logger.warning
        log("readiness %s: %s", issue.code, issue.message)

    import app.models  # noqa: F401 — register ORM tables for create_all

    # Create/upgrade schema on MySQL (Alembic preferred in production deployments).
    Base.metadata.create_all(bind=engine)
    ensure_phase5_columns(engine)
    db = SessionLocal()
    try:
        seed_reference_data(db)
        logger.info("Reference data seeded (%s)", settings.app_env)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health")
    def health():
        from pathlib import Path

        from app.services.whatsapp_client import get_whatsapp_client

        issues = list(check_production_settings(settings))
        evidence_root = Path(settings.evidence_root)
        evidence_ok = False
        evidence_detail = ""
        try:
            evidence_root.mkdir(parents=True, exist_ok=True)
            probe = evidence_root / ".health_write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            evidence_ok = True
            evidence_detail = str(evidence_root.resolve())
        except Exception as exc:  # noqa: BLE001
            evidence_detail = str(exc)[:200]
            issues.append(
                ReadinessIssue(
                    code="EVIDENCE_NOT_WRITABLE",
                    severity="ERROR",
                    message=evidence_detail,
                )
            )

        wa = get_whatsapp_client()
        wa_mode = getattr(wa, "provider_name", wa.__class__.__name__)
        is_prod = settings.app_env.lower() in {"production", "prod"}
        if wa_mode == "mock_whatsapp":
            if settings.whatsapp_allow_mock:
                # Accepted staging path — OTP returns otp_preview; no Meta credentials required
                issues.append(
                    ReadinessIssue(
                        code="WHATSAPP_MOCK_OK",
                        severity="WARN" if is_prod else "WARN",
                        message=(
                            "WhatsApp mock active (accepted). OTP/alerts succeed with on-screen code. "
                            "Set WHATSAPP_TOKEN + WHATSAPP_PHONE_NUMBER_ID later for Meta live."
                        ),
                    )
                )
            elif is_prod:
                issues.append(
                    ReadinessIssue(
                        code="WHATSAPP_MOCK_IN_PRODUCTION",
                        severity="ERROR",
                        message=(
                            "WhatsApp mock blocked in production. Set Meta credentials or "
                            "WHATSAPP_ALLOW_MOCK=true for staging."
                        ),
                    )
                )

        # Flag published seed passwords still in use
        try:
            from sqlalchemy import select

            from app.core.security import verify_password
            from app.models.user import User

            seed_defaults = {
                "owner": "Owner@123",
                "supervisor": "Super@123",
                "security": "Security@123",
                "weighbridge": "Weigh@123",
                "store": "Store@123",
                "production": "Prod@123",
                "canteen": "Canteen@123",
            }
            db = SessionLocal()
            try:
                still = []
                for code, pw in seed_defaults.items():
                    u = db.execute(select(User).where(User.user_code == code)).scalar_one_or_none()
                    if u and verify_password(pw, u.password_hash):
                        still.append(code)
                if still:
                    issues.append(
                        ReadinessIssue(
                            code="DEFAULT_SEED_PASSWORDS",
                            severity="ERROR" if is_prod else "WARN",
                            message=(
                                "Change seed passwords before go-live: "
                                + ", ".join(still)
                                + " (Settings → Change password, or POST /auth/change-password)."
                            ),
                        )
                    )
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed password probe skipped: %s", exc)

        return {
            "status": "ok" if evidence_ok else "degraded",
            "app": settings.app_name,
            "env": settings.app_env,
            "whatsapp": {
                "provider": wa_mode,
                "live": wa_mode == "meta_cloud",
                "allow_mock": settings.whatsapp_allow_mock,
                "otp_path": "mock_preview" if wa_mode == "mock_whatsapp" else "meta_cloud",
            },
            "evidence": {"writable": evidence_ok, "root": evidence_detail},
            "geofence": {
                "lat": settings.gps_geofence_lat,
                "lon": settings.gps_geofence_lon,
                "radius_m": settings.gps_geofence_radius_m,
                "enforce": settings.gps_enforce,
            },
            "readiness": [
                {"code": i.code, "severity": i.severity, "message": i.message} for i in issues
            ],
        }

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s: %s", request.url.path, exc)
        msg = "Unable to complete the request. Please try again."
        code = "INTERNAL_ERROR"
        # Surface DB outages clearly (Aiven DNS / local MySQL down) instead of a blank retry.
        exc_name = type(exc).__name__
        exc_text = str(exc).lower()
        if exc_name in {"OperationalError", "InterfaceError"} or "getaddrinfo" in exc_text:
            code = "DATABASE_UNAVAILABLE"
            msg = (
                "Database unreachable. Check DATABASE_URL / MySQL is running, then retry."
                if settings.app_env != "production"
                else msg
            )
        return JSONResponse(
            status_code=500,
            content={"code": code, "message": msg},
        )

    return app


app = create_app()
