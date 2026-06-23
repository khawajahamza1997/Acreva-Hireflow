from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_BACKEND_DIR / ".env"),
            str(_ROOT_DIR / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    openai_api_key: str = ""

    resend_api_key: str = ""
    email_from: str = "Acreva HireFlow <noreply@acreva.com>"
    resend_test_to_email: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""
    stripe_trial_days: int = 14

    frontend_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    support_email: str = "support@acreva.com"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
