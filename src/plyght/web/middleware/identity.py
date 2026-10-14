"""
Who is calling: identity from the auth proxy's headers.

Deployed behind oauth2-proxy (or an equivalent), the proxy authenticates against your idp and injects
X-Auth-Request-User/-Email/-Groups. This middleware parses those into
request.state.identity; the require_groups dependency turns group
membership (which carries role information from keycloak or gitlab)
into per-route authorization.

Trusting those headers blindly is a spoofing hole: anything that can
reach the application port directly (not through the proxy) could set
them and impersonate any user in any group. So the headers are trusted
ONLY when the request proves it came through the trusted proxy. Set
proxy_secret to a shared value the proxy injects on a header the public
cannot forge (it never reaches the internet); the middleware verifies
it with a constant-time compare and, on mismatch, treats the caller as
anonymous. When no proxy_secret is configured the middleware falls back
to trusting the headers and logs a warning once - that mode relies
entirely on network isolation between the proxy and the app and should
only be used where that isolation is guaranteed.

With auth_enabled=False (development) every request is an anonymous
identity and group checks pass open - the wiring stays identical so
enabling auth later changes configuration, not code.
"""

import hmac
from dataclasses import dataclass, field

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from plyght.logging import get_logger

_log = get_logger("plyght.web.identity")


@dataclass
class Identity:
    """
    The authenticated caller as the auth proxy reported them. source
    says how the identity was established, for audit and for routes
    that tell a verified proxy session from a raw header.
    """

    user: str | None = None
    email: str | None = None
    groups: list[str] = field(default_factory=list)
    source: str = "anonymous"

    @property
    def authenticated(self) -> bool:
        """True when the proxy identified a user."""
        return self.user is not None


def trusts_headers(get, proxy_secret: str, proxy_header: str) -> bool:
    """
    Whether identity headers from this request may be trusted: with a
    proxy secret configured, require a constant-time match on the proxy
    header; without one, trust them (network-isolation mode). get is a
    header lookup like request.headers.get, so both the http middleware
    and the websocket path can share this check.
    """
    if proxy_secret:
        return hmac.compare_digest(get(proxy_header, "") or "", proxy_secret)
    return True


def parse_identity(
    get,
    header_user: str = "x-auth-request-user",
    header_email: str = "x-auth-request-email",
    header_groups: str = "x-auth-request-groups",
) -> Identity:
    """
    Build an Identity from trusted proxy headers (call only after
    trusts_headers has passed). Anonymous when no user header is present.
    """
    user = get(header_user)
    if not user:
        return Identity()
    return Identity(
        user=user,
        email=get(header_email),
        groups=[
            group.strip()
            for group in (get(header_groups, "") or "").split(",")
            if group.strip()
        ],
        source="proxy",
    )


class IdentityMiddleware(BaseHTTPMiddleware):
    """Parses verified proxy identity headers into request.state.identity."""

    def __init__(
        self,
        app,
        enabled: bool,
        header_user: str = "x-auth-request-user",
        header_email: str = "x-auth-request-email",
        header_groups: str = "x-auth-request-groups",
        proxy_secret: str = "",
        proxy_header: str = "x-auth-proxy-secret",
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.header_user = header_user
        self.header_email = header_email
        self.header_groups = header_groups
        self.proxy_secret = proxy_secret
        self.proxy_header = proxy_header
        self._warned_unverified = False

    def _trusts_headers(self, request: Request) -> bool:
        """
        Whether this request's identity headers came from the trusted
        proxy. With a proxy secret configured, require a constant-time
        match; without one, fall back to trusting them (network
        isolation mode) and warn once.
        """
        if not self.proxy_secret and not self._warned_unverified:
            self._warned_unverified = True
            _log.warning(
                "auth is enabled but AUTH_PROXY_SECRET is not set; identity "
                "headers are trusted without verification and can be spoofed "
                "by anything that reaches this port directly. Set a proxy "
                "secret and inject it from the auth proxy."
            )
        return trusts_headers(request.headers.get, self.proxy_secret, self.proxy_header)

    async def dispatch(self, request: Request, call_next):
        """Attach the caller's Identity (anonymous when auth is off)."""
        identity = Identity()
        if self.enabled and self._trusts_headers(request):
            identity = parse_identity(
                request.headers.get,
                self.header_user,
                self.header_email,
                self.header_groups,
            )
        request.state.identity = identity
        return await call_next(request)


def require_groups(*groups: str):
    """
    Route dependency enforcing group membership:

        @router.get("/admin", dependencies=[Depends(require_groups("admins"))])

    401 when unauthenticated, 403 when authenticated but outside every
    listed group. Passes open when auth is disabled (development).
    """

    def check(request: Request) -> Identity:
        identity: Identity = getattr(request.state, "identity", Identity())
        if not request.app.state.settings.auth_enabled:
            return identity
        if not identity.authenticated:
            raise HTTPException(status_code=401, detail="not authenticated")
        if groups and not set(groups) & set(identity.groups):
            raise HTTPException(
                status_code=403, detail=f"requires one of groups {sorted(groups)}"
            )
        return identity

    return check
