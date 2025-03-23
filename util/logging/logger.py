import logging
from typing import Optional, Any
from functools import wraps
from util.logging.formatter import Formatter


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


def log_exceptions(logger: Logger):
    """Decorator to log exceptions from the decorated function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                caller = f"{func.__module__}.{func.__qualname__}"
                logger.error(
                    f"Exception in {caller}: {e}",
                    extra={"caller": caller}
                )
                raise
        return wrapper
    return decorator
