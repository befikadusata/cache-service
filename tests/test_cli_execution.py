import io
import json
from functools import partial

import httpx
import pytest

from cache_service.cli import main

IDENTIFIER = "550e8400-e29b-41d4-a716-446655440000"
PAYLOAD = '{"list1":["hello"],"list2":["world"]}'


@pytest.fixture
def mock_http(monkeypatch):
    original = httpx.Client

    def install(handler):
        monkeypatch.setattr(
            httpx, "Client", partial(original, transport=httpx.MockTransport(handler))
        )

    return install


def success(request):
    if request.method == "POST":
        assert json.loads(request.content) == json.loads(PAYLOAD)
        return httpx.Response(200, json={"id": IDENTIFIER})
    return httpx.Response(200, json={"output": "HELLO, WORLD\nß"})


def test_repeats_preserve_host_prefix_and_flush_records(mock_http, monkeypatch, capsys):
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if len(calls) == 3:
            assert len(capsys.readouterr().out.splitlines()) == 1
        return success(request)

    mock_http(handler)
    assert main(["--json", PAYLOAD, "--host", "https://example.com/api/", "--repeat", "2"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {"id": IDENTIFIER, "output": "HELLO, WORLD\nß"}
    assert calls == [("POST", "/api/payloads"), ("GET", f"/api/payloads/{IDENTIFIER}")] * 2


@pytest.mark.parametrize("source", ["file", "stdin", "inline"])
def test_input_sources_and_file_output(source, tmp_path, monkeypatch, mock_http, capsys):
    mock_http(success)
    input_path = tmp_path / "input.json"
    input_path.write_text(PAYLOAD, encoding="utf-8")
    output_path = tmp_path / "output.jsonl"
    output_path.write_text("old contents", encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(PAYLOAD))
    args = {
        "file": ["--input", str(input_path)],
        "stdin": ["--input", "-"],
        "inline": ["--json", PAYLOAD],
    }[source]
    assert main([*args, "--output", str(output_path), "--repeat", "2"]) == 0
    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all(
        json.loads(line) == {"id": IDENTIFIER, "output": "HELLO, WORLD\nß"} for line in lines
    )
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "raw", ["not JSON", "{}", '{"list1":[1],"list2":[2]}', '{"list1":[],"list2":["x"]}']
)
def test_invalid_input_preserves_existing_destination(raw, tmp_path, capsys):
    output_path = tmp_path / "output.jsonl"
    output_path.write_text("preserved", encoding="utf-8")
    assert main(["--json", raw, "--output", str(output_path)]) == 1
    assert output_path.read_text() == "preserved"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "cache-service:" in captured.err
    assert raw not in captured.err


@pytest.mark.parametrize(
    "args", [[], ["--unknown", "secret"], ["--json", PAYLOAD, "--repeat", "0"]]
)
def test_argument_failures(args, capsys):
    assert main(args) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Invalid arguments" in captured.err
    assert "secret" not in captured.err


@pytest.mark.parametrize("stage", ["create", "read"])
@pytest.mark.parametrize("failure", ["status", "malformed", "schema"])
def test_response_failures_keep_earlier_records(stage, failure, mock_http, capsys):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        target = 3 if stage == "create" else 4
        if calls == target:
            if failure == "status":
                return httpx.Response(503, json={"detail": "secret input"})
            if failure == "malformed":
                return httpx.Response(200, text="secret input")
            return httpx.Response(200, json={"id": "bad", "output": 123})
        return success(request)

    mock_http(handler)
    assert main(["--json", PAYLOAD, "--repeat", "3"]) == 1
    captured = capsys.readouterr()
    assert len(captured.out.splitlines()) == 1
    assert json.loads(captured.out)["id"] == IDENTIFIER
    assert calls == (3 if stage == "create" else 4)
    assert "secret input" not in captured.err


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadTimeout])
def test_network_failures_are_safe(error, mock_http, capsys):
    def handler(request):
        raise error("secret credentials", request=request)

    mock_http(handler)
    assert main(["--json", PAYLOAD]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "secret credentials" not in captured.err
    assert "HTTP request" in captured.err


def test_file_read_and_write_failures(tmp_path, capsys):
    assert main(["--input", str(tmp_path / "missing")]) == 1
    assert "Cannot read" in capsys.readouterr().err
    assert main(["--json", PAYLOAD, "--output", str(tmp_path)]) == 1
    assert "Cannot write" in capsys.readouterr().err


def test_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["--help"])
    assert caught.value.code == 0
    assert capsys.readouterr().err == ""


def test_empty_payload_and_output(mock_http, capsys):
    def handler(request):
        if request.method == "POST":
            assert json.loads(request.content) == {"list1": [], "list2": []}
            return httpx.Response(200, json={"id": IDENTIFIER})
        return httpx.Response(200, json={"output": ""})

    mock_http(handler)
    assert main(["--json", '{"list1":[],"list2":[]}']) == 0
    assert json.loads(capsys.readouterr().out) == {"id": IDENTIFIER, "output": ""}


def test_same_input_output_path(tmp_path, mock_http):
    mock_http(success)
    path = tmp_path / "payload.json"
    path.write_text(PAYLOAD, encoding="utf-8")
    assert main(["--input", str(path), "--output", str(path)]) == 0
    assert json.loads(path.read_text())["id"] == IDENTIFIER


def test_invalid_utf8_input(tmp_path, capsys):
    path = tmp_path / "payload.json"
    path.write_bytes(b"\xff")
    assert main(["--input", str(path)]) == 1
    assert "Cannot read UTF-8 input" in capsys.readouterr().err


def test_output_flush_failure_stops_requests(monkeypatch, mock_http, capsys):
    class FailingOutput(io.StringIO):
        def flush(self):
            raise OSError("secret path")

    calls = []

    def handler(request):
        calls.append(request.method)
        return success(request)

    mock_http(handler)
    monkeypatch.setattr("sys.stdout", FailingOutput())
    assert main(["--json", PAYLOAD, "--repeat", "2"]) == 1
    assert calls == ["POST", "GET"]
    assert "Cannot write output" in capsys.readouterr().err
