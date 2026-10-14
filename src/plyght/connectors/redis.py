"""
Redis behind the Connector protocol. The wrapper stays deliberately
thin: redis-py's async client is already good, so .client is the
canonical surface and only the lifecycle is standardized.

    async with RedisConnector() as redis:
        await redis.client.set("k", "v")
        assert await redis.client.get("k") == b"v"

TLS is off by default. ssl=true (or a rediss:// url) connects over
TLS, verifying the server against ssl_ca (system trust when unset),
with ssl_cert/ssl_key for mutual TLS and ssl_check_hostname to relax
hostname matching for certificates minted without the right name.
"""

from typing import Self
from urllib.parse import urlsplit, urlunsplit

from pydantic import model_validator
from redis.asyncio import Redis

from plyght.connector import Connector
from plyght.settings import ConnectorSettings, connector_config


def redact(url: str) -> str:
    """The url with any password replaced, safe to log."""
    parts = urlsplit(url)
    if parts.password is None:
        return url
    host = parts.netloc.rpartition("@")[2]
    user = parts.username or ""
    return urlunsplit(parts._replace(netloc=f"{user}:***@{host}"))


class RedisSettings(ConnectorSettings):
    """Server url and wire security settings; PLYGHT_REDIS_*."""

    model_config = connector_config("redis")

    url: str = "redis://localhost:6379/0"
    ssl: bool = False
    ssl_ca: str | None = None
    ssl_cert: str | None = None
    ssl_key: str | None = None
    ssl_check_hostname: bool = True

    @property
    def tls(self) -> bool:
        """Whether the connection is encrypted, by flag or by scheme."""
        return self.ssl or self.url.startswith("rediss://")

    @model_validator(mode="after")
    def check(self) -> Self:
        """Refuse certificate settings a plain connection would ignore."""
        if self.tls and not self.url.startswith(("redis://", "rediss://")):
            raise ValueError(
                f"{self.variable('ssl')} needs a redis:// or rediss:// "
                f"{self.variable('url')}"
            )
        if (self.ssl_ca or self.ssl_cert or self.ssl_key) and not self.tls:
            raise ValueError(
                f"{self.variable('ssl_ca')}/_CERT/_KEY are set but TLS is "
                f"off; set {self.variable('ssl')}=true or use rediss://"
            )
        if self.ssl_key and not self.ssl_cert:
            raise ValueError(
                f"{self.variable('ssl_key')} needs {self.variable('ssl_cert')}"
            )
        self.require_file("ssl_ca", "ssl_cert", "ssl_key")
        return self

    def address(self) -> str:
        """The url to dial: rediss:// whenever TLS is on."""
        if self.tls and self.url.startswith("redis://"):
            return "rediss://" + self.url.removeprefix("redis://")
        return self.url

    def options(self) -> dict:
        """Redis.from_url kwargs beyond the url; empty when TLS is off."""
        if not self.tls:
            return {}
        options: dict = {
            "ssl_cert_reqs": "required",
            "ssl_check_hostname": self.ssl_check_hostname,
        }
        if self.ssl_ca:
            options["ssl_ca_certs"] = self.ssl_ca
        if self.ssl_cert:
            options |= {"ssl_certfile": self.ssl_cert, "ssl_keyfile": self.ssl_key}
        return options


class RedisConnector(Connector):
    Settings = RedisSettings

    async def connect(self) -> None:
        self._client = Redis.from_url(
            self.settings.address(), **self.settings.options()
        )
        self.log.debug("connected", extra={"url": redact(self.settings.url)})

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def healthy(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception:
            return False
