"""
The application factory: settings in, wired FastAPI out.

create_app gives every service the same spine - middleware
order, self-hosted docs, health/ready probes, static files - so a
service only writes its settings, lifespan, and resource routers:

    settings = Settings()                    # subclass of WebSettings
    app = create_app(settings, lifespan=lifespan)
    app.include_router(v1, prefix=settings.api_prefix)

Middleware runs outermost-last: logging sees the proxied client ip
and the final response including security headers. A CORS wildcard
never allows credentials, so "*" means anonymous calls only. The docs
bundle mounts under /static/plyght so a service can mount its own
/static without colliding.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from plyght.logging import configure
from plyght.web.middleware.identity import IdentityMiddleware
from plyght.web.middleware.proxied_client import ProxiedClientMiddleware
from plyght.web.middleware.request_logging import RequestLoggingMiddleware
from plyght.web.middleware.security_headers import SecurityHeadersMiddleware
from plyght.web.routers import docs, health
from plyght.web.settings import WebSettings

STATIC = Path(__file__).resolve().parent / "static"


def create_app(settings: WebSettings | None = None, *, lifespan=None) -> FastAPI:
    """
    Build a FastAPI application with the middleware stack,
    self-hosted docs, and health probes already wired. Pass settings
    explicitly in tests; include your versioned routers afterwards
    under settings.api_prefix.
    """
    settings = settings or WebSettings()
    configure(level=settings.log_level, json_lines=settings.log_json)

    app = FastAPI(
        title=settings.name,
        version=settings.version,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = settings

    app.add_middleware(
        IdentityMiddleware,
        enabled=settings.auth_enabled,
        header_user=settings.header_user,
        header_email=settings.header_email,
        header_groups=settings.header_groups,
        proxy_secret=settings.auth_proxy_secret,
        proxy_header=settings.auth_proxy_header,
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts=settings.hsts,
        csp=settings.csp,
        csp_exempt=settings.csp_exempt,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        ProxiedClientMiddleware,
        trust_forwarded=settings.trust_forwarded,
        hops=settings.forwarded_hops,
    )
    if settings.cors_origins:
        origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials="*" not in origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.mount(
        "/static/plyght", StaticFiles(directory=str(STATIC)), name="plyght-static"
    )
    app.include_router(health.router)
    app.include_router(docs.router)
    return app
