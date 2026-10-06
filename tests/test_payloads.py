import asyncio
import os
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from cache_service.config import Settings
from cache_service.identity import payload_identity
from cache_service.main import create_app
from cache_service.transformation import uppercase_transform


@pytest.fixture
async def payload_app():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL database")
    marker = str(uuid4())
    app = create_app(Settings(database_url=url))
    async with app.router.lifespan_context(app):
        try:
            yield app, marker
        finally:
            async with app.state.engine.begin() as connection:
                await connection.execute(
                    text("DELETE FROM payloads WHERE canonical_input LIKE :marker"),
                    {"marker": f"%{marker}%"},
                )


@pytest.mark.integration
async def test_create_read_reuse_and_restart(payload_app):
    app, marker = payload_app
    calls = []

    async def transform(source):
        calls.append(source)
        return await uppercase_transform(source)

    settings = Settings(database_url=os.environ["TEST_DATABASE_URL"])
    application = create_app(settings, transformer=transform)
    data = {"list1": [f"hello {marker}", "world"], "list2": ["one", "two"]}
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as c:
            response = await c.post("/payloads", json=data)
            assert response.status_code == 200
            identifier = response.json()["id"]
            UUID(identifier)
            assert (await c.get(f"/payloads/{identifier}")).json() == {
                "output": f"HELLO {marker.upper()}, ONE, WORLD, TWO"
            }
            assert (await c.post("/payloads", json=data)).json() == {"id": identifier}
            assert calls == [*data["list1"], *data["list2"]]
            distinct = {**data, "list1": [f"HELLO {marker}", "world"]}
            assert (await c.post("/payloads", json=distinct)).json()["id"] != identifier

    # A fresh application and pool reuse persisted payloads, without transformation.
    async def unexpected_transform(source):
        pytest.fail("Stored payload should bypass transformation")

    restarted = create_app(settings, transformer=unexpected_transform)
    async with restarted.router.lifespan_context(restarted):
        async with AsyncClient(transport=ASGITransport(app=restarted), base_url="http://test") as c:
            assert (await c.post("/payloads", json=data)).json() == {"id": identifier}
            assert (await c.get(f"/payloads/{identifier}")).status_code == 200


@pytest.mark.integration
async def test_empty_and_unknown_payload(payload_app):
    app, marker = payload_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post("/payloads", json={"list1": [], "list2": []})
        assert response.status_code == 200
        assert (await c.get(f"/payloads/{response.json()['id']}")).json() == {"output": ""}
        response = await c.post("/payloads", json={"list1": [marker, ""], "list2": ["", ""]})
        assert (await c.get(f"/payloads/{response.json()['id']}")).json() == {
            "output": f"{marker.upper()}, , , "
        }
        response = await c.get(f"/payloads/{uuid4()}")
        assert response.status_code == 404
        assert response.json() == {"detail": "Payload not found"}
        assert (await c.get("/payloads/not-a-uuid")).status_code == 422


@pytest.mark.integration
async def test_concurrent_publication_returns_authoritative_id(payload_app):
    app, marker = payload_app
    arrived = 0
    both_started = asyncio.Event()

    async def transform(source):
        nonlocal arrived
        if source == marker:
            arrived += 1
            if arrived == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=5)
        return source.upper()

    application = create_app(
        Settings(database_url=os.environ["TEST_DATABASE_URL"]), transformer=transform
    )
    data = {"list1": [marker], "list2": ["shared"]}
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as c:
            responses = await asyncio.gather(*(c.post("/payloads", json=data) for _ in range(2)))
            assert [response.status_code for response in responses] == [200, 200]
            assert responses[0].json() == responses[1].json()
    async with app.state.engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM payloads WHERE input_digest = :digest"),
                {"digest": payload_identity(**data).input_digest},
            )
            == 1
        )


@pytest.mark.integration
async def test_failed_transform_does_not_publish(payload_app):
    app, marker = payload_app

    async def transform(source):
        if source == "fail":
            raise OSError("private transformer diagnostics")
        return source.upper()

    application = create_app(
        Settings(database_url=os.environ["TEST_DATABASE_URL"]), transformer=transform
    )
    data = {"list1": [marker], "list2": ["fail"]}
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as c:
            response = await c.post("/payloads", json=data)
            assert response.status_code == 502
            assert response.json() == {"detail": "Transformation failed"}
    async with app.state.engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM payloads WHERE input_digest = :digest"),
                {"digest": payload_identity(**data).input_digest},
            )
            == 0
        )


@pytest.mark.integration
async def test_payload_digest_collision_is_rejected(payload_app):
    app, marker = payload_app
    data = {"list1": [marker], "list2": ["collision"]}
    async with app.state.engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO payloads (id, input_digest, canonical_input, output) "
                "VALUES (:id, :digest, :canonical, :output)"
            ),
            {
                "id": uuid4(),
                "digest": payload_identity(**data).input_digest,
                "canonical": marker,
                "output": "wrong",
            },
        )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post("/payloads", json=data)
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}


@pytest.mark.parametrize(
    "data",
    [
        {"list1": [1], "list2": ["a"]},
        {"list1": [], "list2": ["a"]},
        {"list1": [], "list2": [], "extra": True},
        {"list1": None, "list2": []},
        [],
    ],
)
async def test_invalid_payload_is_rejected_before_database_access(data):
    app = create_app(Settings(_env_file=None, db_pass="test", db_port=1))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.post("/payloads", json=data)
            assert response.status_code == 422
            assert isinstance(response.json()["detail"], list)


async def test_request_validation_uses_configured_limits():
    settings = Settings(_env_file=None, db_pass="test", db_port=1, max_list_items=1)
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.post("/payloads", json={"list1": ["a", "b"], "list2": ["c", "d"]})
            assert response.status_code == 422
            assert "List item limit exceeded" in response.json()["detail"][0]["msg"]


@pytest.mark.integration
async def test_generation_deadline_does_not_publish_and_retry_succeeds(payload_app):
    app, marker = payload_app
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow_transform(source):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    settings = Settings(
        database_url=os.environ["TEST_DATABASE_URL"], generation_timeout_seconds=0.2
    )
    application = create_app(settings, transformer=slow_transform)
    data = {"list1": [marker], "list2": ["deadline"]}
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            response = await client.post("/payloads", json=data)
            assert response.status_code == 504
            assert response.json() == {"detail": "Request timed out"}
            assert started.is_set() and cancelled.is_set()
    async with app.state.engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM payloads WHERE input_digest = :digest"),
                {"digest": payload_identity(**data).input_digest},
            )
            == 0
        )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/payloads", json=data)).status_code == 200


@pytest.mark.integration
async def test_collision_on_publication_readback_is_rejected(payload_app):
    app, marker = payload_app
    data = {"list1": [marker], "list2": ["publication"]}

    async def transform(source):
        if source == marker:
            async with app.state.engine.begin() as connection:
                await connection.execute(
                    text(
                        "INSERT INTO payloads (id, input_digest, canonical_input, output) "
                        "VALUES (:id, :digest, :canonical, :output)"
                    ),
                    {
                        "id": uuid4(),
                        "digest": payload_identity(**data).input_digest,
                        "canonical": marker,
                        "output": "wrong",
                    },
                )
        return source.upper()

    application = create_app(
        Settings(database_url=os.environ["TEST_DATABASE_URL"]), transformer=transform
    )
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            response = await client.post("/payloads", json=data)
            assert response.status_code == 500
            assert response.json() == {"detail": "Internal server error"}


@pytest.mark.integration
async def test_custom_limit_can_exceed_default(payload_app):
    app, marker = payload_app
    settings = Settings(database_url=os.environ["TEST_DATABASE_URL"], max_list_items=101)
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            response = await client.post(
                "/payloads", json={"list1": [marker] * 101, "list2": [""] * 101}
            )
            assert response.status_code == 200
