from dataclasses import dataclass


@dataclass
class Response:
    """
    Custom HTTP response data class.

    Attributes:
        status: HTTP status code of the response.
        content: Raw response body as bytes.
        headers: Response headers.
        response_time: Time taken to complete the request, in seconds.
    """

    status: int
    content: bytes
    headers: dict[str, str]
    response_time: float
