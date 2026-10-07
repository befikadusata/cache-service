"""Installed CLI subprocesses talking to a live HTTP server and migrated PostgreSQL."""

import asyncio
import json
import os
import socket
import sys
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
import uvicorn
from sqlalchemy import text

from cache_service.config import Settings
from cache_service.database import create_engine
from cache_service.main import create_app


@pytest.fixture
async def live_cli_service():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL database")
    version = f"test-cli-{uuid4()}"
    calls = []

    async def transform(source):
        calls.append(source)
        if source == "fail":
            raise RuntimeError("private transformer details")
        return source.upper()

    settings = Settings(database_url=url)
    app = create_app(settings, transformer=transform, transformer_version=version)
    # Keep the socket open from binding through startup, avoiding a free-port race.
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    host = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(15):
            while not server.started:
                if task.done():
                    await task
                    pytest.fail("Live test API stopped before startup")
                await asyncio.sleep(0.01)
        async with httpx.AsyncClient(base_url=host) as client:
            assert (await client.get("/health/ready")).status_code == 200
        yield host, calls, version, settings
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(task, timeout=10)
        finally:
            listener.close()
            engine = create_engine(settings)
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


async def invoke_cli(*args, stdin=None, command="cache-service"):
    executable = Path(sys.executable).parent / command
    assert executable.is_file(), "Install the project with uv sync before running CLI integration"
    # The client should work without API/database settings or credentials.
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("DB_") and key not in {"DATABASE_URL", "TEST_DATABASE_URL"}
    }
    process = await asyncio.create_subprocess_exec(
        str(executable),
        *args,
        env=environment,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(None if stdin is None else stdin.encode("utf-8")),
            timeout=20,
        )
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.communicate()
        raise
    return process.returncode, stdout.decode("utf-8"), stderr.decode("utf-8")


@pytest.mark.integration
async def test_assessment_sample_routes_fields_and_cli(live_cli_service, tmp_path):
    host, calls, _, _ = live_cli_service
    payload = {
        "list_1": ["first string", "second string", "third string"],
        "list_2": ["other string", "another string", "last string"],
    }
    expected = (
        "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
    )
    async with httpx.AsyncClient(base_url=host) as client:
        response = await client.post("/payload", json=payload)
        assert response.status_code == 200
        identifier = response.json()["id"]
        UUID(identifier)
        legacy = {"list1": payload["list_1"], "list2": payload["list_2"]}
        assert (await client.post("/payloads", json=legacy)).json() == {"id": identifier}
        for path in ("/payload", "/payloads"):
            response = await client.get(f"{path}/{identifier}")
            assert response.status_code == 200
            assert response.json() == {"output": expected}
        schema = (await client.get("/openapi.json")).json()
        assert "/payload" in schema["paths"]
        assert "/payload/{id}" in schema["paths"]
        assert "/payloads" not in schema["paths"]

    record = {"id": identifier, "output": expected}
    raw = json.dumps(payload)
    code, stdout, stderr = await invoke_cli(
        "--host", host, "-j", raw, "-r", "2", command="cache-cli"
    )
    assert (code, stderr) == (0, "")
    assert [json.loads(line) for line in stdout.splitlines()] == [record, record]

    input_file = tmp_path / "payload.json"
    input_file.write_text(raw, encoding="utf-8")
    output_file = tmp_path / "output.jsonl"
    code, stdout, stderr = await invoke_cli(
        "--host", host, "-i", str(input_file), "-o", str(output_file), command="cache-cli"
    )
    assert (code, stdout, stderr) == (0, "", "")
    assert json.loads(output_file.read_text(encoding="utf-8")) == record

    code, stdout, stderr = await invoke_cli(
        "--host", host, "-i", "-", "-o", "-", stdin=raw, command="cache-cli"
    )
    assert (code, stderr) == (0, "")
    assert json.loads(stdout) == record
    assert calls == [*payload["list_1"], *payload["list_2"]]


@pytest.mark.integration
async def test_installed_cli_input_output_modes_and_persisted_reuse(live_cli_service, tmp_path):
    host, calls, version, settings = live_cli_service
    payload = {"list1": ["hello\nß", "hello\nß"], "list2": ["世界", "世界"]}
    raw = json.dumps(payload, ensure_ascii=False)
    expected_output = "HELLO\nSS, 世界, HELLO\nSS, 世界"
    code, stdout, stderr = await invoke_cli("--host", host, "--json", raw, "--repeat", "2")
    assert code == 0
    assert stderr == ""
    records = [json.loads(line) for line in stdout.splitlines()]
    assert len(records) == 2
    UUID(records[0]["id"])
    assert records == [{"id": records[0]["id"], "output": expected_output}] * 2
    assert calls == ["hello\nß", "世界"]

    source = tmp_path / "input with spaces.json"
    source.write_text(raw, encoding="utf-8")
    output = tmp_path / "results.jsonl"
    code, stdout, stderr = await invoke_cli(
        "--host",
        host,
        "--input",
        str(source),
        "--output",
        str(output),
    )
    assert (code, stdout, stderr) == (0, "", "")
    assert json.loads(output.read_text(encoding="utf-8")) == records[0]
    code, stdout, stderr = await invoke_cli("--host", host, "--input", "-", stdin=raw)
    assert code == 0
    assert stderr == ""
    assert json.loads(stdout) == records[0]
    assert calls == ["hello\nß", "世界"]

    # Check actual committed storage independently of the HTTP and CLI responses.
    engine = create_engine(settings)
    try:
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM transformations WHERE version = :version"),
                    {"version": version},
                )
                == 2
            )
            assert (
                await connection.scalar(
                    text("SELECT output FROM payloads WHERE id = :id"),
                    {"id": UUID(records[0]["id"])},
                )
                == expected_output
            )
    finally:
        await engine.dispose()


@pytest.mark.integration
async def test_installed_cli_reports_live_server_failure(live_cli_service):
    host, calls, version, settings = live_cli_service
    code, stdout, stderr = await invoke_cli(
        "--host",
        host,
        "--json",
        '{"list1":["saved"],"list2":["fail"]}',
        "--repeat",
        "3",
    )
    assert code == 1
    assert stdout == ""
    assert stderr == "cache-service: Create request failed (HTTP 502)\n"
    assert calls == ["saved", "fail"]
    engine = create_engine(settings)
    try:
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM payloads WHERE canonical_input LIKE :version"),
                    {"version": f"%{version}%"},
                )
                == 0
            )
            assert (
                await connection.execute(
                    text("SELECT source FROM transformations WHERE version = :version"),
                    {"version": version},
                )
            ).scalars().all() == ["saved"]
    finally:
        await engine.dispose()
