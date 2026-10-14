"""
Connectors without servers: settings refuse inconsistent security,
clients are guarded until connect, sqlite round trips for real, and
the lazy catalog names the extra a missing library needs.
"""

import asyncio

import pytest
from pydantic import ValidationError

from plyght import NotConnectedError
from plyght.connectors import (
    KafkaSettings,
    PostgresSettings,
    RedisConnector,
    RedisSettings,
    SqliteConnector,
)
from plyght.connectors.kafka import encode
from plyght.connectors.redis import redact


def test_kafka_plaintext_by_default():
    options = KafkaSettings().common()
    assert options["security_protocol"] == "PLAINTEXT"
    assert "ssl_context" not in options and "sasl_mechanism" not in options


def test_kafka_sasl_needs_credentials():
    with pytest.raises(ValidationError, match="PLYGHT_KAFKA_SASL_USERNAME"):
        KafkaSettings(security_protocol="sasl_plaintext")
    settings = KafkaSettings(
        security_protocol="SASL_PLAINTEXT", sasl_username="u", sasl_password="p"
    )
    assert settings.common()["sasl_mechanism"] == "PLAIN"


def test_kafka_refuses_certificates_without_tls(tmp_path):
    authority = tmp_path / "ca.pem"
    authority.write_text("")
    with pytest.raises(ValidationError, match="use SSL or SASL_SSL"):
        KafkaSettings(ssl_cafile=str(authority))


def test_kafka_encodes_values():
    assert encode(None) == b""
    assert encode(b"raw") == b"raw"
    assert encode("text") == b"text"
    assert encode({"a": 1}) == b'{"a": 1}'


def test_redis_tls_upgrades_scheme():
    settings = RedisSettings(url="redis://cache:6379/0", ssl=True)
    assert settings.address() == "rediss://cache:6379/0"
    assert settings.options()["ssl_cert_reqs"] == "required"
    assert RedisSettings().options() == {}


def test_redis_redacts_passwords():
    assert redact("redis://user:secret@cache:6379") == "redis://user:***@cache:6379"
    assert redact("redis://cache:6379") == "redis://cache:6379"


def test_postgres_conninfo_quotes_values():
    settings = PostgresSettings(password="it's a secret", sslmode="REQUIRE")
    info = settings.conninfo()
    assert "password='it\\'s a secret'" in info
    assert "sslmode=require" in info
    assert "sslrootcert" not in info


def test_postgres_refuses_certificates_without_sslmode(tmp_path):
    with pytest.raises(ValidationError, match="use require, verify-ca or verify-full"):
        PostgresSettings(sslrootcert="system")


def test_client_is_guarded_until_connect():
    connector = RedisConnector()
    assert not connector.connected
    with pytest.raises(NotConnectedError):
        connector.client


def test_sqlite_round_trip(tmp_path):
    async def run():
        async with SqliteConnector(path=str(tmp_path / "nested" / "app.db")) as db:
            assert await db.healthy()
            await db.execute("create table events (id text, size int)")
            await db.executemany("insert into events values (?, ?)", [("a", 1), ("b", 2)])
            return await db.fetch("select * from events order by id")

    assert asyncio.run(run()) == [{"id": "a", "size": 1}, {"id": "b", "size": 2}]


def test_unknown_catalog_name():
    import plyght.connectors

    with pytest.raises(AttributeError):
        plyght.connectors.MongoConnector
