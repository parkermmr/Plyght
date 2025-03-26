import logging
import re
import time


class Formatter(logging.Formatter):
    """
    Custom formatter that applies user/data formats, injects ANSI colors
    when desired, and strips ANSI codes for file logging. Extra arguments
    are appended if no '%' placeholders are present.
    """

    ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

    def __init__(self, colored: bool = False):
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
