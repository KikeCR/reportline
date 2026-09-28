"""Typed, validated application configuration.

Every setting is read from the environment (or a local ``.env`` file) and
validated at import time - see ``docs/adr/0000-conventions-from-savestate.md``
§2 for why this deviates from SaveState's plain, unvalidated ``Config``
class.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    flask_env: str = Field(default="production", alias="FLASK_ENV")
    secret_key: str = Field(alias="SECRET_KEY")

    mongodb_uri: str = Field(alias="MONGODB_URI")
    mongodb_db_name: str = Field(alias="MONGODB_DB_NAME")
    mongodb_max_pool_size: int = Field(default=50, alias="MONGODB_MAX_POOL_SIZE")
    mongodb_min_pool_size: int = Field(default=0, alias="MONGODB_MIN_POOL_SIZE")
    mongodb_server_selection_timeout_ms: int = Field(
        default=5000, alias="MONGODB_SERVER_SELECTION_TIMEOUT_MS"
    )
    mongodb_socket_timeout_ms: int = Field(default=20000, alias="MONGODB_SOCKET_TIMEOUT_MS")
    mongodb_slow_query_threshold_ms: int = Field(
        default=100, alias="MONGODB_SLOW_QUERY_THRESHOLD_MS"
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        return self.flask_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide, cached ``Settings`` instance."""
    return Settings()  # type: ignore[call-arg]
