import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class IntegrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    test_database_url: SecretStr = SecretStr("")


def pytest_configure() -> None:
    """Supply only the test database setting to existing fixtures and child processes."""
    url = IntegrationSettings().test_database_url.get_secret_value()
    if url:
        os.environ.setdefault("TEST_DATABASE_URL", url)
