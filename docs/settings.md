# Settings

Connector and web settings are pydantic-settings models with one fixed
order of sources. The highest source wins:

1. Keyword arguments: `KafkaConnector(bootstrap="broker:9092")`.
2. Mounted secret files. When `PLYGHT_KAFKA_SASL_PASSWORD_FILE` names a
   file, its stripped content is the value. A pointer at a file that does
   not exist fails at startup instead of silently falling back.
3. Environment variables: `PLYGHT_KAFKA_SASL_PASSWORD`.
4. Dotenv files: `resources/.env`, then `resources/.env.<PROFILE>` when
   `PROFILE` is set. The later file wins.
5. Field defaults.

The `resources` directory is the first that exists of:

- `resources/` next to a source checkout of plyght
- `/platform/resources`
- `./resources` in the working directory

Variable names match case insensitively. Unknown keys in a dotenv file
are ignored, so one file can hold the settings for every connector and
service.

## Prefixes

| Settings                         | Prefix              |
|----------------------------------|---------------------|
| `connector_config("kafka")`      | `PLYGHT_KAFKA_`     |
| `web_config("NOTES")`            | `NOTES_`            |
| `WebSettings` without a config   | `APP_`              |

## Your own settings

```python
from plyght import ConnectorSettings, connector_config


class MongoSettings(ConnectorSettings):
    model_config = connector_config("mongo")

    url: str = "mongodb://localhost:27017"
    tls_ca: str | None = None


settings = MongoSettings()
settings.merge(url="mongodb://other:27017")       # validated copy
settings.variable("tls_ca")                        # "PLYGHT_MONGO_TLS_CA"
settings.require_file("tls_ca")                    # ValueError naming the variable if missing
```

`merge` returns a validated copy, so an override that breaks a validator
fails the same way that a bad environment variable would.
