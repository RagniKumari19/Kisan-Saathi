"""Application settings. Fails fast on unsafe production configuration."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Farmer Assistance Platform"
    app_version: str = "1.0.0"
    app_env: str = "development"
    secret_key: str = "dev-insecure-secret-change-me"
    database_url: str = f"sqlite+aiosqlite:///{(BACKEND_DIR / 'farm.db').as_posix()}"
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    openweather_api_key: str = ""
    agmarknet_api_key: str = ""
    agmarknet_resource_id: str = "9ef84268-d588-465a-a308-a864a43d0070"

    # Phone verification. "dev" never sends an SMS; the code is returned only outside
    # production so the flow can be tested. Set a provider once DLT approval exists.
    sms_provider: str = "dev"  # dev | msg91 | fast2sms | twilio
    sms_api_key: str = ""
    sms_sender_id: str = ""
    sms_template_id: str = ""
    sms_account_sid: str = ""
    sms_auth_token: str = ""
    sms_from_number: str = ""
    otp_ttl_seconds: int = 300
    otp_resend_seconds: int = 60
    otp_max_attempts: int = 5
    otp_max_per_hour: int = 5
    otp_max_per_ip_hour: int = 20

    disease_confidence_threshold: float = 0.55
    storage_dir: str = str(BACKEND_DIR / "storage")
    allow_mock_data: bool = True
    sms_enabled: bool = False

    @property
    def sms_configured(self) -> bool:
        provider = self.sms_provider.strip().lower()
        if provider in {"msg91", "fast2sms"}:
            return bool(self.sms_api_key)
        if provider == "twilio":
            return bool(self.sms_account_sid and self.sms_auth_token and self.sms_from_number)
        return False

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_for_startup(self) -> None:
        if self.is_production:
            weak = {"", "changeme", "dev-insecure-secret-change-me", "secret"}
            if self.secret_key.lower() in weak or len(self.secret_key) < 32:
                raise RuntimeError(
                    "SECRET_KEY is weak or default. Set a random 32+ character value before running production."
                )
            if self.allow_mock_data:
                raise RuntimeError(
                    "ALLOW_MOCK_DATA must be false in production: mock data may never be served as real."
                )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
