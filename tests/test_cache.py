import asyncio
import os
from unittest.mock import Mock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text

from cache_service.cache import DatabaseUnavailable, TransformationFailed, cached_transformations
from cache_service.config import Settings
from cache_service.database import create_engine
from cache_service.identity import (
    IdentityCollisionError,
    TransformationIdentity,
    transformation_identity,
)
from cache_service.main import create_app


@pytest.fixture
async def cache_database():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL database")
    engine = create_engine(Settings(database_url=url))
    version = f"test-cache-{uuid4()}"
    try:
        yield engine, version
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


async def insert_result(engine, source, version, result, *, retained_source=None):
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO transformations (version, source_digest, source, result) "
                "VALUES (:version, :digest, :source, :result)"
            ),
            {
                "version": version,
                "digest": transformation_identity(source, version=version).source_digest,
                "source": source if retained_source is None else retained_source,
                "result": result,
            },
        )


async def test_empty_input_avoids_database_and_transformer():
    engine, transform = Mock(), Mock()
    assert await cached_transformations(engine, [], transform, "test") == {}
    engine.connect.assert_not_called()
    transform.assert_not_called()


async def test_colliding_request_sources_are_rejected_before_lookup(monkeypatch):
    engine, transform = Mock(), Mock()
    monkeypatch.setattr(
        "cache_service.cache.transformation_identity",
        lambda source, version: TransformationIdentity(version, source, b"x" * 32),
    )
    with pytest.raises(IdentityCollisionError):
        await cached_transformations(engine, ["first", "second"], transform, "test")
    engine.connect.assert_not_called()
    transform.assert_not_called()


async def test_database_connection_timeout_is_distinct_from_transformer_timeout():
    engine, transform = Mock(), Mock()
    engine.connect.side_effect = TimeoutError()
    with pytest.raises(DatabaseUnavailable):
        await cached_transformations(engine, ["a"], transform, "test")
    transform.assert_not_called()


@pytest.mark.integration
async def test_deduplication_batch_reads_and_no_connection_during_transform(cache_database):
    engine, version = cache_database
    await insert_result(engine, "cached", version, "STORED")
    statements, calls = [], []

    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)

    async def transform(source):
        assert engine.pool.checkedout() == 0
        calls.append(source)
        return source.upper()

    try:
        assert await cached_transformations(
            engine, ["cached", "new", "new", "", "cached", ""], transform, version
        ) == {"cached": "STORED", "new": "NEW", "": ""}
        assert calls == ["new", ""]
        batch_reads = [statement for statement in statements if "source_digest IN" in statement]
        assert len(batch_reads) == 1
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)


@pytest.mark.integration
async def test_large_cached_request_uses_bounded_batches(cache_database):
    engine, version = cache_database
    sources = [str(index) for index in range(501)]
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO transformations (version, source_digest, source, result) "
                "VALUES (:version, :digest, :source, :result)"
            ),
            [
                {
                    "version": version,
                    "digest": transformation_identity(source, version=version).source_digest,
                    "source": source,
                    "result": source,
                }
                for source in sources
            ],
        )
    batch_reads = []

    def record(connection, cursor, statement, parameters, context, executemany):
        if "source_digest IN" in statement:
            batch_reads.append(statement)

    async def unexpected(source):
        pytest.fail("Cached result must bypass transformer")

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        assert await cached_transformations(engine, sources, unexpected, version) == {
            source: source for source in sources
        }
        assert len(batch_reads) == 2
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)


@pytest.mark.integration
async def test_payload_overlap_and_restart_reuse_cached_strings(cache_database):
    engine, version = cache_database
    settings = Settings(database_url=os.environ["TEST_DATABASE_URL"])
    calls = []

    async def transform(source):
        calls.append(source)
        return source.upper()

    app = create_app(settings, transformer=transform, transformer_version=version)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post("/payloads", json={"list1": ["a", "a"], "list2": ["b", "a"]})
            assert first.status_code == 200
            second = await client.post("/payloads", json={"list1": ["b", "c"], "list2": ["a", "b"]})
            assert second.status_code == 200
            assert first.json() != second.json()
            assert (await client.get(f"/payloads/{second.json()['id']}")).json() == {
                "output": "B, A, C, B"
            }
            assert calls == ["a", "b", "c"]

    async def unexpected(source):
        pytest.fail("Restart must reuse stored transformations")

    restarted = create_app(settings, transformer=unexpected, transformer_version=version)
    async with restarted.router.lifespan_context(restarted):
        async with AsyncClient(
            transport=ASGITransport(app=restarted), base_url="http://test"
        ) as client:
            # New payload identity forces per-string lookup rather than payload reuse.
            response = await client.post("/payloads", json={"list1": ["c"], "list2": ["a"]})
            assert response.status_code == 200
            assert (await client.get(f"/payloads/{response.json()['id']}")).json() == {
                "output": "C, A"
            }


@pytest.mark.integration
async def test_failure_retains_successful_results_and_retries_only_misses(cache_database):
    engine, version = cache_database
    calls = []

    async def failing(source):
        calls.append(source)
        if source == "bad":
            raise ValueError("private input diagnostics")
        return source.upper()

    with pytest.raises(TransformationFailed, match="^Transformation failed$"):
        await cached_transformations(engine, ["good", "bad", "later"], failing, version)
    async with engine.connect() as connection:
        assert (
            await connection.execute(
                text("SELECT source FROM transformations WHERE version = :version"),
                {"version": version},
            )
        ).scalars().all() == ["good"]

    async def recovered(source):
        calls.append(source)
        return source.upper()

    assert await cached_transformations(engine, ["good", "bad", "later"], recovered, version) == {
        "good": "GOOD",
        "bad": "BAD",
        "later": "LATER",
    }
    assert calls == ["good", "bad", "bad", "later"]


@pytest.mark.integration
@pytest.mark.parametrize("error", [TimeoutError, asyncio.CancelledError])
async def test_interrupted_transformation_is_not_cached(cache_database, error):
    engine, version = cache_database

    async def interrupted(source):
        raise error()

    with pytest.raises(error):
        await cached_transformations(engine, ["missing"], interrupted, version)
    async with engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM transformations WHERE version = :version"),
                {"version": version},
            )
            == 0
        )


@pytest.mark.integration
async def test_version_change_does_not_reuse_old_result(cache_database):
    engine, version = cache_database
    await insert_result(engine, "a", "old-" + version, "OLD")
    try:
        calls = []

        async def transform(source):
            calls.append(source)
            return "NEW"

        assert await cached_transformations(engine, ["a"], transform, version) == {"a": "NEW"}
        assert calls == ["a"]
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM transformations WHERE version = :version"),
                {"version": "old-" + version},
            )


@pytest.mark.integration
@pytest.mark.parametrize("during_transform", [False, True])
async def test_collision_is_rejected_at_lookup_and_readback(cache_database, during_transform):
    engine, version = cache_database
    calls = []

    async def insert_collision():
        await insert_result(engine, "a", version, "WRONG", retained_source="different")

    if not during_transform:
        await insert_collision()

    async def transform(source):
        calls.append(source)
        await insert_collision()
        return "LOCAL"

    with pytest.raises(IdentityCollisionError):
        await cached_transformations(engine, ["a"], transform, version)
    assert calls == (["a"] if during_transform else [])


@pytest.mark.integration
async def test_conflicting_insert_returns_authoritative_stored_result(cache_database):
    engine, version = cache_database

    async def transform(source):
        await insert_result(engine, source, version, "WINNER")
        return "LOSER"

    assert await cached_transformations(engine, ["a", "a"], transform, version) == {"a": "WINNER"}
