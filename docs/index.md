---
hide:
  - navigation
---

# Plyght

Typed connectors, settings, logging and a FastAPI service spine.

Kafka, redis, postgres, s3 and sqlite all sit behind one small
[`Connector`](connectors.md) lifecycle, each configured from the
environment through [settings](settings.md). [`plyght.web`](web.md)
builds a FastAPI app that already has its middleware, docs and health
probes wired, and [`plyght.logging`](logging.md) gives services console
or JSON logs from a single call.

## Install

```
pip install plyght                 # settings, logging, sqlite, standard library utilities
pip install "plyght[kafka]"        # + KafkaConnector (aiokafka)
pip install "plyght[redis]"        # + RedisConnector (redis)
pip install "plyght[postgres]"     # + PostgresConnector (psycopg)
pip install "plyght[s3]"           # + S3Connector (boto3)
pip install "plyght[web]"          # + plyght.web (fastapi, uvicorn)
pip install "plyght[all]"
```

Python 3.12 or newer.

## A taste

```python
from fastapi import APIRouter
from plyght.connectors import PostgresConnector
from plyght.web import WebSettings, create_app, web_config


class Settings(WebSettings):
    model_config = web_config("ORDERS")          # ORDERS_PORT, ORDERS_AUTH_ENABLED, ...


database = PostgresConnector()                    # PLYGHT_POSTGRES_HOST, ...
router = APIRouter()


@router.get("/orders")
async def orders() -> list[dict]:
    return await database.fetch("select * from orders")


app = create_app(Settings())
app.include_router(router, prefix=app.state.settings.api_prefix)
```

The repository's `sample/` directory has a complete service and a
connector probe that you can run as they are.
