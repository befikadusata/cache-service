import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError

from cache_service.cli import parse_cli_args


def test_inline_input_defaults():
    raw = '{"list1":[],"list2":[]}'
    settings = parse_cli_args(["--json", raw])
    assert settings.inline_json == raw
    assert settings.input_file is None
    assert str(settings.host) == "http://127.0.0.1:8000/"
    assert settings.repeat == 1
    assert settings.output_file == "-"


@pytest.mark.parametrize("source", ["payload.json", "-", "folder with spaces/input.json"])
def test_file_source_and_explicit_options(source):
    settings = parse_cli_args(
        [
            "--host",
            "https://example.com:8443/api/",
            "--repeat",
            "3",
            "--input",
            source,
            "--output",
            "results.jsonl",
        ]
    )
    assert str(settings.host) == "https://example.com:8443/api/"
    assert settings.repeat == 3
    assert settings.input_file == source
    assert settings.inline_json is None
    assert settings.output_file == "results.jsonl"


@pytest.mark.parametrize("args", [[], ["--input", "-", "--json", "{}"]])
def test_exactly_one_input_source(args):
    with pytest.raises(ValidationError, match="exactly one"):
        parse_cli_args(args)


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "many"])
def test_invalid_repeat(value):
    with pytest.raises(ValidationError):
        parse_cli_args(["--json", "{}", "--repeat", value])


@pytest.mark.parametrize("value", ["localhost:8000", "ftp://example.com", ""])
def test_invalid_host(value):
    with pytest.raises(ValidationError):
        parse_cli_args(["--json", "{}", "--host", value])


@pytest.mark.parametrize("flag", ["--input", "--json", "--output"])
def test_empty_source_or_destination(flag):
    args = [flag, ""] if flag != "--output" else ["--json", "{}", flag, ""]
    with pytest.raises(ValidationError):
        parse_cli_args(args)


@pytest.mark.parametrize("args", [["--unknown"], ["--input"], ["--host"]])
def test_invalid_flags(args):
    with pytest.raises(SettingsError):
        parse_cli_args(args)


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_exits_successfully_without_input(flag, capsys):
    with pytest.raises(SystemExit) as caught:
        parse_cli_args([flag])
    assert caught.value.code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    for option in ("--host", "--repeat", "--input", "--json", "--output", "-h, --help"):
        assert option in captured.out


def test_uses_process_arguments_when_omitted(monkeypatch):
    monkeypatch.setattr("sys.argv", ["cache-service", "--input", "-"])
    assert parse_cli_args().input_file == "-"


def test_environment_and_dotenv_do_not_supply_cli_values(monkeypatch, tmp_path):
    for name, value in {
        "HOST": "https://unexpected.example",
        "REPEAT": "9",
        "INPUT": "hidden.json",
        "OUTPUT": "hidden.jsonl",
    }.items():
        monkeypatch.setenv(name, value)
    (tmp_path / ".env").write_text('JSON="{}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError, match="exactly one"):
        parse_cli_args([])
    settings = parse_cli_args(["--json", "{}"])
    assert str(settings.host) == "http://127.0.0.1:8000/"
    assert settings.repeat == 1
    assert settings.output_file == "-"


def test_parsing_does_not_read_files_or_validate_payload_contents():
    assert parse_cli_args(["--input", "missing.json"]).input_file == "missing.json"
    assert parse_cli_args(["--json", "malformed JSON"]).inline_json == "malformed JSON"
