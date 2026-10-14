"""
The one protocol every plyght connector implements.

A connector wraps one external service behind a tiny, uniform
lifecycle so calling code never learns four client libraries:

    async with KafkaConnector() as kafka:
        await kafka.produce("events", {"id": 1})

    redis = RedisConnector(url="redis://cache:6379")
    await redis.connect()
    assert await redis.healthy()
    await redis.aclose()

Configuration comes from the connector's Settings class (environment,
resources/.env, constructor overrides - see plyght.settings). The
underlying client library object stays reachable via .client for
anything the wrapper does not surface.
"""

import abc
from typing import Any, Self

from plyght.logging import get_logger
from plyght.settings import ConnectorSettings


class NotConnectedError(RuntimeError):
    """Raised when .client is read before connect()."""


class Connector(abc.ABC):
    """
    Uniform lifecycle around one external service. Subclasses define
    a nested Settings class and implement connect/aclose/healthy;
    everything else (context management, override merging, logging,
    guarded client access) comes for free.
    """

    class Settings(ConnectorSettings):
        pass

    def __init__(self, settings: ConnectorSettings | None = None, **overrides) -> None:
        base = settings or type(self).Settings()
        self.settings = base.merge(**overrides)
        self.log = get_logger(type(self).__name__)
        self._client: Any = None

    @property
    def client(self) -> Any:
        """
        The underlying library client, guarded: reading it before
        connect() is a bug worth failing loudly on.
        """
        if self._client is None:
            raise NotConnectedError(
                f"{type(self).__name__} is not connected: call connect() "
                "or use it as an async context manager"
            )
        return self._client

    @property
    def connected(self) -> bool:
        return self._client is not None

    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish the connection and set self._client."""

    @abc.abstractmethod
    async def aclose(self) -> None:
        """Release the connection; safe to call when not connected."""

    @abc.abstractmethod
    async def healthy(self) -> bool:
        """One cheap round trip to the service; False, never raise."""

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *_exc) -> None:
        await self.aclose()
