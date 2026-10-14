"""
Connector settings: prefixed environment variables, constructor
overrides validated like the environment, mounted secret files, and
the dotenv files a PROFILE overlays.
"""

import pytest
from pydantic import ValidationError

from plyght import ConnectorSettings, connector_config
from plyght.settings import env_files


class DemoSettings(ConnectorSettings):
    model_config = connector_config("demo")

    host: str = "localhost"
    port: int = 1


def test_defaults_and_prefix(monkeypatch):
    monkeypatch.setenv("PLYGHT_DEMO_HOST", "remote")
    settings = DemoSettings()
    assert (settings.host, settings.port) == ("remote", 1)
    assert settings.variable("port") == "PLYGHT_DEMO_PORT"


def test_merge_validates_overrides():
    settings = DemoSettings()
    assert settings.merge() is settings
    assert settings.merge(port="9").port == 9
    with pytest.raises(ValidationError):
        settings.merge(port="nine")


def test_secret_file_beats_environment(tmp_path, monkeypatch):
    secret = tmp_path / "host"
    secret.write_text("from-file\n")
    monkeypatch.setenv("PLYGHT_DEMO_HOST", "from-env")
    monkeypatch.setenv("PLYGHT_DEMO_HOST_FILE", str(secret))
    assert DemoSettings().host == "from-file"
    assert DemoSettings(host="explicit").host == "explicit"


def test_missing_secret_file_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.setenv("PLYGHT_DEMO_HOST_FILE", str(tmp_path / "absent"))
    with pytest.raises(RuntimeError, match="PLYGHT_DEMO_HOST_FILE"):
        DemoSettings()


def test_require_file_names_the_variable(tmp_path):
    class Paths(DemoSettings):
        certificate: str | None = None

    Paths(certificate=None).require_file("certificate")
    with pytest.raises(ValueError, match="PLYGHT_DEMO_CERTIFICATE"):
        Paths(certificate=str(tmp_path / "absent")).require_file("certificate")


def test_env_files_overlay_profile(tmp_path, monkeypatch):
    (tmp_path / "resources").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PROFILE", raising=False)
    assert env_files()[-1].endswith("resources/.env")
    monkeypatch.setenv("PROFILE", "dev")
    assert env_files()[-2:][0].endswith("resources/.env")
    assert env_files()[-1].endswith("resources/.env.dev")
