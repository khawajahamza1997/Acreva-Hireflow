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
    ai_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    cv_processing_concurrency: int = 5
    max_batch_files: int = 300
    max_cv_file_bytes: int = 10 * 1024 * 1024
    max_recording_bytes: int = 25 * 1024 * 1024
    needs_review_min_words: int = 50

    rate_limit_auth_per_minute: int = 10
    rate_limit_upload_per_minute: int = 5
    rate_limit_ask_per_minute: int = 20
    rate_limit_scoring_per_minute: int = 10

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
