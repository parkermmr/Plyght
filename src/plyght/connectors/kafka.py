"""
Kafka through one connector: a shared producer plus consumer factories.

    async with KafkaConnector() as kafka:
        await kafka.produce("events", {"user": "u1"}, key="u1")
        async with kafka.consumer("events", group="workers") as consumer:
            async for record in consumer:
                ...

Values that are dicts/lists encode as JSON, strings as utf-8, bytes
pass through. Consumers are real consumer-group members: two
consumers with the same group split the topic's partitions, which is
what makes flow replication scale instead of duplicate.

Security is off by default (PLAINTEXT). security_protocol SSL or
SASL_SSL builds a verifying ssl.SSLContext from ssl_cafile (system
trust when unset), with ssl_certfile/ssl_keyfile for mutual TLS;
SASL_PLAINTEXT or SASL_SSL adds sasl_mechanism with
sasl_username/sasl_password. Inconsistent combinations and dangling
certificate paths are refused when the settings are built.
"""

import json
from contextlib import asynccontextmanager
from ssl import SSLContext, create_default_context
from typing import Any, AsyncIterator, Literal, Self

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import Field, field_validator, model_validator

from plyght.connector import Connector
from plyght.settings import ConnectorSettings, connector_config


def encode(value: Any) -> bytes:
    if value is None or isinstance(value, bytes):
        return value or b""
    if isinstance(value, str):
        return value.encode()
    return json.dumps(value, default=str).encode()


Protocol = Literal["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"]
Mechanism = Literal["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"]


class KafkaSettings(ConnectorSettings):
    """Broker, producer and wire security settings; PLYGHT_KAFKA_*."""

    model_config = connector_config("kafka")

    bootstrap: str = "localhost:9092"
    client_id: str = "plyght"
    acks: str = "all"
    security_protocol: Protocol = "PLAINTEXT"
    sasl_mechanism: Mechanism | None = None
    sasl_username: str | None = None
    sasl_password: str | None = Field(default=None, repr=False)
    ssl_cafile: str | None = None
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None
    ssl_password: str | None = Field(default=None, repr=False)
    ssl_check_hostname: bool = True

    @field_validator("security_protocol", "sasl_mechanism", mode="before")
    @classmethod
    def normalize(cls, value: Any) -> Any:
        """Accept any case; an empty value means unset."""
        if isinstance(value, str):
            return value.strip().upper() or None
        return value

    @property
    def tls(self) -> bool:
        """Whether the protocol encrypts the wire."""
        return self.security_protocol in ("SSL", "SASL_SSL")

    @property
    def sasl(self) -> bool:
        """Whether the protocol authenticates with SASL."""
        return self.security_protocol.startswith("SASL_")

    @model_validator(mode="after")
    def check(self) -> Self:
        """Refuse security settings the protocol would silently ignore."""
        files = [self.ssl_cafile, self.ssl_certfile, self.ssl_keyfile]
        if any(files) and not self.tls:
            raise ValueError(
                f"{self.variable('ssl_cafile')}/_CERTFILE/_KEYFILE are set but "
                f"{self.variable('security_protocol')} is "
                f"{self.security_protocol}; use SSL or SASL_SSL"
            )
        if self.ssl_keyfile and not self.ssl_certfile:
            raise ValueError(
                f"{self.variable('ssl_keyfile')} needs "
                f"{self.variable('ssl_certfile')}"
            )
        self.require_file("ssl_cafile", "ssl_certfile", "ssl_keyfile")
        if self.sasl_mechanism and not self.sasl:
            raise ValueError(
                f"{self.variable('sasl_mechanism')} is set but "
                f"{self.variable('security_protocol')} is "
                f"{self.security_protocol}; use SASL_PLAINTEXT or SASL_SSL"
            )
        if self.sasl and not (self.sasl_username and self.sasl_password):
            raise ValueError(
                f"{self.variable('security_protocol')} {self.security_protocol} "
                f"needs {self.variable('sasl_username')} and "
                f"{self.variable('sasl_password')}"
            )
        return self

    def context(self) -> SSLContext:
        """
        A verifying client context: the configured CA (or system
        trust), the client certificate when one is set, and hostname
        checking unless explicitly turned off.
        """
        context = create_default_context(cafile=self.ssl_cafile)
        context.check_hostname = self.ssl_check_hostname
        if self.ssl_certfile:
            context.load_cert_chain(
                self.ssl_certfile, self.ssl_keyfile, self.ssl_password
            )
        return context

    def common(self) -> dict:
        """
        The connection kwargs every aiokafka producer and consumer
        built from these settings shares.
        """
        options: dict = {
            "bootstrap_servers": self.bootstrap,
            "client_id": self.client_id,
            "security_protocol": self.security_protocol,
        }
        if self.sasl:
            options |= {
                "sasl_mechanism": self.sasl_mechanism or "PLAIN",
                "sasl_plain_username": self.sasl_username,
                "sasl_plain_password": self.sasl_password,
            }
        if self.tls:
            options["ssl_context"] = self.context()
        return options


class KafkaConnector(Connector):
    Settings = KafkaSettings

    async def connect(self) -> None:
        acks = self.settings.acks
        producer = AIOKafkaProducer(
            acks=int(acks) if acks.lstrip("-").isdigit() else acks,
            **self.settings.common(),
        )
        try:
            await producer.start()
        except BaseException:
            await producer.stop()
            raise
        self._client = producer
        self.log.debug("connected", extra={"bootstrap": self.settings.bootstrap})

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.stop()
            self._client = None

    async def healthy(self) -> bool:
        try:
            await self.client.client.fetch_all_metadata()
            return True
        except Exception:
            return False

    async def produce(
        self, topic: str, value: Any, key: str | bytes | None = None
    ) -> None:
        """Send one record and wait for the broker's ack."""
        encoded_key = key.encode() if isinstance(key, str) else key
        await self.client.send_and_wait(topic, encode(value), key=encoded_key)

    @asynccontextmanager
    async def consumer(
        self,
        *topics: str,
        group: str = "plyght",
        from_beginning: bool = False,
    ) -> AsyncIterator[AIOKafkaConsumer]:
        """
        A started consumer-group member, stopped on exit. Iterate it
        for records; records commit automatically.
        """
        consumer = AIOKafkaConsumer(
            *topics,
            group_id=group,
            auto_offset_reset="earliest" if from_beginning else "latest",
            **self.settings.common(),
        )
        await consumer.start()
        try:
            yield consumer
        finally:
            await consumer.stop()
