import os

import pytest
from conftest import pytest_configure


@pytest.fixture
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TEST_DATABASE_URL", "")
    monkeypatch.delenv("TEST_DATABASE_URL")
    return tmp_path


def test_loads_test_database_from_dotenv(isolated_environment):
    url = "postgresql+asyncpg://test:sentinel@localhost/cache_test"
    (isolated_environment / ".env").write_text(
        f'TEST_DATABASE_URL="{url}"\nDATABASE_URL=ignored\nDB_PASS=ignored\n'
    )

    pytest_configure()

    assert os.environ["TEST_DATABASE_URL"] == url


def test_exported_test_database_overrides_dotenv(isolated_environment, monkeypatch):
    (isolated_environment / ".env").write_text("TEST_DATABASE_URL=dotenv-value\n")
    monkeypatch.setenv("TEST_DATABASE_URL", "exported-value")

    pytest_configure()

    assert os.environ["TEST_DATABASE_URL"] == "exported-value"


@pytest.mark.parametrize("contents", [None, "DATABASE_URL=ignored\nDB_PASS=ignored\n"])
def test_missing_test_database_does_not_fall_back_to_application(isolated_environment, contents):
    if contents is not None:
        (isolated_environment / ".env").write_text(contents)

    pytest_configure()

    assert "TEST_DATABASE_URL" not in os.environ


def test_empty_exported_value_disables_dotenv_database(isolated_environment, monkeypatch):
    (isolated_environment / ".env").write_text("TEST_DATABASE_URL=dotenv-value\n")
    monkeypatch.setenv("TEST_DATABASE_URL", "")

    pytest_configure()

    assert os.environ["TEST_DATABASE_URL"] == ""
