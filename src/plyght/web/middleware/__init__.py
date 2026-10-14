"""The security and observability middleware stack."""

from plyght.web.middleware.identity import (
    Identity,
    IdentityMiddleware,
    require_groups,
)
from plyght.web.middleware.proxied_client import ProxiedClientMiddleware
from plyght.web.middleware.request_logging import RequestLoggingMiddleware
from plyght.web.middleware.security_headers import SecurityHeadersMiddleware

__all__ = [
    "Identity",
    "IdentityMiddleware",
    "ProxiedClientMiddleware",
    "RequestLoggingMiddleware",
    "SecurityHeadersMiddleware",
    "require_groups",
]
