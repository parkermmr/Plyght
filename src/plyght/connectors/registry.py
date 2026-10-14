"""
The connector registry: every connector this environment can build,
by kind, whether plyght ships it or a package installed it.

A package adds connectors under the `plyght.connectors` entry point
group, one entry per kind:

    [project.entry-points."plyght.connectors"]
    mongo = "acme_mongo.connector:MongoConnector"

That is the same install story as adapters and secret providers: put
the package on the path (the image, an instance's packages, or a
group's extensions) and the kind exists. A package naming a kind
plyght ships is ignored, so installing something never swaps a
built-in out from under a flow; one that fails to load is logged by
name and skipped. Nothing is imported until asked for, so listing the
registry never pulls in a client library.
"""

import logging
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import entry_points

from plyght.connector import Connector

GROUP = "plyght.connectors"

BUILTIN = {
    "kafka": ("plyght.connectors.kafka", "KafkaConnector", "kafka"),
    "redis": ("plyght.connectors.redis", "RedisConnector", "redis"),
    "postgres": ("plyght.connectors.postgres", "PostgresConnector", "postgres"),
    "s3": ("plyght.connectors.s3", "S3Connector", "s3"),
    "sqlite": ("plyght.connectors.sqlite", "SqliteConnector", ""),
}

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Entry:
    """One connector kind and where it comes from."""

    kind: str
    target: str
    source: str
    extra: str = ""

    def describe(self) -> dict:
        """The listing form."""
        return {"kind": self.kind, "target": self.target, "source": self.source,
                "extra": self.extra}


def entries() -> dict[str, Entry]:
    """Every kind, built-ins first and never replaced, then packages."""
    found = {
        kind: Entry(kind, f"{module}:{name}", "builtin", extra)
        for kind, (module, name, extra) in BUILTIN.items()
    }
    for point in sorted(entry_points(group=GROUP), key=lambda entry: entry.name):
        if point.name in found:
            if found[point.name].source == "builtin":
                log.warning("connector package %s names built-in kind %r; ignored",
                            point.value, point.name)
            continue
        found[point.name] = Entry(point.name, point.value, "package")
    return found


def connector(kind: str) -> type[Connector]:
    """
    The connector class for a kind, imported on first use. Raises
    LookupError for an unknown kind and ImportError, naming the extra
    to install, when its client library is missing.
    """
    entry = entries().get(kind)
    if entry is None:
        raise LookupError(f"no connector of kind {kind!r}")
    module, _, name = entry.target.partition(":")
    try:
        loaded = getattr(import_module(module), name)
    except ImportError as error:
        hint = f"pip install 'plyght[{entry.extra}]'" if entry.extra else f"install {module}"
        raise ImportError(f"connector {kind!r} needs its library: {hint}") from error
    except AttributeError as error:
        raise ImportError(f"connector {kind!r} names {entry.target}, which is missing") from error
    if not (isinstance(loaded, type) and issubclass(loaded, Connector)):
        raise ImportError(f"connector {kind!r} names {entry.target}, which is not a Connector")
    return loaded


def available() -> list[dict]:
    """Every kind with whether it loads here, for a listing."""
    listed = []
    for kind, entry in sorted(entries().items()):
        try:
            connector(kind)
            reason = ""
        except (ImportError, LookupError) as error:
            reason = str(error)
        listed.append({**entry.describe(), "loads": not reason, "reason": reason})
    return listed
