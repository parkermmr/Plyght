"""
Connector configuration, pydantic-settings style.

Every connector owns a nested Settings class whose fields map to
PLYGHT_<CONNECTOR>_-prefixed environment variables, with defaults read
from a resources/.env file (PROFILE=dev overlays resources/.env.dev).
Real environment variables override both, constructor overrides beat
everything:

    KafkaConnector()                                # env / .env / defaults
    KafkaConnector(bootstrap="broker:9092")         # explicit wins
"""

import os
from pathlib import Path
from typing import Self

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class SecretFileSource(PydanticBaseSettingsSource):
    """
    A settings source honoring <PREFIX><FIELD>_FILE environment
    variables: the named file's stripped content becomes the field
    value. Mounted secrets (docker secrets, kubernetes volumes) beat
    plain environment variables this way, and a pointer at a missing
    file is an operator error that fails the boot loudly rather than
    silently falling back to whatever the environment holds.
    """

    def pointer(self, field_name: str) -> str:
        prefix = self.settings_cls.model_config.get("env_prefix", "")
        return f"{prefix}{field_name}_FILE".upper()

    def get_field_value(self, field, field_name: str):
        location = os.environ.get(self.pointer(field_name), "")
        if not location:
            return None, field_name, False
        path = Path(location)
        if not path.is_file():
            raise RuntimeError(
                f"{self.pointer(field_name)} points at {location!r}, "
                f"which is not a readable file"
            )
        return path.read_text(encoding="utf-8").strip(), field_name, False

    def __call__(self) -> dict:
        values = {}
        for field_name, field in self.settings_cls.model_fields.items():
            value, key, _ = self.get_field_value(field, field_name)
            if value is not None:
                values[key] = value
        return values


def env_files() -> tuple[str, ...]:
    """
    The dotenv files settings read: .env in the first resources
    directory found (the source checkout, /platform/resources, then the
    working directory), plus .env.<PROFILE> when PROFILE is set. Later
    files take priority.
    """
    for candidate in [
        Path(__file__).resolve().parents[2] / "resources",
        Path("/platform/resources"),
        Path.cwd() / "resources",
    ]:
        if candidate.is_dir():
            base = candidate
            break
    else:
        return ()
    files = [base / ".env"]
    profile = os.environ.get("PROFILE", "").strip()
    if profile:
        files.append(base / f".env.{profile}")
    return tuple(str(path) for path in files)


def connector_config(name: str) -> SettingsConfigDict:
    """
    The model_config for a connector's Settings class:
    connector_config("kafka") maps fields to PLYGHT_KAFKA_* variables.
    """
    return SettingsConfigDict(
        env_prefix=f"PLYGHT_{name.upper()}_",
        env_file=env_files(),
        extra="ignore",
    )


class ConnectorSettings(BaseSettings):
    """
    Base for connector settings; subclasses set
    model_config = connector_config("<name>"). Every field can arrive
    from a mounted file via <PREFIX><FIELD>_FILE (SecretFileSource);
    explicit constructor values still beat everything.
    """

    model_config = SettingsConfigDict(env_prefix="PLYGHT_", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            SecretFileSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    def merge(self, **overrides) -> Self:
        """
        A copy with overrides applied and validated again, so a
        constructor override is held to the same rules as the
        environment.
        """
        if not overrides:
            return self
        return type(self).model_validate(self.model_dump() | overrides)

    def variable(self, field: str) -> str:
        """The environment variable a field reads, for error messages."""
        prefix = self.model_config.get("env_prefix", "")
        return f"{prefix}{field}".upper()

    def require_file(self, *fields: str) -> None:
        """
        Refuse a set path field that names no readable file, naming
        the variable so the operator knows what to fix.
        """
        for field in fields:
            location = getattr(self, field)
            if location and not Path(location).is_file():
                raise ValueError(
                    f"{self.variable(field)} is {location!r}, "
                    "which is not a readable file"
                )
