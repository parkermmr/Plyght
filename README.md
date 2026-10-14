[![CI Status][ci-shield]][ci-url]
[![Coverage][coverage-shield]][coverage-url]
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

# Plyght

Typed connectors, settings, logging and a FastAPI service spine. Kafka,
redis, postgres, s3 and sqlite all sit behind one small `Connector`
lifecycle, each configured from the environment. `plyght.web` builds a
FastAPI app that already has its middleware, docs and health probes
wired.

Full documentation: [plyght.teampixl.info](https://plyght.teampixl.info)

```
pip install plyght                 # settings, logging, sqlite, standard library utilities
pip install "plyght[kafka]"        # + KafkaConnector (aiokafka)
pip install "plyght[redis]"        # + RedisConnector (redis)
pip install "plyght[postgres]"     # + PostgresConnector (psycopg)
pip install "plyght[s3]"           # + S3Connector (boto3)
pip install "plyght[web]"          # + plyght.web (fastapi, uvicorn)
pip install "plyght[all]"
```

## Connectors

```python
from plyght.connectors import KafkaConnector, PostgresConnector

async with KafkaConnector(bootstrap="broker:9092") as kafka:
    await kafka.produce("events", {"id": 1}, key="u1")
    async with kafka.consumer("events", group="workers") as consumer:
        async for record in consumer:
            ...

async with PostgresConnector() as pg:
    await pg.execute("insert into events (id) values (%s)", (1,))
    rows = await pg.fetch("select * from events")
```

| Connector           | Extra        | Variables          | Surface                                                     |
|---------------------|--------------|--------------------|-------------------------------------------------------------|
| `KafkaConnector`    | `[kafka]`    | `PLYGHT_KAFKA_*`   | `produce(topic, value, key)`, `consumer(*topics, group)`     |
| `RedisConnector`    | `[redis]`    | `PLYGHT_REDIS_*`   | `.client` (redis-py async)                                   |
| `PostgresConnector` | `[postgres]` | `PLYGHT_POSTGRES_*`| `execute(query, params)`, `fetch(query, params)`             |
| `S3Connector`       | `[s3]`       | `PLYGHT_S3_*`      | `ensure_bucket`, `put`, `get`, `list`, `delete`              |
| `SqliteConnector`   | none         | `PLYGHT_SQLITE_*`  | `execute`, `executemany`, `fetch`                            |

Every connector has the same lifecycle:

- `connect()` / `aclose()`, or `async with`.
- `healthy() -> bool` - one cheap round trip; never raises.
- `.client` - the underlying library object, for anything the wrapper
  does not surface. Reading it before `connect()` raises
  `NotConnectedError`.
- `Connector(settings=None, **overrides)` - keyword overrides are
  validated by the same rules as the environment.

Importing a connector whose client library is missing raises an
`ImportError` that names the extra to install.

### Security

TLS and authentication are off by default and opt in through settings.
Settings that the chosen mode would silently ignore, such as a CA file
with plaintext Kafka or a client key without a certificate, are refused
when the settings are built. Certificate paths must name readable files.

| Connector | Settings                                                                                     |
|-----------|----------------------------------------------------------------------------------------------|
| Kafka     | `security_protocol` (`PLAINTEXT`, `SSL`, `SASL_PLAINTEXT`, `SASL_SSL`), `ssl_cafile`, `ssl_certfile`, `ssl_keyfile`, `sasl_mechanism`, `sasl_username`, `sasl_password` |
| Redis     | `ssl` or a `rediss://` url, `ssl_ca`, `ssl_cert`, `ssl_key`, `ssl_check_hostname`             |
| Postgres  | `sslmode` (`disable`, `require`, `verify-ca`, `verify-full`), `sslrootcert`, `sslcert`, `sslkey` |

### Registry

Connectors are looked up by kind. Other packages can add kinds through
the `plyght.connectors` entry point group. A package can never replace a
built-in kind, and a package that fails to load is logged and skipped.

```toml
[project.entry-points."plyght.connectors"]
mongo = "acme_mongo.connector:MongoConnector"
```

```python
from plyght.connectors.registry import available, connector

connector("redis")      # the class, imported on first use
available()             # every kind, whether it loads here, and why not
```

## Settings

Each connector's settings class is a pydantic-settings model. Values are
resolved in this order, highest first:

1. Keyword arguments.
2. `<VARIABLE>_FILE` naming a file, for mounted secrets. The file's
   stripped content is used, and a pointer at a missing file fails at
   startup.
3. Environment variables (`PLYGHT_KAFKA_BOOTSTRAP`, ...).
4. Dotenv files: `resources/.env`, then `resources/.env.<PROFILE>` when
   `PROFILE` is set. `resources` is the first of `./resources` in the
   source checkout, `/platform/resources`, or the working directory.
5. Field defaults.

Your own connector settings use the same rules:

```python
from plyght import ConnectorSettings, connector_config

class MongoSettings(ConnectorSettings):
    model_config = connector_config("mongo")     # PLYGHT_MONGO_*
    url: str = "mongodb://localhost:27017"
```

## Web

```python
from plyght.web import WebSettings, create_app, require_groups, web_config

class Settings(WebSettings):
    model_config = web_config("NOTES")           # NOTES_PORT, NOTES_AUTH_ENABLED, ...

app = create_app(Settings(), lifespan=lifespan)
app.include_router(router, prefix=app.state.settings.api_prefix)

@router.get("/admin", dependencies=[Depends(require_groups("admins"))])
def admin(): ...
```

`create_app` wires:

| Piece                       | What it does                                                                          |
|-----------------------------|---------------------------------------------------------------------------------------|
| `IdentityMiddleware`        | `request.state.identity` from auth proxy headers (`x-auth-request-user/-email/-groups`) |
| `SecurityHeadersMiddleware` | `nosniff`, `DENY` framing, `no-referrer`, permissions policy; opt in CSP and HSTS      |
| `RequestLoggingMiddleware`  | one line per request with status, latency, client and caller                           |
| `ProxiedClientMiddleware`   | `request.state.client_ip`, read from `X-Forwarded-For` only when trusted               |
| CORS                        | from `cors_origins`; a `*` origin never allows credentials                             |
| `/docs`, `/redoc`           | swagger and redoc served from bundled assets, no CDN, no inline script                 |
| `/health`, `/ready`         | liveness, and readiness from an optional `app.state.ready_check`                       |

- Identity headers are trusted only when the request carries
  `auth_proxy_secret` on `auth_proxy_header` (constant time compare).
  Without a secret they are trusted unverified, which depends on network
  isolation, and a warning is logged once.
- `auth_enabled=False` (the default) makes every caller anonymous and
  lets every group check pass, so turning auth on is a configuration
  change and needs no code change.
- `require_groups` returns 401 for anonymous callers and 403 for callers
  outside every listed group.
- With `trust_forwarded`, the client is the `X-Forwarded-For` entry
  `forwarded_hops` places from the right. Entries further left are
  written by the client and are never trusted.
- Every `WebSettings` field also reads `<PREFIX><FIELD>_FILE`.

## Logging

```python
from plyght import configure, get_logger

configure()                       # colored console lines on a terminal
configure(json_lines=True)        # one JSON object per line
get_logger("kafka").info("consumed", extra={"topic": "events", "offset": 42})
```

`PLYGHT_LOG_LEVEL` and `PLYGHT_LOG_JSON` override the defaults.
`configure` is idempotent: calling it again replaces the handler it
installed earlier instead of adding a second one.

## Utilities

`plyght.util.CaseConverter` detects and converts between snake,
SCREAMING, Pascal, camel, kebab and Train case.

## Samples

- [`sample/service.py`](sample/service.py) - a notes API on
  `plyght.web` and sqlite, with readiness and a group guard.
- [`sample/connectors.py`](sample/connectors.py) - probe every
  connector kind that loads in this environment.

## Tests

```
pip install -e ".[all,dev]"
pytest --cov

pip install -e ".[all,docs]"
mkdocs serve
```

[ci-shield]: https://img.shields.io/github/actions/workflow/status/parkermmr/plyght/ci.yml?branch=main&style=for-the-badge&label=CI
[ci-url]: https://github.com/parkermmr/plyght/actions/workflows/ci.yml
[coverage-shield]: https://img.shields.io/codecov/c/github/parkermmr/plyght?style=for-the-badge
[coverage-url]: https://codecov.io/gh/parkermmr/plyght
[contributors-shield]: https://img.shields.io/github/contributors/parkermmr/plyght.svg?style=for-the-badge
[contributors-url]: https://github.com/parkermmr/plyght/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/parkermmr/plyght.svg?style=for-the-badge
[forks-url]: https://github.com/parkermmr/plyght/network/members
[stars-shield]: https://img.shields.io/github/stars/parkermmr/plyght.svg?style=for-the-badge
[stars-url]: https://github.com/parkermmr/plyght/stargazers
[issues-shield]: https://img.shields.io/github/issues/parkermmr/plyght.svg?style=for-the-badge
[issues-url]: https://github.com/parkermmr/plyght/issues
