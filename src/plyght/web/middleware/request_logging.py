"""
Request logging: one line per request with method, path, status,
latency, and who made it, leveled by outcome (5xx error, 4xx warning,
else info). The application names the caller by setting
request.state.caller while it handles the request; a request that
never says stays anonymous in the log.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from plyght.logging import get_logger

log = get_logger("plyght.web.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Times every request and logs its outcome at the right level."""

    async def dispatch(self, request: Request, call_next):
        """Measure the handler, then log client, caller, route, status, ms."""
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception(
                "unhandled",
                extra={"method": request.method, "path": request.url.path},
            )
            raise
        elapsed = (time.perf_counter() - started) * 1000
        client = getattr(request.state, "client_ip", None) or (
            request.client.host if request.client else "unknown"
        )
        level = (
            log.error
            if response.status_code >= 500
            else log.warning if response.status_code >= 400 else log.info
        )
        fields = {
            "status": response.status_code,
            "ms": round(elapsed, 2),
            "client": client,
        }
        caller = getattr(request.state, "caller", None)
        if caller:
            fields["caller"] = caller
        level(f"{request.method} {request.url.path}", extra=fields)
        return response
