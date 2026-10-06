"""CLI argument contract; request execution and file I/O follow in B16."""

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


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
    execution entry point will turn these into stderr diagnostics and a nonzero exit.
    Input contents and file accessibility are checked by the later I/O layer.
    """
    return CliSettings(_cli_parse_args=True if args is None else args)
