"""
Provides custom exception classes for more detailed error handling within client
implementations. These exception classes add extra information such as a status code
and error type to facilitate clearer debugging and logging.
"""


class ConnectionException(Exception):
    """
    Overrides the base exception to offer status codes and additional details for
    connection-related errors.
    """

    def __init__(self, status_code: int, error_type: str, info: str):
        """
        Initialize the exception with a status code, an error type, and a message.

        :param status_code: Numeric status code to represent the connection error.
        :param error_type: String identifying the type of error.
        :param info: Additional information describing the error.
        """
        self.status_code = status_code
        self.error_type = error_type
        self.info = info
        super().__init__(f"{self.error_type} - {self.status_code} - {self.info}")

    def __str__(self):
        """
        Return a string representation that includes the error type,
        status code, and info message.
        """
        return f"{self.error_type} - {self.status_code} - {self.info}"
