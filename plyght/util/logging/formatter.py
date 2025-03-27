"""
This module provides a custom logging.Formatter subclass that supports
user/data log formatting, optional ANSI color injection, and automatic
ANSI code stripping for file logs.
"""

import logging
import re
import time


class Formatter(logging.Formatter):
    """
    A custom logging formatter that applies specialized formats for user-
    and data-related logs, optionally includes ANSI colors, and strips
    ANSI escape codes when colors are not desired.

    If a log record contains extra arguments with no '%' placeholders, those
    arguments are appended to the log message string.
    """

    ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

    def __init__(self, colored: bool = False):
        """
        Initialize the Formatter instance.

        :param colored: If True, ANSI color codes will be added to the log output.
        """
        super().__init__(
            fmt="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
            style="%",
        )
        self.colored = colored
        logging.Formatter.converter = time.gmtime

        self.user_fmt = (
            "%(asctime)s - %(levelname)s - [TX: %(transaction_id)s] "
            "- [Service: %(service)s] - [Caller: %(caller)s] "
            "- [User: %(user_id)s] - [URI: %(request_uri)s] - %(message)s"
        )
        self.data_fmt = (
            "%(asctime)s - %(levelname)s - [Data: %(data_id)s] "
            "- [Service: %(service)s] - [Caller: %(caller)s] "
            "- [URI: %(request_uri)s] - %(message)s"
        )
        self.default_fmt = "%(asctime)s - %(levelname)s - %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the specified log record as text.

        If record.args is non-empty and there are no '%' placeholders in
        record.msg, the args are appended to the message.

        Determines the format string based on whether the record indicates a
        user or data event. If an api_response_code is present, that is also
        included. If colored output is enabled, ANSI color codes are applied
        to the log level name. For non-colored output, any ANSI codes are
        stripped before returning the final log message.

        :param record: The log record to format.
        :return: Formatted log record as a string.
        """
        if record.args and "%" not in record.msg:
            extra = " ".join(str(arg) for arg in record.args)
            record.msg = f"{record.msg} {extra}"
            record.args = ()

        if hasattr(record, "log_type"):
            fmt = self.user_fmt if record.log_type == "user" else self.data_fmt
        else:
            fmt = self.default_fmt

        if getattr(record, "api_response_code", None) is not None:
            fmt += " - [Response: %(api_response_code)s]"
        self._style._fmt = fmt

        if self.colored:
            lvl = record.levelname
            color = ""
            if lvl == "DEBUG":
                color = "\033[34m"
            elif lvl == "INFO":
                color = "\033[32m"
            elif lvl == "WARNING":
                color = "\033[33m"
            elif lvl == "ERROR":
                color = "\033[31m"
            elif lvl == "CRITICAL":
                color = "\033[1;31m"
            if color:
                record.levelname = f"{color}{lvl}\033[0m"

        output = super().format(record)

        if not self.colored:
            output = self.ANSI_ESCAPE.sub("", output)

        return output
