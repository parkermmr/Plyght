"""
This module provides a specialized Logger class with advanced logging functionality,
along with a decorator to log exceptions. The Logger class extends Python's built-in
logging.Logger, providing additional methods to log user- and data-related events.
"""

import inspect
import logging
import os
from functools import wraps
from logging import Logger as BaseLogger
from typing import Any, Optional
from plyght.util.logging.json_formatter import JsonFormatter
from plyght.util.logging.formatter import Formatter


class Logger(BaseLogger):
    """
    A logger subclass that provides methods for user- and data-initiated logs.
    Uses the dictionary config if available, or attaches both a file and a stream
    handler.

    :param name: Name for this logger.
    :param level: Logging level. Defaults to logging.INFO.
    :param logfile: Optional log file name/path. Defaults to 'application.log'.
    :param colored: Whether log output should use colored formatting. Defaults to False.
    """
    LOG_SCHEMA = {
        "ts": "@time",
        "level": "@level",
        "msg": "@message",
        "trace": "@exception",
        "module": "@module",
        "logger": "@logger",
        "@all": None,
    }

    LOG_FILE = "application.log"

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        logfile: Optional[str] = LOG_FILE,
        colored: bool = False,
    ):
        """
        Initialize the Logger instance.

        :param name: Name for this logger.
        :param level: Logging level. Defaults to logging.INFO.
        :param logfile: Optional log file name/path. Defaults to 'application.log'.
        :param colored: Whether log output should use colored formatting.
                         Defaults to False.
        """
        super().__init__(name, level)
        if not self.hasHandlers():
            if logfile:
                file_handler = logging.FileHandler(logfile)
                file_handler.setFormatter(JsonFormatter(schema=self.LOG_SCHEMA))
                self.addHandler(file_handler)

            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(Formatter(colored=colored))
            self.addHandler(stream_handler)

        self.propagate = False

    def log_user(
        self,
        level: int,
        transaction_id: str,
        service: str,
        caller: str,
        user_id: str,
        request_uri: str,
        message: str,
        data_id: Optional[str] = None,
        api_response_code: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log a user event with additional metadata.

        :param level: Logging level (e.g., logging.INFO).
        :param transaction_id: Unique transaction identifier.
        :param service: Name of the service or module logging this event.
        :param caller: The calling method or function.
        :param user_id: Identifier for the user triggering the event.
        :param request_uri: URI of the request causing this log.
        :param message: Human-readable log message.
        :param data_id: Optional identifier for associated data.
        :param api_response_code: Optional HTTP response code or similar.
        :param kwargs: Additional keyword arguments for the log method.
        """
        extra = {
            "log_type": "user",
            "transaction_id": transaction_id,
            "service": service,
            "caller": caller,
            "user_id": user_id,
            "request_uri": request_uri,
            "data_id": data_id,
            "api_response_code": api_response_code,
        }
        self.log(level, message, extra=extra, **kwargs)

    def log_data(
        self,
        level: int,
        data_id: str,
        service: str,
        caller: str,
        request_uri: str,
        message: str,
        api_response_code: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log a data event with additional metadata.

        :param level: Logging level (e.g., logging.INFO).
        :param data_id: Unique identifier of the data being logged.
        :param service: Name of the service or module logging this event.
        :param caller: The calling method or function.
        :param request_uri: URI of the request causing this log.
        :param message: Human-readable log message.
        :param api_response_code: Optional HTTP response code or similar.
        :param kwargs: Additional keyword arguments for the log method.
        """
        extra = {
            "log_type": "data",
            "data_id": data_id,
            "service": service,
            "caller": caller,
            "request_uri": request_uri,
            "api_response_code": api_response_code,
        }
        self.log(level, message, extra=extra, **kwargs)


def log_exceptions(logger: BaseLogger = None):
    """
    Decorator to log exceptions in the format: package.module:line.
    Uses logger from the class instance if available, otherwise
    uses the logger passed in.

    :param logger: Optional logger to use if no logger is found on the instance.
    :return: Decorated function that logs any raised exceptions.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            instance_logger = getattr(args[0], "logger", None) if args else None
            active_logger = (
                instance_logger if isinstance(instance_logger, BaseLogger) else logger
            )

            try:
                return func(*args, **kwargs)
            except Exception as e:
                caller_info = f"{func.__module__}.{func.__qualname__}"

                try:
                    stack = inspect.stack()
                    for frame_info in stack[1:]:
                        frame = frame_info.frame
                        lineno = frame_info.lineno
                        filename = os.path.abspath(frame_info.filename)

                        if "logger" in filename:
                            continue

                        mod_name = frame.f_globals.get("__name__")

                        if mod_name == "__main__":
                            cwd = os.getcwd()
                            rel_path = os.path.relpath(filename, cwd)
                            mod_path = os.path.splitext(rel_path)[0].replace(
                                os.sep, "."
                            )
                            mod_name = mod_path

                        caller_info = f"{mod_name}:{lineno}"
                        break
                except Exception as inspect_error:
                    if active_logger:
                        active_logger.warning(
                            f"Could not inspect call stack: {inspect_error}"
                        )

                if active_logger:
                    active_logger.error(
                        f"Exception in {caller_info}: {e}",
                        extra={"caller": caller_info},
                    )
                else:
                    print(f"[ERROR] Exception in {caller_info}: {e}")

                raise

        return wrapper

    if callable(logger):
        func = logger
        logger = None
        return decorator(func)

    return decorator


mylogger = Logger(__name__)
mylogger.info("Trying new message...")
