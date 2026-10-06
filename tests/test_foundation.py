import os

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from cache_service.config import Settings
from cache_service.main import create_app


def test_database_configuration_is_required(monkeypatch):
    monkeypatch.delenv("CACHE_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_credentials_are_masked():
    password = "sentinel-private-password"
    settings = Settings(database_url=f"postgresql+asyncpg://cache:{password}@localhost/cache")
    assert password not in repr(settings)
    assert password not in settings.model_dump_json()
    with pytest.raises(ValidationError) as error:
        Settings(database_url=f"invalid://cache:{password}@localhost/cache")
    assert password not in str(error.value)


def test_liveness_does_not_require_database():
    settings = Settings(database_url="postgresql+asyncpg://cache:cache@127.0.0.1:1/cache")
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "Database is not ready"}


@pytest.mark.integration
def test_readiness_against_migrated_postgresql():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL database")
    with TestClient(create_app(Settings(database_url=url))) as client:
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
