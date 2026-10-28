from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "JV-OMS"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    jwt_secret: str = "change-me-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    database_url: str = "mysql+pymysql://jvoms:JvOms%402026@127.0.0.1:3306/jvoms?charset=utf8mb4"

    # Aiven / cloud MySQL SSL
    mysql_ssl_required: bool = True
    mysql_ssl_ca: str = ""  # optional path to aiven-ca.pem

    storage_endpoint: str = ""
    storage_bucket: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_region: str = "ap-south-1"

    whatsapp_api_url: str = ""
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    # When true (default for staging), mock WhatsApp OTP/alerts are an accepted success path
    whatsapp_allow_mock: bool = True
    # Comma-separated mobiles for management alerts (WhatsApp)
    management_alert_mobiles: str = ""

    ai_provider: str = "on_device_mlkit"
    ai_api_key: str = ""
    # Groq vision (gsk_…) — preferred for ANPR when set
    groq_api_key: str = ""
    groq_vision_model: str = "qwen/qwen3.8-27b"

    evidence_root: str = "./evidence_store"

    # JV Industries — Chittoor yard (approx; override in Settings / DB)
    gps_geofence_lat: float = 13.2172
    gps_geofence_lon: float = 79.1004
    gps_geofence_radius_m: float = 500.0
    # Browser / Wi-Fi GPS is often 50–500 m; 50 m was rejecting almost all desktop/PWA fixes.
    gps_max_accuracy_m: float = 250.0
    # When false (typical for local APP_ENV=development), geofence soft-passes so yard can be tested off-site.
    gps_enforce: bool = True

    # Confidence thresholds (operator confirmation still required)
    anpr_min_confidence: float = 0.55
    weighbridge_min_confidence: float = 0.55
    density_min_confidence: float = 0.55

    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
