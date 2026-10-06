import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from cache_service.config import Settings


def test_db_environment_builds_url_with_escaped_credentials(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    values = {
        "DB_HOST": "localhost", "DB_PORT": "55432", "DB_USER": "custom@user",
        "DB_NAME": "custom_db", "DB_PASS": "sentinel@:/?#password",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    settings = Settings(_env_file=None)
    url = make_url(settings.database_url.get_secret_value())
    assert (url.host, url.port, url.username, url.database, url.password) == (
        "localhost", 55432, values["DB_USER"], "custom_db", values["DB_PASS"],
    )
    assert values["DB_PASS"] not in repr(settings)
    assert values["DB_PASS"] not in settings.model_dump_json()


def test_database_url_override_takes_precedence():
    value = "postgresql+asyncpg://override:password@localhost:5432/override"
    settings = Settings(_env_file=None, database_url=value, db_user="ignored", db_pass="ignored")
    assert settings.database_url.get_secret_value() == value


@pytest.mark.parametrize("port", [0, 65536])
def test_rejects_invalid_database_port(port):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, db_port=port, db_pass="sentinel")


def test_old_environment_prefixes_do_not_supply_credentials(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_PASS", raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "sentinel")
    monkeypatch.setenv("CACHE_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
    with pytest.raises(ValidationError, match="Set DB_PASS or DATABASE_URL"):
        Settings(_env_file=None)
