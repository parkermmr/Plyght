# Connectors

A connector wraps one external service in the same small lifecycle:

```python
async with RedisConnector(url="redis://cache:6379/0") as redis:
    await redis.client.set("key", "value")

redis = RedisConnector()
await redis.connect()
assert await redis.healthy()
await redis.aclose()
```

| Member                                     | Meaning                                                                     |
|--------------------------------------------|-----------------------------------------------------------------------------|
| `Connector(settings=None, **overrides)`    | settings from the environment, overrides validated by the same rules        |
| `connect()` / `aclose()` / `async with`    | open and release; `aclose` is safe when never connected                      |
| `healthy() -> bool`                        | one cheap round trip; returns False and never raises                        |
| `.client`                                  | the underlying library object; raises `NotConnectedError` before `connect`  |
| `.connected`                               | whether `.client` is set                                                    |

Connectors import lazily from `plyght.connectors`. When a connector's
client library is missing, the import raises an `ImportError` that names
the extra to install.

## Kafka

`pip install "plyght[kafka]"` - variables `PLYGHT_KAFKA_*`.

```python
async with KafkaConnector() as kafka:
    await kafka.produce("events", {"user": "u1"}, key="u1")
    async with kafka.consumer("events", group="workers", from_beginning=True) as consumer:
        async for record in consumer:
            ...
```

- `produce` waits for the broker's ack (`acks`, default `all`). Dicts and
  lists are encoded as JSON, strings as utf-8, and bytes are sent as they
  are.
- `consumer` yields a started consumer group member and stops it on exit.
  Two consumers in the same group split the topic's partitions between
  them. Offsets commit automatically.

| Setting                                   | Default          |
|-------------------------------------------|------------------|
| `bootstrap`                               | `localhost:9092` |
| `client_id`                               | `plyght`         |
| `acks`                                    | `all`            |
| `security_protocol`                       | `PLAINTEXT`      |
| `sasl_mechanism`                          | `PLAIN` when SASL is on |
| `sasl_username`, `sasl_password`          | unset            |
| `ssl_cafile`, `ssl_certfile`, `ssl_keyfile`, `ssl_password` | unset |
| `ssl_check_hostname`                      | `true`           |

`SSL` and `SASL_SSL` build a verifying context from `ssl_cafile`, or from
system trust when it is unset. A certificate plus key gives mutual TLS.
The settings are refused when certificate files are set without TLS,
when a SASL mechanism is set without SASL, or when SASL is on without
credentials.

## Redis

`pip install "plyght[redis]"` - variables `PLYGHT_REDIS_*`.

The wrapper standardizes only the lifecycle. Use `.client`, which is
redis-py's async client, for commands.

| Setting                         | Default                    |
|---------------------------------|----------------------------|
| `url`                           | `redis://localhost:6379/0` |
| `ssl`                           | `false`                    |
| `ssl_ca`, `ssl_cert`, `ssl_key` | unset                      |
| `ssl_check_hostname`            | `true`                     |

`ssl=true` or a `rediss://` url turns on TLS and requires the server
certificate to verify. Passwords in the url are redacted in logs.

## Postgres

`pip install "plyght[postgres]"` - variables `PLYGHT_POSTGRES_*`.

```python
async with PostgresConnector() as pg:
    count = await pg.execute("update jobs set done = true where id = %s", (7,))
    rows = await pg.fetch("select * from jobs")      # list of dicts
```

The connection uses autocommit and returns rows as dicts. For
transactions or pooling, use `.client`, which is a psycopg
`AsyncConnection`.

| Setting                                | Default     |
|----------------------------------------|-------------|
| `host`, `port`                         | `localhost`, `5432` |
| `user`, `password`, `database`         | `postgres`  |
| `sslmode`                              | libpq's default |
| `sslrootcert`, `sslcert`, `sslkey`     | unset       |

`sslmode` follows libpq. `require` encrypts the connection, `verify-ca`
also checks the server against `sslrootcert`, and `verify-full` also
checks the hostname. `sslrootcert=system` uses system trust.

## S3

`pip install "plyght[s3]"` - variables `PLYGHT_S3_*`.

```python
async with S3Connector(endpoint="http://localhost:9000") as s3:
    await s3.ensure_bucket("artifacts")
    await s3.put("artifacts", "runs/1.json", b"{}")
    data = await s3.get("artifacts", "runs/1.json")
    objects = await s3.list("artifacts", prefix="runs/")   # every page
    await s3.delete("artifacts", "runs/1.json")
```

Leave `endpoint` unset for AWS, or set it for MinIO and other S3
compatible stores. `access_key`, `secret_key` and `region` (default
`us-east-1`) fall back to boto3's usual credential chain. boto3 is
synchronous, so each call runs in a worker thread.

## SQLite

Standard library, no extra - variables `PLYGHT_SQLITE_*`.

`path` defaults to `./sqlite.db`, and parent directories are created.
The connector has the same `execute` and `fetch` surface as postgres,
plus `executemany`. Statements autocommit and rows come back as dicts.

## Registry

Kinds are looked up by name, so a configuration file can name the
connector it wants:

```python
from plyght.connectors.registry import available, connector

Redis = connector("redis")
available()      # [{"kind", "target", "source", "extra", "loads", "reason"}, ...]
```

Other packages can add kinds through an entry point:

```toml
[project.entry-points."plyght.connectors"]
mongo = "acme_mongo.connector:MongoConnector"
```

A package can never replace a built-in kind. A package that fails to
load, or that names something other than a `Connector`, is reported by
`available()` and skipped. Nothing is imported until a kind is asked
for.

## Writing a connector

Subclass `Connector`, give it a nested `Settings`, and implement
`connect`, `aclose` and `healthy`:

```python
from plyght import Connector, ConnectorSettings, connector_config


class MongoSettings(ConnectorSettings):
    model_config = connector_config("mongo")
    url: str = "mongodb://localhost:27017"


class MongoConnector(Connector):
    Settings = MongoSettings

    async def connect(self) -> None:
        self._client = AsyncMongoClient(self.settings.url)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def healthy(self) -> bool:
        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            return False
```
