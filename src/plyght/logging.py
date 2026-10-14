"""
Logging for services: one call to configure, structured when
machines read it, readable when humans do.

    from plyght.logging import configure, get_logger

    configure()                    # concise colored console lines
    configure(json_lines=True)     # one JSON object per line
    log = get_logger("kafka")
    log.info("consumed", extra={"topic": "events", "offset": 42})

Extra fields ride along: rendered as key=value suffixes on console,
merged into the object in JSON mode. PLYGHT_LOG_LEVEL and
PLYGHT_LOG_JSON environment variables override the defaults so
deployments retune logging without code changes.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

_RESERVED = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "taskName", "color_message"}

_COLORS = {
    logging.DEBUG: "\033[2m",
    logging.INFO: "\033[36m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[1;31m",
}
_RESET = "\033[0m"


def _extras(record: logging.LogRecord) -> dict:
    """
    The fields a caller passed through extra=, leaving out the
    bookkeeping attributes every LogRecord carries.
    """
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RESERVED and not key.startswith("_")
    }


class ConsoleFormatter(logging.Formatter):
    """
    `HH:MM:SS LEVEL name message key=value` with the level colored
    when the stream is a terminal.
    """

    def __init__(self, colored: bool | None = None) -> None:
        super().__init__()
        self.colored = sys.stderr.isatty() if colored is None else colored

    def format(self, record: logging.LogRecord) -> str:
        stamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level = record.levelname
        if self.colored:
            level = f"{_COLORS.get(record.levelno, '')}{level}{_RESET}"
        line = f"{stamp} {level:<7} {record.name} {record.getMessage()}"
        extras = _extras(record)
        if extras:
            line += " " + " ".join(f"{key}={value}" for key, value in extras.items())
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class JsonFormatter(logging.Formatter):
    """
    One JSON object per line: time, level, logger, message, extras,
    and the exception when present. No dependency needed.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **_extras(record),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure(
    level: str | int | None = None,
    json_lines: bool | None = None,
    stream=None,
) -> None:
    """
    Install one handler on the root logger (idempotent: replaces any
    handler a previous configure installed).
    """
    if level is None:
        level = os.environ.get("PLYGHT_LOG_LEVEL", "INFO")
    if json_lines is None:
        json_lines = os.environ.get("PLYGHT_LOG_JSON", "").lower() in ("1", "true")
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.set_name("plyght")
    handler.setFormatter(JsonFormatter() if json_lines else ConsoleFormatter())
    root = logging.getLogger()
    root.handlers = [entry for entry in root.handlers if entry.name != "plyght"]
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """A named standard library logger."""
    return logging.getLogger(name)
