from functools import lru_cache
from pathlib import Path

from dynaconf import Dynaconf  # type: ignore[import-untyped]
from pydantic import (
    BaseModel,
    model_validator,
)
from pydantic_settings import BaseSettings

__all__ = (
    "ROOT_DIR",
    "App",
    "Settings",
    "load_settings",
    "settings",
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class App(BaseModel):
    """Application configuration."""

    title: str
    version: str
    root_path: str
    port: int
    host: str
    opentelemetry_available: bool
    otel_endpoint: str
    otel_service_name: str

    @staticmethod
    def __parse_version_from_pyproject_toml() -> str:
        """Parse version from pyproject.toml file."""
        try:
            with open("pyproject.toml") as f:
                for line in f:
                    if line.startswith("version ="):
                        return line.split("=")[1].strip().strip('"')
        except FileNotFoundError:
            return "0.0.0"

        return "0.0.0"

    @model_validator(mode="after")
    def set_version_from_pyproject(self) -> "App":
        """Post-initialization to set default values."""
        temp = self.version
        parsed_version = self.__parse_version_from_pyproject_toml()

        if parsed_version != "0.0.0":
            self.version = parsed_version
        elif self.version == "0.0.0":
            self.version = temp

        return self


class Settings(BaseSettings):
    """Main configuration class."""

    app: App

    # skip extra validation for Dynaconf compatibility
    model_config = {
        "extra": "allow",  # Allow extra fields for Dynaconf compatibility
    }


@lru_cache(maxsize=1)
def load_settings(settings_dir: str | Path | None = None) -> Settings:
    """Load configuration from YAML files using Dynaconf.

    Args:
        settings_dir: Directory containing settings.yml and secrets.yml files.
            Default is the project root directory.

    Returns:
        Settings: Config Pydantic model instance with all settings.
    """
    if settings_dir is None:
        settings_dir = ROOT_DIR

    settings_path = (
        Path(settings_dir) if isinstance(settings_dir, str) else settings_dir
    )

    secrets_file = settings_path / ".secrets.yml"

    # Check if secrets file exists
    if not secrets_file.exists():
        raise FileNotFoundError(f"Settings file not found: {secrets_file}")

    # Prepare list of configuration files
    config_files = [str(secrets_file)]

    # Load configuration using Dynaconf
    dynaconf_settings = Dynaconf(
        settings_files=config_files,
        envvar_prefix="MCP_",
        load_dotenv=True,
        merge_enabled=True,
    )

    # Convert Dynaconf settings to a regular dictionary
    config_data = {k.lower(): v for k, v in dynaconf_settings.to_dict().items()}

    # Create Settings instance directly from config data
    return Settings.model_validate(config_data)


settings = load_settings()
