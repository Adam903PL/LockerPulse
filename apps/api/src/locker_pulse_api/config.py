from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", "../../.env"),
        extra="ignore",
    )

    app_name: str = "LockerPulse API"
    inpost_api_base_url: str = Field(
        default="https://api-global-points.easypack24.net/v1",
        validation_alias="INPOST_API_BASE_URL",
    )
    inpost_request_timeout_seconds: float = Field(
        default=10,
        validation_alias="INPOST_REQUEST_TIMEOUT_SECONDS",
    )
    nominatim_api_base_url: str = Field(
        default="https://nominatim.openstreetmap.org",
        validation_alias="NOMINATIM_API_BASE_URL",
    )
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    web_origin: str = Field(default="http://localhost:3000", validation_alias="WEB_ORIGIN")
    report_triage_provider: str = Field(default="auto", validation_alias="REPORT_TRIAGE_PROVIDER")
    report_triage_model: str = Field(default="", validation_alias="REPORT_TRIAGE_MODEL")
    report_triage_api_base: str | None = Field(default=None, validation_alias="REPORT_TRIAGE_API_BASE")
    report_triage_allow_cloud_photos: bool = Field(
        default=False,
        validation_alias="REPORT_TRIAGE_ALLOW_CLOUD_PHOTOS",
    )
    report_triage_local_model_prefixes: str = Field(
        default="ollama/,ollama_chat/,local/",
        validation_alias="REPORT_TRIAGE_LOCAL_MODEL_PREFIXES",
    )
    report_triage_timeout_seconds: float = Field(default=60, validation_alias="REPORT_TRIAGE_TIMEOUT_SECONDS")
    report_triage_prompt_version: str = Field(
        default="report-triage-v1",
        validation_alias="REPORT_TRIAGE_PROMPT_VERSION",
    )
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", validation_alias="OLLAMA_BASE_URL")
    admin_token: str | None = Field(default=None, validation_alias="ADMIN_TOKEN")

    @property
    def cors_origins(self) -> list[str]:
        origins = {self.web_origin, "http://localhost:3000", "http://127.0.0.1:3000"}
        return sorted(origins)

    @property
    def triage_local_model_prefixes(self) -> tuple[str, ...]:
        return tuple(
            prefix.strip()
            for prefix in self.report_triage_local_model_prefixes.split(",")
            if prefix.strip()
        )

    @property
    def effective_report_triage_api_base(self) -> str | None:
        if self.report_triage_api_base:
            return self.report_triage_api_base
        if self.report_triage_model.startswith(("ollama/", "ollama_chat/")):
            return self.ollama_base_url
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
