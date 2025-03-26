class ConnectionException(Exception):
    """
    Overides the base exception and provides more details error handling for client
      errors. Specifically implements status codes to provide additional connection
      error information.
    """

    def __init__(self, status_code: int, error_type: str, info: str):
        self.status_code = status_code
        self.error_type = error_type
        self.info = info
        super().__init__(f"{self.error_type} - {self.status_code} - {self.info}")

    def __str__(self):
        return f"{self.error_type} - {self.status_code} - {self.info}"
