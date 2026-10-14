"""
Logging: one handler however often configure runs, extras rendered as
key=value on the console and merged into json lines.
"""

import io
import json
import logging

from plyght import configure, get_logger


def emit(json_lines: bool) -> str:
    stream = io.StringIO()
    configure(level="INFO", json_lines=json_lines, stream=stream)
    get_logger("demo").info("consumed", extra={"topic": "events", "offset": 42})
    return stream.getvalue()


def test_console_line_carries_extras():
    line = emit(json_lines=False)
    assert "INFO" in line and "demo consumed" in line
    assert "topic=events offset=42" in line


def test_json_line_merges_extras():
    entry = json.loads(emit(json_lines=True))
    assert entry["message"] == "consumed"
    assert entry["logger"] == "demo"
    assert (entry["topic"], entry["offset"]) == ("events", 42)


def test_configure_is_idempotent():
    configure()
    configure()
    named = [handler for handler in logging.getLogger().handlers if handler.name == "plyght"]
    assert len(named) == 1
