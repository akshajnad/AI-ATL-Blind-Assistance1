import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)


class Settings:
    """Centralized environment configuration."""

    def __init__(self) -> None:
        self._data = {
            "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY"),
            "SNOWFLAKE_ACCOUNT": os.getenv("SNOWFLAKE_ACCOUNT"),
            "SNOWFLAKE_USER": os.getenv("SNOWFLAKE_USER"),
            "SNOWFLAKE_PASSWORD": os.getenv("SNOWFLAKE_PASSWORD"),
            "SNOWFLAKE_ROLE": os.getenv("SNOWFLAKE_ROLE"),
            "SNOWFLAKE_WAREHOUSE": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "SNOWFLAKE_DATABASE": os.getenv("SNOWFLAKE_DATABASE"),
            "SNOWFLAKE_SCHEMA": os.getenv("SNOWFLAKE_SCHEMA"),
            "SNOWFLAKE_MODEL": os.getenv("SNOWFLAKE_MODEL", "mistral-7b"),
        }

    def require(self, key: str) -> str:
        value = self._data.get(key)
        if not value:
            raise RuntimeError(f"Environment variable {key} is required but not set.")
        return value

    def optional(self, key: str) -> Optional[str]:
        return self._data.get(key) or None

    @property
    def elevenlabs_api_key(self) -> Optional[str]:
        return self.optional("ELEVENLABS_API_KEY")

    @property
    def snowflake_account(self) -> Optional[str]:
        return self.optional("SNOWFLAKE_ACCOUNT")

    @property
    def snowflake_user(self) -> Optional[str]:
        return self.optional("SNOWFLAKE_USER")

    @property
    def snowflake_password(self) -> Optional[str]:
        return self.optional("SNOWFLAKE_PASSWORD")

    @property
    def snowflake_role(self) -> Optional[str]:
        return self.optional("SNOWFLAKE_ROLE")

    @property
    def snowflake_warehouse(self) -> Optional[str]:
        return self.optional("SNOWFLAKE_WAREHOUSE")

    @property
    def snowflake_database(self) -> Optional[str]:
        return self.optional("SNOWFLAKE_DATABASE")

    @property
    def snowflake_schema(self) -> Optional[str]:
        return self.optional("SNOWFLAKE_SCHEMA")

    @property
    def snowflake_model(self) -> str:
        return self.optional("SNOWFLAKE_MODEL") or "mistral-7b"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
