"""Production configuration guards — fail closed on unsafe defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class ReadinessIssue:
    code: str
    severity: str  # ERROR | WARN
    message: str


WEAK_JWT_MARKERS = (
    "change-me",
    "test-secret",
    "secret",
    "password",
    "jwt_secret",
)


def check_production_settings(settings: Settings) -> list[ReadinessIssue]:
    issues: list[ReadinessIssue] = []
    is_prod = settings.app_env.lower() in {"production", "prod"}

    secret = (settings.jwt_secret or "").strip().lower()
    weak = len(settings.jwt_secret or "") < 32 or any(m in secret for m in WEAK_JWT_MARKERS)
    if weak:
        issues.append(
            ReadinessIssue(
                code="WEAK_JWT_SECRET",
                severity="ERROR" if is_prod else "WARN",
                message="JWT_SECRET must be a long random value (≥32 chars), not a default/test secret.",
            )
        )

    if settings.debug and is_prod:
        issues.append(
            ReadinessIssue(
                code="DEBUG_IN_PRODUCTION",
                severity="ERROR",
                message="DEBUG must be false when APP_ENV is production.",
            )
        )

    if settings.cors_origins.strip() == "*" and is_prod:
        issues.append(
            ReadinessIssue(
                code="OPEN_CORS",
                severity="ERROR",
                message="CORS_ORIGINS must list explicit origins in production (not *).",
            )
        )

    if not settings.mysql_ssl_required and is_prod:
        issues.append(
            ReadinessIssue(
                code="MYSQL_SSL_OFF",
                severity="WARN",
                message="MYSQL_SSL_REQUIRED is false — enable SSL for Aiven/cloud MySQL.",
            )
        )

    if "127.0.0.1" in settings.database_url and is_prod:
        issues.append(
            ReadinessIssue(
                code="LOCAL_DATABASE_URL",
                severity="WARN",
                message="DATABASE_URL points at localhost in a production env.",
            )
        )

    return issues


def assert_production_ready(settings: Settings) -> None:
    """Raise RuntimeError if production has blocking ERROR issues."""
    if settings.app_env.lower() not in {"production", "prod"}:
        return
    errors = [i for i in check_production_settings(settings) if i.severity == "ERROR"]
    if errors:
        joined = "; ".join(f"{e.code}: {e.message}" for e in errors)
        raise RuntimeError(f"Production readiness failed: {joined}")
