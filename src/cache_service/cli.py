"""CLI parsing, payload requests and incremental JSON Lines output."""

import json
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import TextIO

import httpx
from pydantic import AnyHttpUrl, Field, ValidationError, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    SettingsError,
)

from cache_service.schemas import PayloadCreate, PayloadCreated, PayloadOutput


class CliSettings(BaseSettings):
    """Create and read payloads, emitting one JSON Lines record per successful repeat."""

    model_config = SettingsConfigDict(
        cli_prog_name="cache-service",
        cli_exit_on_error=False,
        cli_avoid_json=True,
        hide_input_in_errors=True,
    )

    host: AnyHttpUrl = Field(
        default="http://127.0.0.1:8000", description="HTTP or HTTPS service base URL"
    )
    repeat: int = Field(default=1, gt=0, description="Number of create/read iterations")
    input_file: str | None = Field(
        default=None,
        alias="input",
        min_length=1,
        description="Input JSON file; use - for stdin (exclusive with --json)",
    )
    inline_json: str | None = Field(
        default=None,
        alias="json",
        min_length=1,
        description="Inline payload JSON (exclusive with --input)",
    )
    output_file: str = Field(
        default="-",
        alias="output",
        min_length=1,
        description="JSON Lines output file; use - for stdout",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # BaseSettings adds its CLI source separately. Shell variables and .env must
        # not silently supply an input source or change the destination of CLI output.
        return (init_settings,)

    @model_validator(mode="after")
    def require_one_input_source(self) -> "CliSettings":
        if (self.input_file is None) == (self.inline_json is None):
            raise ValueError("Provide exactly one of --input or --json")
        return self


def parse_cli_args(args: list[str] | None = None) -> CliSettings:
    """Parse explicit arguments, or sys.argv when omitted; help exits with status zero.

    Invalid flags raise SettingsError and invalid values raise ValidationError. The
    execution entry point turns these into stderr diagnostics and a nonzero exit.
    Input contents and file accessibility are checked by the I/O layer.
    """
    return CliSettings(_cli_parse_args=True if args is None else args)


class CliError(Exception):
    """A diagnostic safe to display without including input or credentials."""


def load_input(settings: CliSettings) -> PayloadCreate:
    """Read and validate once, before opening the output destination."""
    try:
        if settings.inline_json is not None:
            raw = settings.inline_json
        elif settings.input_file == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(settings.input_file).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CliError("Cannot read UTF-8 input") from exc
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise CliError("Input must be valid JSON") from exc
    try:
        return PayloadCreate.model_validate(data)
    except ValidationError as exc:
        raise CliError("Invalid payload; check list types, equal lengths and input limits") from exc


def execute_requests(
    settings: CliSettings,
    payload: PayloadCreate,
    client: httpx.Client,
    output: TextIO,
) -> None:
    """Emit a result only after both requests for that iteration succeed."""
    base = str(settings.host).rstrip("/")
    for _ in range(settings.repeat):
        response = client.post(f"{base}/payloads", json=payload.model_dump())
        if response.status_code != 200:
            raise CliError(f"Create request failed (HTTP {response.status_code})")
        try:
            created = PayloadCreated.model_validate_json(response.content, strict=True)
        except ValidationError as exc:
            raise CliError("Invalid create response") from exc
        response = client.get(f"{base}/payloads/{created.id}")
        if response.status_code != 200:
            raise CliError(f"Read request failed (HTTP {response.status_code})")
        try:
            result = PayloadOutput.model_validate_json(response.content, strict=True)
        except ValidationError as exc:
            raise CliError("Invalid read response") from exc
        record = json.dumps(
            {"id": str(created.id), "output": result.output},
            separators=(",", ":"),
        )
        output.write(record + "\n")
        output.flush()


def main(args: list[str] | None = None) -> int:
    """Return an exit status; help retains the parser's successful SystemExit."""
    try:
        try:
            settings = parse_cli_args(args)
        except (SettingsError, ValidationError) as exc:
            raise CliError("Invalid arguments; use --help for supported options") from exc
        payload = load_input(settings)
        # The read budget accommodates default generation (60s) plus cleanup (5s).
        timeout = httpx.Timeout(75.0, connect=5.0, write=10.0, pool=5.0)
        destination = (
            nullcontext(sys.stdout)
            if settings.output_file == "-"
            else open(settings.output_file, "w", encoding="utf-8")
        )
        with destination as output, httpx.Client(timeout=timeout) as client:
            execute_requests(settings, payload, client, output)
    except CliError as exc:
        print(f"cache-service: {exc}", file=sys.stderr)
        return 1
    except httpx.TimeoutException:
        print("cache-service: HTTP request timed out", file=sys.stderr)
        return 1
    except httpx.HTTPError:
        print("cache-service: HTTP request failed", file=sys.stderr)
        return 1
    except (OSError, UnicodeError):
        print("cache-service: Cannot write output", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("cache-service: Interrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
