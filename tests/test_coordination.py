import asyncio
import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from cache_service.cache import cached_transformations
from cache_service.config import Settings
from cache_service.coordination import Coordination, DatabaseUnavailable
from cache_service.database import create_engine
from cache_service.identity import transformation_identity
from cache_service.main import create_app


@pytest.mark.parametrize("changes", [
    {"pool_size": 2, "coordination_slots": 2},
    {"coordination_slots": 0},
    {"admission_timeout_seconds": 0},
    {"advisory_lock_timeout_seconds": 0},
    {"transformation_timeout_seconds": float("inf")},
    {"cleanup_timeout_seconds": float("nan")},
    {"pool_timeout_seconds": float("inf")},
    {"database_statement_timeout_seconds": float("nan")},
])
def test_capacity_and_budgets_are_validated(changes):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, db_pass="test", **changes)


async def test_cleanup_survives_repeated_cancellation(monkeypatch):
    coordination = Coordination(Settings(_env_file=None, db_pass="test"))
    started, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def cleanup(*args):
        started.set()
        await release.wait()
        finished.set()

    monkeypatch.setattr(coordination, "_cleanup", cleanup)
    task = asyncio.create_task(coordination._protected_cleanup(None, 1, True, None))
    await started.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.sleep(0)
    assert not finished.is_set()
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished.is_set()


@pytest.fixture
async def database():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL database")
    settings = Settings(
        database_url=url, pool_size=2, coordination_slots=1,
        admission_timeout_seconds=0.05, advisory_lock_timeout_seconds=0.05,
        transformation_timeout_seconds=0.2, cleanup_timeout_seconds=0.2,
        pool_timeout_seconds=0.05,
    )
    engine = create_engine(settings)
    version = f"test-coordination-{uuid4()}"
    try:
        yield engine, settings, version
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM transformations WHERE version = :version"), {"version": version}
            )
            await connection.execute(
                text("DELETE FROM payloads WHERE canonical_input LIKE :version"),
                {"version": f"%{version}%"},
            )
        await engine.dispose()


async def uppercase(source):
    return source.upper()


@pytest.mark.integration
async def test_saturated_admission_preserves_read_capacity_and_recovers(database):
    engine, settings, version = database
    started, release = asyncio.Event(), asyncio.Event()

    async def holder(source):
        started.set()
        await release.wait()
        return source.upper()

    task = asyncio.create_task(cached_transformations(engine, ["held"], holder, version))
    try:
        await asyncio.wait_for(started.wait(), 2)
        with pytest.raises(DatabaseUnavailable, match="capacity"):
            await cached_transformations(engine, ["other"], uppercase, version)
        # One slot occupies one connection; ordinary reads still make progress.
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT 1")) == 1
        assert engine.pool.checkedout() == 1
        release.set()
        assert await task == {"held": "HELD"}
        assert await cached_transformations(engine, ["other"], uppercase, version) == {
            "other": "OTHER"
        }
        assert engine.pool.checkedout() == 0
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.integration
async def test_lock_wait_timeout_does_not_transform_and_retry_succeeds(database):
    engine, settings, version = database
    key = transformation_identity("locked", version=version).advisory_key
    calls = []

    async def transform(source):
        calls.append(source)
        return source.upper()

    async with engine.connect() as holder:
        await holder.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
        await holder.commit()
        app = create_app(settings, transformer=transform, transformer_version=version)
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/payloads", json={"list1": ["locked"], "list2": ["locked"]}
                )
                assert response.status_code == 503
                assert response.json() == {"detail": "Database unavailable"}
                assert response.headers["Retry-After"] == "1"
                assert calls == []
                await holder.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                await holder.commit()
                assert (await client.post(
                    "/payloads", json={"list1": ["locked"], "list2": ["locked"]}
                )).status_code == 200
        assert calls == ["locked"]


@pytest.mark.integration
async def test_transform_deadline_returns_504_and_releases_connection(database):
    engine, settings, version = database

    async def slow(source):
        await asyncio.Event().wait()

    app = create_app(settings, transformer=slow, transformer_version=version)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/payloads", json={"list1": ["slow"], "list2": ["slow"]})
            assert response.status_code == 504
            assert app.state.engine.pool.checkedout() == 0
    assert await cached_transformations(engine, ["slow"], uppercase, version) == {"slow": "SLOW"}


@pytest.mark.integration
async def test_checkout_timeout_releases_admission(database):
    engine, settings, version = database
    coordination = engine.get_execution_options()["cache_coordination"]
    async with engine.connect(), engine.connect():
        with pytest.raises(DatabaseUnavailable):
            async with coordination.connection(engine, 1):
                pytest.fail("Saturated pool must time out")
    assert await cached_transformations(engine, ["retry"], uppercase, version) == {"retry": "RETRY"}


@pytest.mark.integration
async def test_cancellation_discards_lock_session_and_allows_retry(database):
    engine, settings, version = database
    started = asyncio.Event()

    async def blocked(source):
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(cached_transformations(engine, ["cancel"], blocked, version))
    await asyncio.wait_for(started.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert engine.pool.checkedout() == 0
    assert await cached_transformations(engine, ["cancel"], uppercase, version) == {
        "cancel": "CANCEL"
    }


@pytest.mark.integration
async def test_cleanup_timeout_force_closes_session_and_releases_lock(database, monkeypatch):
    engine, settings, version = database
    scalar = AsyncConnection.scalar

    async def stalled_unlock(connection, statement, *args, **kwargs):
        if "pg_advisory_unlock" in str(statement):
            await asyncio.Event().wait()
        return await scalar(connection, statement, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(AsyncConnection, "scalar", stalled_unlock)
        with pytest.raises(DatabaseUnavailable, match="cleanup"):
            await cached_transformations(engine, ["cleanup"], uppercase, version)
    assert engine.pool.checkedout() == 0
    # Successful cache commit preceded failed cleanup; another session can get the lock.
    key = transformation_identity("cleanup", version=version).advisory_key
    async with engine.begin() as connection:
        assert await connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
        assert await connection.scalar(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
    assert await cached_transformations(engine, ["cleanup"], uppercase, version) == {
        "cleanup": "CLEANUP"
    }


@pytest.mark.integration
async def test_admission_failure_returns_retryable_503(database):
    engine, settings, version = database
    app = create_app(settings, transformer=uppercase, transformer_version=version)
    async with app.router.lifespan_context(app):
        coordination = app.state.engine.get_execution_options()["cache_coordination"]
        await coordination.slots.acquire()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/payloads", json={"list1": ["a"], "list2": ["b"]})
                assert response.status_code == 503
                assert response.headers["Retry-After"] == "1"
                assert app.state.engine.pool.checkedout() == 0
        finally:
            coordination.slots.release()


@pytest.mark.integration
async def test_uncertain_acquisition_is_discarded_and_wait_settings_do_not_leak(
    database, monkeypatch
):
    engine, settings, version = database
    execute = AsyncConnection.execute
    key = transformation_identity("uncertain", version=version).advisory_key

    async def interrupted(connection, statement, *args, **kwargs):
        result = await execute(connection, statement, *args, **kwargs)
        if "SELECT pg_advisory_lock(" in str(statement):
            raise asyncio.CancelledError
        return result

    with monkeypatch.context() as patch:
        patch.setattr(AsyncConnection, "execute", interrupted)
        with pytest.raises(asyncio.CancelledError):
            await cached_transformations(engine, ["uncertain"], uppercase, version)
    assert engine.pool.checkedout() == 0
    async with engine.begin() as connection:
        assert await connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
        assert await connection.scalar(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
    assert await cached_transformations(engine, ["uncertain"], uppercase, version) == {
        "uncertain": "UNCERTAIN"
    }
    async with engine.connect() as connection:
        assert await connection.scalar(text("SHOW lock_timeout")) == "0"
        assert await connection.scalar(text("SHOW statement_timeout")) == "5s"
