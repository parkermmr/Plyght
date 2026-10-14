"""
plyght.web: the API template as a library (needs plyght[web]).

Every service builds on the same spine instead of copying a
template around:

    from plyght.web import WebSettings, create_app, web_config

    class Settings(WebSettings):
        model_config = web_config("MYSERVICE")

    app = create_app(Settings())
    app.include_router(my_v1_router, prefix=app.state.settings.api_prefix)

Ships the middleware stack (identity from an auth proxy + group
guards, security headers, request logging, proxied client ip), self
hosted swagger/redoc, and health/ready probes.
"""

from plyght.web.application import create_app
from plyght.web.middleware import (
    Identity,
    IdentityMiddleware,
    ProxiedClientMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    require_groups,
)
from plyght.web.settings import WebSettings, web_config

__all__ = [
    "Identity",
    "IdentityMiddleware",
    "ProxiedClientMiddleware",
    "RequestLoggingMiddleware",
    "SecurityHeadersMiddleware",
    "WebSettings",
    "create_app",
    "require_groups",
    "web_config",
]
