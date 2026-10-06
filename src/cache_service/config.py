from pydantic import Field, PostgresDsn, SecretStr, TypeAdapter, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    database_url: SecretStr

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = TypeAdapter(PostgresDsn).validate_python(value.get_secret_value())
            if url.scheme != "postgresql+asyncpg":
                raise ValueError
        except ValueError:
            raise ValueError("Database URL must use postgresql+asyncpg") from None
        return value

    pool_size: int = Field(default=10, ge=2, le=100)
    pool_timeout_seconds: float = Field(default=5, gt=0)
    database_connect_timeout_seconds: float = Field(default=5, gt=0)
    database_statement_timeout_seconds: float = Field(default=5, gt=0)
