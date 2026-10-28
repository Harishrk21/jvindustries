from app.core.config import Settings
from app.core.production_readiness import assert_production_ready, check_production_settings


def test_dev_weak_secret_is_warn_only():
    s = Settings(
        app_env="development",
        jwt_secret="change-me-to-a-long-random-secret",
        debug=True,
        cors_origins="*",
    )
    issues = check_production_settings(s)
    assert any(i.code == "WEAK_JWT_SECRET" and i.severity == "WARN" for i in issues)
    assert_production_ready(s)  # must not raise in development


def test_production_blocks_weak_secret_and_open_cors():
    s = Settings(
        app_env="production",
        jwt_secret="short",
        debug=True,
        cors_origins="*",
        mysql_ssl_required=True,
        database_url="mysql+pymysql://u:p@db.example:3306/jvoms",
    )
    issues = check_production_settings(s)
    codes = {i.code: i.severity for i in issues}
    assert codes.get("WEAK_JWT_SECRET") == "ERROR"
    assert codes.get("DEBUG_IN_PRODUCTION") == "ERROR"
    assert codes.get("OPEN_CORS") == "ERROR"
    try:
        assert_production_ready(s)
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_production_ok_with_strong_config():
    s = Settings(
        app_env="production",
        jwt_secret="a" * 40,
        debug=False,
        cors_origins="https://oms.jvindustries.example",
        mysql_ssl_required=True,
        database_url="mysql+pymysql://u:p@db.example:3306/jvoms",
    )
    errors = [i for i in check_production_settings(s) if i.severity == "ERROR"]
    assert errors == []
    assert_production_ready(s)
