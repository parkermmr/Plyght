"""
Real client address behind a reverse proxy: when trust_forwarded is
on, request.state.client_ip is the address the nearest trusted proxy
saw, so logs and rate limits see the caller, not the proxy. Off, the
socket peer is used and forwarded headers are ignored entirely.

Each proxy appends the address it received from to X-Forwarded-For, so
only the right-most entries were written by proxies we run; anything
to their left came from the client and can say anything. hops is how
many proxies sit in front of this process: the client is the entry
that many places from the right. Reading the left-most entry instead,
as this once did, let any caller choose its own address by sending
the header itself.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class ProxiedClientMiddleware(BaseHTTPMiddleware):
    """Resolves request.state.client_ip once, up front."""

    def __init__(self, app, trust_forwarded: bool = False, hops: int = 1) -> None:
        super().__init__(app)
        self.trust_forwarded = trust_forwarded
        self.hops = max(1, hops)

    async def dispatch(self, request: Request, call_next):
        """Stash the effective client ip on request.state."""
        client_ip = request.client.host if request.client else None
        if self.trust_forwarded:
            client_ip = forwarded(request.headers.get("x-forwarded-for"), self.hops) or client_ip
        request.state.client_ip = client_ip
        return await call_next(request)


def forwarded(header: str | None, hops: int) -> str | None:
    """
    The client address a chain of hops trusted proxies recorded, or
    None when the header is absent or empty. A chain shorter than the
    hops configured yields its left-most entry, the furthest any proxy
    of ours could have seen.
    """
    parts = [part.strip() for part in (header or "").split(",") if part.strip()]
    if not parts:
        return None
    return parts[-hops] if len(parts) >= hops else parts[0]
