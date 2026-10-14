"""
Connector catalog. Imports are lazy so plyght installs light and a
missing client library fails at first use with the exact extra to
install, not at import of anything else. SqliteConnector is standard
library and needs no extra.
"""

_CATALOG = {
    "KafkaConnector": ("plyght.connectors.kafka", "kafka"),
    "KafkaSettings": ("plyght.connectors.kafka", "kafka"),
    "RedisConnector": ("plyght.connectors.redis", "redis"),
    "RedisSettings": ("plyght.connectors.redis", "redis"),
    "PostgresConnector": ("plyght.connectors.postgres", "postgres"),
    "PostgresSettings": ("plyght.connectors.postgres", "postgres"),
    "S3Connector": ("plyght.connectors.s3", "s3"),
    "S3Settings": ("plyght.connectors.s3", "s3"),
    "SqliteConnector": ("plyght.connectors.sqlite", "sqlite"),
    "SqliteSettings": ("plyght.connectors.sqlite", "sqlite"),
}

__all__ = list(_CATALOG)


def __getattr__(name: str):
    """Resolve a connector on first touch, naming its extra on failure."""
    if name not in _CATALOG:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, extra = _CATALOG[name]
    from importlib import import_module

    try:
        module = import_module(module_name)
    except ImportError as error:
        raise ImportError(
            f"{name} needs its client library: pip install 'plyght[{extra}]'"
        ) from error
    return getattr(module, name)
