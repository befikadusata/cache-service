from pydantic import Field, PostgresDsn, SecretStr, TypeAdapter, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    db_host: str = Field(default="127.0.0.1", min_length=1)
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_user: str = Field(default="cache", min_length=1)
    db_name: str = Field(default="cache", min_length=1)
    db_pass: SecretStr | None = None
    database_url: SecretStr = Field(default_factory=lambda: SecretStr(""))

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if self.database_url.get_secret_value():
            return self
        if self.db_pass is None or not self.db_pass.get_secret_value():
            raise ValueError("Set DB_PASS or DATABASE_URL")
        url = URL.create(
            "postgresql+asyncpg",
            username=self.db_user,
            password=self.db_pass.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )
        self.database_url = SecretStr(url.render_as_string(hide_password=False))
        return self

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            return value
        try:
            url = TypeAdapter(PostgresDsn).validate_python(value.get_secret_value())
            if url.scheme != "postgresql+asyncpg":
                raise ValueError
        except ValueError:
            raise ValueError("Database URL must use postgresql+asyncpg") from None
        return value

    pool_size: int = Field(default=10, ge=2, le=100)
    pool_timeout_seconds: float = Field(default=5, gt=0, allow_inf_nan=False)
    database_connect_timeout_seconds: float = Field(default=5, gt=0, allow_inf_nan=False)
    database_statement_timeout_seconds: float = Field(default=5, gt=0, allow_inf_nan=False)
    max_list_items: int = Field(default=100, ge=1)
    max_string_characters: int = Field(default=10000, ge=1)
    max_total_characters: int = Field(default=100000, ge=1)
    generation_timeout_seconds: float = Field(default=60, gt=0, allow_inf_nan=False)
    read_timeout_seconds: float = Field(default=10, gt=0, allow_inf_nan=False)

    coordination_slots: int = Field(default=8, ge=1)
    admission_timeout_seconds: float = Field(default=5, gt=0, allow_inf_nan=False)
    advisory_lock_timeout_seconds: float = Field(default=35, ge=0.001, allow_inf_nan=False)
    transformation_timeout_seconds: float = Field(default=30, gt=0, allow_inf_nan=False)
    cleanup_timeout_seconds: float = Field(default=5, gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def reserve_read_capacity(self) -> "Settings":
        if self.coordination_slots >= self.pool_size:
            raise ValueError("COORDINATION_SLOTS must be less than POOL_SIZE")
        return self
