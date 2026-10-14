# Logging

```python
from plyght import configure, get_logger

configure()                       # console lines, level colored on a terminal
configure(json_lines=True)        # one JSON object per line
configure(level="DEBUG", stream=sys.stdout)

log = get_logger("kafka")
log.info("consumed", extra={"topic": "events", "offset": 42})
```

Console:

```
12:04:31 INFO    kafka consumed topic=events offset=42
```

JSON:

```json
{"time": "2026-10-14T01:04:31.512+00:00", "level": "INFO", "logger": "kafka", "message": "consumed", "topic": "events", "offset": 42}
```

- Fields passed through `extra=` are appended as `key=value` on the
  console and merged into the object in JSON mode. Exceptions are
  included in both.
- `PLYGHT_LOG_LEVEL` and `PLYGHT_LOG_JSON` (`1` or `true`) change
  logging without code changes.
- `configure` installs one handler on the root logger. Calling it again
  replaces that handler instead of adding a second one.

## Case conversion

`plyght.util.CaseConverter` detects a string's case and converts it:

```python
from plyght.util import Case, CaseConverter

CaseConverter.case("RedisConfig")          # Case.PASCAL
CaseConverter.snake("RedisConfig")         # "redis_config"
CaseConverter.kebab("redis_config")        # "redis-config"
CaseConverter.screaming("redisConfig")     # "REDIS_CONFIG"
```
