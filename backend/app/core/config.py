"""Environment-backed settings for the OPERATIX API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import quote_plus

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration without exposing secrets in logs or source control."""

    app_name: str
    app_env: str
    database_url: str
    jwt_secret: str = ""
    jwt_access_token_minutes: int = 30
    storage_root: str = "storage"
    max_upload_bytes: int = 10 * 1024 * 1024
    frontend_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    telegram_bot_token: str = ""
    telegram_poll_interval_seconds: int = 5

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from environment variables and local developer files."""
        load_dotenv(".env.local", override=False)
        load_dotenv(".env", override=False)

        configured_url = os.getenv("DATABASE_URL", "").strip()
        if configured_url:
            database_url = configured_url
        else:
            user = os.getenv("MYSQL_USER", "operatix").strip()
            password = os.getenv("MYSQL_PASSWORD", "")
            host = os.getenv("MYSQL_HOST", "127.0.0.1").strip()
            port = os.getenv("MYSQL_PORT", "3306").strip()
            database = os.getenv("MYSQL_DATABASE", "operatix").strip()
            database_url = (
                f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
                f"@{host}:{port}/{quote_plus(database)}"
            )

        raw_expiration = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30").strip()
        try:
            expiration_minutes = int(raw_expiration)
        except ValueError as error:
            raise ValueError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES debe ser un entero.") from error
        if not 5 <= expiration_minutes <= 1_440:
            raise ValueError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES debe estar entre 5 y 1440.")

        raw_max_upload = os.getenv("OPERATIX_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)).strip()
        try:
            max_upload_bytes = int(raw_max_upload)
        except ValueError as error:
            raise ValueError("OPERATIX_MAX_UPLOAD_BYTES debe ser un entero.") from error
        if not 1_024 <= max_upload_bytes <= 100 * 1024 * 1024:
            raise ValueError("OPERATIX_MAX_UPLOAD_BYTES debe estar entre 1024 y 104857600.")

        raw_origins = os.getenv(
            "OPERATIX_FRONTEND_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
        frontend_origins = tuple(
            origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()
        )
        if not frontend_origins:
            raise ValueError("OPERATIX_FRONTEND_ORIGINS debe contener al menos un origen.")

        raw_poll_interval = os.getenv("TELEGRAM_POLL_INTERVAL_SECONDS", "5").strip()
        try:
            telegram_poll_interval_seconds = int(raw_poll_interval)
        except ValueError as error:
            raise ValueError("TELEGRAM_POLL_INTERVAL_SECONDS debe ser un entero.") from error
        if not 1 <= telegram_poll_interval_seconds <= 300:
            raise ValueError("TELEGRAM_POLL_INTERVAL_SECONDS debe estar entre 1 y 300.")

        return cls(
            app_name=os.getenv("APP_NAME", "OPERATIX API").strip(),
            app_env=os.getenv("APP_ENV", "development").strip(),
            database_url=database_url,
            jwt_secret=os.getenv("JWT_SECRET", "").strip(),
            jwt_access_token_minutes=expiration_minutes,
            storage_root=os.getenv("OPERATIX_STORAGE_ROOT", "storage").strip() or "storage",
            max_upload_bytes=max_upload_bytes,
            frontend_origins=frontend_origins,
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_poll_interval_seconds=telegram_poll_interval_seconds,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one immutable settings instance per process."""
    return Settings.from_env()
