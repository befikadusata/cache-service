"""Separate spawned applications sharing PostgreSQL, with observable lock contention."""

import asyncio
import multiprocessing
import os
from collections import Counter
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from cache_service.config import Settings
from cache_service.database import create_engine
from cache_service.identity import transformation_identity
from cache_service.main import create_app


def application_process(url, version, requests, release, pipe):
    """Build an independent engine/event loop; report calls and HTTP results over IPC."""
    async def run():
        async def transform(source):
            pipe.send(("call", source))
            if source == "shared":
                if not await asyncio.to_thread(release.wait, 20):
                    raise TimeoutError("Test release was not received")
            return source.upper()

        app = create_app(
            Settings(database_url=url), transformer=transform, transformer_version=version
        )
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                results = []
                for data in requests:
                    created = await c.post("/payloads", json=data)
                    assert created.status_code == 200
                    identifier = created.json()["id"]
                    read = await c.get(f"/payloads/{identifier}")
                    assert read.status_code == 200
                    results.append((identifier, read.json()["output"]))
        pipe.send(("results", results))

    try:
        asyncio.run(run())
    except BaseException as error:
        # Do not send exception diagnostics that could contain connection credentials.
        pipe.send(("error", type(error).__name__))
    finally:
        pipe.close()


def receive(pipe):
    assert pipe.poll(25), "Application process did not respond within its test budget"
    return pipe.recv()


def finish(process, pipe):
    calls = []
    while True:
        kind, value = receive(pipe)
        if kind == "call":
            calls.append(value)
        else:
            assert kind == "results", f"Application process failed: {value}"
            process.join(5)
            assert process.exitcode == 0
            return value, calls


@pytest.mark.integration
@pytest.mark.parametrize("overlapping", [False, True], ids=["identical", "overlapping"])
async def test_processes_coordinate_calls_and_restart_reuses_storage(overlapping):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL database")
    version = f"test-process-{uuid4()}"
    engine = create_engine(Settings(database_url=url))
    context = multiprocessing.get_context("spawn")
    release = context.Event()
    workers = []

    def start(requests):
        parent, child = context.Pipe(duplex=False)
        process = context.Process(
            target=application_process, args=(url, version, requests, release, child)
        )
        process.start()
        child.close()
        workers.append((process, parent))
        return process, parent

    first = {"list1": ["shared", "shared"], "list2": ["left", "shared"]}
    second = (
        {"list1": ["shared", "right"], "list2": ["left", "shared"]}
        if overlapping else first
    )
    try:
        holder, holder_pipe = start([first])
        assert await asyncio.to_thread(receive, holder_pipe) == ("call", "shared")
        waiter, waiter_pipe = start([second])
        key = transformation_identity("shared", version=version).advisory_key
        # PostgreSQL splits the bigint key into two unsigned 32-bit pg_locks fields.
        async with asyncio.timeout(15):
            async with engine.connect() as connection:
                while True:
                    locks = (await connection.execute(
                        text("SELECT pid, granted FROM pg_locks WHERE locktype = 'advisory' "
                             "AND classid = :high AND objid = :low AND objsubid = 1"),
                        {"high": (key >> 32) & 0xFFFFFFFF, "low": key & 0xFFFFFFFF},
                    )).all()
                    if len({pid for pid, _ in locks}) == 2 and {g for _, g in locks} == {
                        True, False
                    }:
                        break
                    await asyncio.sleep(0.02)
        # A real database waiter exists before the first result is allowed to commit.
        release.set()
        first_results, first_calls = await asyncio.to_thread(finish, holder, holder_pipe)
        second_results, second_calls = await asyncio.to_thread(finish, waiter, waiter_pipe)
        counts = Counter(["shared", *first_calls, *second_calls])
        assert counts == Counter({"shared": 1, "left": 1, **({"right": 1} if overlapping else {})})
        assert first_results[0][1] == "SHARED, LEFT, SHARED, SHARED"
        assert second_results[0][1] == (
            "SHARED, LEFT, RIGHT, SHARED" if overlapping else first_results[0][1]
        )
        assert (first_results[0][0] != second_results[0][0]) == overlapping

        # Both original processes have exited. A fresh process reuses IDs and handles
        # a new ordered input, proving cache reuse independently of payload reuse.
        new_input = {"list1": ["left"], "list2": ["shared"]}
        restarted, restarted_pipe = start([first, second, new_input])
        restart_results, restart_calls = await asyncio.to_thread(finish, restarted, restarted_pipe)
        assert restart_calls == []
        assert restart_results[:2] == [first_results[0], second_results[0]]
        assert restart_results[2][1] == "LEFT, SHARED"
        async with engine.connect() as connection:
            assert await connection.scalar(
                text("SELECT count(*) FROM transformations WHERE version = :version"),
                {"version": version},
            ) == len(counts)
    finally:
        release.set()
        for process, pipe in workers:
            if process.is_alive():
                process.terminate()
            await asyncio.to_thread(process.join, 5)
            if process.is_alive():
                process.kill()
                await asyncio.to_thread(process.join, 5)
            pipe.close()
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("DELETE FROM payloads WHERE canonical_input LIKE :version"),
                    {"version": f"%{version}%"},
                )
                await connection.execute(
                    text("DELETE FROM transformations WHERE version = :version"),
                    {"version": version},
                )
        finally:
            await engine.dispose()
