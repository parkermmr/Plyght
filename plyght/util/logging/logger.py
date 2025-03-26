import os
import logging
import inspect

from logging import Logger as BaseLogger
from typing import Optional, Any
from functools import wraps

from plyght.util.logging.formatter import Formatter


class Logger(logging.Logger):
    """
    A logger subclass that provides methods for user- and data-
    initiated logs. It uses the dictionary config if available,
    and otherwise attaches a file and a stream handler.
    """
    LOG_FILE = 'application.log'

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        logfile: Optional[str] = LOG_FILE,
        colored: bool = False
    ):
        super().__init__(name, level)
        if not self.hasHandlers():
            if logfile:
                file_handler = logging.FileHandler(logfile)
                file_handler.setFormatter(Formatter(colored=False))
                self.addHandler(file_handler)
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(Formatter(colored=colored))
            self.addHandler(stream_handler)
        self.propagate = False

    def log_user(
        self, level: int,
        transaction_id: str,
        service: str,
        caller: str,
        user_id: str,
        request_uri: str,
        message: str,
        data_id: Optional[str] = None,
        api_response_code: Optional[int] = None,
        **kwargs: Any
    ) -> None:
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
        self, level: int,
        data_id: str,
        service: str,
        caller: str,
        request_uri: str,
        message: str,
        api_response_code: Optional[int] = None,
        **kwargs: Any
    ) -> None:
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
    Logs exceptions in the format: package.module:line
    Uses self.logger if available, otherwise uses passed logger.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            instance_logger = getattr(args[0], 'logger', None) if args else None
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
                            mod_path = (
                                os.path.splitext(rel_path)[0].replace(os.sep, ".")
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
                        extra={"caller": caller_info}
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
