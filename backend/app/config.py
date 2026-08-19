"""Application configuration.

All configuration is read from environment variables (12-factor style) so the
same image runs in development and production with different settings. Never
hardcode secrets here.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- General ----
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = "Home Music API"
    # Secret used to sign session tokens. MUST be overridden in production.
    secret_key: str = Field(default="dev-insecure-change-me", alias="SECRET_KEY")

    # ---- Database ----
    # SQLite by default; point DATABASE_URL at Postgres to migrate with no code change.
    # e.g. postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str = Field(default="sqlite:///./data/app.db", alias="DATABASE_URL")

    # ---- Sessions / cookies ----
    session_cookie_name: str = Field(default="hm_session", alias="SESSION_COOKIE_NAME")
    session_ttl_seconds: int = Field(default=2_592_000, alias="SESSION_TTL_SECONDS")  # 30 days
    # CSRF double-submit cookie companion.
    csrf_cookie_name: str = Field(default="hm_csrf", alias="CSRF_COOKIE_NAME")
    csrf_header_name: str = Field(default="X-CSRF-Token", alias="CSRF_HEADER_NAME")

    # ---- CORS ----
    # Comma-separated list of allowed origins for development. Empty in production
    # because the frontend is served same-origin behind a reverse proxy.
    frontend_origin: str = Field(default="", alias="FRONTEND_ORIGIN")

    # ---- Integrations ----
    mock_external_services: bool = Field(default=True, alias="MOCK_EXTERNAL_SERVICES")

    droppedneedle_url: str = Field(default="", alias="DROPPEDNEEDLE_URL")
    # DroppedNeedle authenticates with its own account and returns a bearer
    # token. This is deliberately separate from SLSKD_API_KEY.
    droppedneedle_username: str = Field(default="", alias="DROPPEDNEEDLE_USERNAME")
    droppedneedle_password: str = Field(default="", alias="DROPPEDNEEDLE_PASSWORD")
    # Used only by Resonar's server-side catalogue fallback when
    # DroppedNeedle's shorter upstream deadline is exceeded.
    musicbrainz_timeout_seconds: float = Field(default=30.0, alias="MUSICBRAINZ_TIMEOUT_SECONDS")

    navidrome_url: str = Field(default="", alias="NAVIDROME_URL")
    navidrome_username: str = Field(default="", alias="NAVIDROME_USERNAME")
    navidrome_password: str = Field(default="", alias="NAVIDROME_PASSWORD")

    slskd_url: str = Field(default="", alias="SLSKD_URL")
    slskd_api_key: str = Field(default="", alias="SLSKD_API_KEY")

    # ---- Background worker ----
    request_poll_interval_seconds: int = Field(default=10, alias="REQUEST_POLL_INTERVAL_SECONDS")

    # ---- Limits ----
    search_min_query_length: int = Field(default=2, alias="SEARCH_MIN_QUERY_LENGTH")
    search_max_query_length: int = Field(default=120, alias="SEARCH_MAX_QUERY_LENGTH")
    search_result_limit: int = Field(default=50, alias="SEARCH_RESULT_LIMIT")
    history_max_entries: int = Field(default=200, alias="HISTORY_MAX_ENTRIES")

    # ---- Bootstrap admin ----
    bootstrap_admin_username: str = Field(default="", alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_password: str = Field(default="", alias="BOOTSTRAP_ADMIN_PASSWORD")
    bootstrap_admin_display_name: str = Field(default="Admin", alias="BOOTSTRAP_ADMIN_DISPLAY_NAME")

    # Default password assigned to users created via the admin panel (they should
    # change it on first login). Never logged.
    default_user_password: str = Field(default="changeme", alias="DEFAULT_USER_PASSWORD")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def cors_origins(self) -> List[str]:
        if not self.frontend_origin:
            return []
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @field_validator("secret_key")
    @classmethod
    def _warn_default_secret(cls, v: str) -> str:
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
