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

        return cls(
            app_name=os.getenv("APP_NAME", "OPERATIX API").strip(),
            app_env=os.getenv("APP_ENV", "development").strip(),
            database_url=database_url,
            jwt_secret=os.getenv("JWT_SECRET", "").strip(),
            jwt_access_token_minutes=expiration_minutes,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one immutable settings instance per process."""
    return Settings.from_env()
