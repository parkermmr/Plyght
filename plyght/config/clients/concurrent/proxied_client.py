from ssl import create_default_context, CERT_NONE, SSLContext
from time import perf_counter
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientSession, TCPConnector, BasicAuth, ClientTimeout
from async_property import async_property

from plyght.config.clients.concurrent.async_client import AsyncClient
from plyght.config.clients.exceptions import ConnectionException
from plyght.util.logging.logger import Logger
from plyght.core.structures import Response


class AsyncProxiedClient(AsyncClient):
    """
    Async HTTP client with optional SSL (server verification, custom CA),
    password-protected client cert/key, and proxy support.

    For more information on Plyght configurations see:
        https://plyght.teampixl.info/config/intro,
        https://plyght.teampixl.info/config/clients/concurrent/proxied
    """

    def __init__(
        self,
        host: str,
        auth: tuple[str, str] | None = None,
        ssl_enabled: bool = False,
        cert: str | None = None,
        key: str | None = None,
        key_password: str | None = None,
        ca_cert: str | None = None,
        verify: bool = False,
        proxy: str | None = None,
        proxy_auth: tuple[str, str] | None = None,
        timeout: float | None = None,
    ) -> None:
        """
        Initialize with host, auth, SSL/TLS, proxy, and timeout settings.

        :param host: Base URL including scheme.
        :param auth: (user, pass) for HTTP basic auth.
        :param ssl_enabled: Enable custom SSLContext.
        :param cert: Path to client cert PEM.
        :param key: Path to client key PEM.
        :param key_password: Password for client key.
        :param ca_cert: Path to CA bundle PEM.
        :param verify: Verify server certs.
        :param proxy: Proxy URL.
        :param proxy_auth: (user, pass) for proxy.
        :param timeout: Total timeout in seconds.
        """
        super().__init__()
        self.logger = Logger(self.__class__.__name__)
        self._host = host
        self.auth = auth
        self.ssl_enabled = ssl_enabled
        self.cert = cert
        self.key = key
        self.key_password = key_password
        self.ca_cert = ca_cert
        self.verify = verify
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.timeout = timeout
        self._session: ClientSession | None = None

    @async_property
    async def host(self) -> str:
        """Return configured host URL."""
        return self._host

    @async_property
    async def status(self) -> bool:
        """True if session is active, False otherwise."""
        if not self._session:
            self.logger.warning("No active HTTP session is established.")
            return False
        return True

    @async_property
    async def client(self) -> ClientSession:
        """
        Return the active ClientSession or raise if not connected.

        :raises ConnectionException: If session not established.
        """
        if not self._session:
            raise ConnectionException(
                404,
                "NoConnectionFound",
                "Async HTTP session not yet established; call connect() first.",
            )
        return self._session

    def ssl_context(self) -> SSLContext | None:
        """Build SSLContext if enabled, else None."""
        if not self.ssl_enabled:
            return None
        ctx = create_default_context(cafile=self.ca_cert)
        if not self.verify:
            ctx.check_hostname = False
            ctx.verify_mode = CERT_NONE
        if self.cert and self.key:
            ctx.load_cert_chain(self.cert, self.key, password=self.key_password)
        return ctx

    def _build_url(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        """
        Join host and endpoint, URL-encode query params.

        :param endpoint: Path to append.
        :param params: Query parameters.
        """
        base = self._host.rstrip("/")
        path = endpoint.lstrip("/")
        url = f"{base}/{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        return url

    async def connect(self) -> None:
        """Establish ClientSession with SSL, auth, proxy, and timeout."""
        if self._session is not None:
            return
        self.logger.info(f"Establishing async HTTP session to {self._host}")
        ssl_ctx = self.ssl_context()
        connector = TCPConnector(ssl=ssl_ctx)
        timeout = ClientTimeout(total=self.timeout) if self.timeout else None
        auth = BasicAuth(*self.auth) if self.auth else None
        self._session = ClientSession(connector=connector, auth=auth, timeout=timeout)

    async def disconnect(self) -> None:
        """Close and clear the ClientSession."""
        if not self._session:
            return
        self.logger.info("Closing async HTTP session")
        await self._session.close()
        self._session = None

    async def _request(
        self, method: str, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """
        Core request method using perf_counter for timing and proxy options.
        """
        await self.connect()
        url = self._build_url(endpoint, params)
        session = await self.client
        start = perf_counter()
        async with session.request(
            method,
            url,
            proxy=self.proxy,
            proxy_auth=BasicAuth(*self.proxy_auth) if self.proxy_auth else None,
            **kwargs,
        ) as resp:
            content = await resp.read()
        elapsed = perf_counter() - start
        return Response(
            status=resp.status,
            content=content,
            headers=dict(resp.headers),
            response_time=elapsed,
        )

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """Issue a GET request."""
        return await self._request("GET", endpoint, params, **kwargs)

    async def head(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """Issue a HEAD request."""
        return await self._request("HEAD", endpoint, params, **kwargs)

    async def post(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """Issue a POST request."""
        return await self._request("POST", endpoint, params, **kwargs)

    async def put(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """Issue a PUT request."""
        return await self._request("PUT", endpoint, params, **kwargs)

    async def patch(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """Issue a PATCH request."""
        return await self._request("PATCH", endpoint, params, **kwargs)

    async def delete(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """Issue a DELETE request."""
        return await self._request("DELETE", endpoint, params, **kwargs)
