"""
The connector registry: built-ins by kind, packaged connectors through
the plyght.connectors entry point group, a built-in never replaced, a
broken package skipped with a reason rather than breaking the list.
"""

from importlib.metadata import EntryPoint

import pytest

from plyght.connector import Connector
from plyght.connectors import registry


class Mongo(Connector):
    async def connect(self):
        return self

    async def aclose(self):
        return None

    async def healthy(self) -> bool:
        return True


NotAConnector = object


@pytest.fixture
def packaged(monkeypatch):
    points = [
        EntryPoint("mongo", f"{__name__}:Mongo", registry.GROUP),
        EntryPoint("kafka", f"{__name__}:Mongo", registry.GROUP),
        EntryPoint("broken", "nowhere.at_all:Thing", registry.GROUP),
        EntryPoint("odd", f"{__name__}:NotAConnector", registry.GROUP),
    ]
    monkeypatch.setattr(registry, "entry_points", lambda group: points)


def test_built_ins_are_listed_without_importing_them():
    found = registry.entries()
    assert set(found) >= {"kafka", "redis", "postgres", "s3", "sqlite"}
    assert found["kafka"].source == "builtin"


def test_sqlite_loads_from_the_standard_library():
    assert registry.connector("sqlite").__name__ == "SqliteConnector"


def test_a_package_adds_a_kind_but_never_replaces_one(packaged):
    assert registry.connector("mongo") is Mongo
    assert registry.entries()["kafka"].source == "builtin"


def test_what_does_not_load_says_why(packaged):
    listed = {entry["kind"]: entry for entry in registry.available()}
    assert listed["mongo"]["loads"] is True
    assert listed["broken"]["loads"] is False and "nowhere.at_all" in listed["broken"]["reason"]
    assert "not a Connector" in listed["odd"]["reason"]
    with pytest.raises(LookupError):
        registry.connector("absent")
