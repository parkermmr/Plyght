"""
plyght: typed connectors, settings, logging, and a fastapi service spine.

Connectors (each needs its extra: plyght[kafka], plyght[redis], ...):

    from plyght.connectors import KafkaConnector, RedisConnector
    from plyght.connectors import PostgresConnector, S3Connector

Services build on plyght.web (plyght[web]).
"""

from plyght.connector import Connector, NotConnectedError
from plyght.logging import configure, get_logger
from plyght.settings import ConnectorSettings, connector_config

__all__ = [
    "Connector",
    "ConnectorSettings",
    "NotConnectedError",
    "configure",
    "connector_config",
    "get_logger",
]
