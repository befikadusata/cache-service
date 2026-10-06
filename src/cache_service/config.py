from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CACHE_", env_file=".env", extra="ignore")

    database_url: PostgresDsn
    pool_size: int = Field(default=10, ge=2, le=100)
    pool_timeout_seconds: float = Field(default=5, gt=0)
    database_connect_timeout_seconds: float = Field(default=5, gt=0)
    database_statement_timeout_seconds: float = Field(default=5, gt=0)
