"""
Baseline security headers on every response. HSTS is opt-in because
sending it from a plain-http dev server poisons the browser for the
whole host.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds the no-argument security headers every service should send,
    plus an optional Content-Security-Policy. csp_exempt names path
    prefixes the policy must NOT cover - proxied third-party pages
    (application dashboards) ship their own inline styles and scripts
    and would break under the host application's policy.
    """

    def __init__(
        self, app, hsts: bool = False, csp: str = "", csp_exempt: str = ""
    ) -> None:
        super().__init__(app)
        self.hsts = hsts
        self.csp = csp
        self.exempt = tuple(
            prefix.strip() for prefix in csp_exempt.split(",") if prefix.strip()
        )

    async def dispatch(self, request: Request, call_next):
        """Stamp the headers onto the outgoing response."""
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        exempted = self.exempt and request.url.path.startswith(self.exempt)
        if self.csp and not exempted:
            response.headers.setdefault("Content-Security-Policy", self.csp)
        if self.hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response
