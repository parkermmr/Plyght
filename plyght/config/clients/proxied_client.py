from typing import Any
from time import perf_counter
from requests import Session
from ssl import create_default_context, SSLContext, CERT_NONE
from requests.adapters import HTTPAdapter

from urllib.parse import urlencode
from urllib3.poolmanager import PoolManager

from plyght.config.clients.client import Client
from plyght.config.clients.exceptions import ConnectionException
from plyght.util.logging.logger import Logger
from plyght.core.structures import Response


class SSLAdapter(HTTPAdapter):
    """
    Adapter for the requests library to allow passing a custom SSLContext
    to urllib3's PoolManager for HTTPS connections.
    """

    def __init__(self, ssl_context: SSLContext, **kwargs):
        """
        Initialize the SSLAdapter.

        :param ssl_context: An SSLContext to use for HTTPS connections.
        :param kwargs: Additional keyword arguments for the base HTTPAdapter.
        """
        super().__init__(**kwargs)
        self.ssl_context = ssl_context

    def init_poolmanager(
        self, connections: int, maxsize: int, block: bool = False, **pool_kwargs
    ):
        """
        Create and initialize the urllib3 PoolManager with the custom SSL context.

        :param connections: Number of connection pools to cache.
        :param maxsize: Maximum number of connections to save in the pool.
        :param block: Whether the pool should block for connections.
        :param pool_kwargs: Additional keyword arguments for PoolManager.
        """
        pool_kwargs["ssl_context"] = self.ssl_context
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs
        )


class ProxiedClient(Client):
    """
    HTTP client with optional SSL (server verification, custom CA),
    password-protected client cert/key, and proxy support.

    For more information on Plyght configurations see:
        https://plyght.teampixl.info/config/intro,
        https://plyght.teampixl.info/config/clients/proxied
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
    ) -> None:
        """
        Initialize the ProxiedClient with configuration for authentication,
        SSL/TLS, and proxy settings.

        :param host: Base URL (including scheme) for the target service.
        :param auth: Tuple of (username, password) for HTTP basic auth.
        :param ssl_enabled: Whether to enable custom SSL context.
        :param cert: Path to client certificate file (PEM).
        :param key: Path to client private key file (PEM).
        :param key_password: Password for the client private key.
        :param ca_cert: Path to CA bundle file for server verification.
        :param verify: Whether to verify server certificates.
        :param proxy: Proxy URL (e.g. "http://proxy.example.com:3128").
        :param proxy_auth: Tuple of (username, password) for proxy basic auth.
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
        self._session: Session | None = None

    def _build_url(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        """
        Construct a full URL by joining host and endpoint, and URL-encode query params.

        :param endpoint: Path to append to the base host URL.
        :param params: Dictionary of query parameters.
        :return: Fully qualified URL.
        """
        base = self.host.rstrip("/")
        path = endpoint.lstrip("/")
        url = f"{base}/{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        return url

    @property
    def host(self) -> str:
        """
        Return the configured host URL.
        """
        return self._host

    @property
    def client(self) -> Session:
        """
        Return the active requests.Session, or raise if not connected.

        :return: Active HTTP session.
        :raises ConnectionException: If session has not been established.
        """
        if not self._session:
            raise ConnectionException(
                404,
                "NoConnectionFound",
                "HTTP session not yet established; call connect() first.",
            )
        return self._session

    @property
    def status(self) -> bool:
        """
        Return True if a session is active, False otherwise.

        :return: Boolean connection status.
        """
        if not self._session:
            self.logger.warning("No active HTTP session is established.")
            return False
        return True

    def ssl_context(self) -> SSLContext | None:
        """
        Build and return an SSLContext if ssl_enabled, else None.

        :return: Configured SSLContext or None.
        """
        if not self.ssl_enabled:
            return None
        ctx = create_default_context(cafile=self.ca_cert)
        if not self.verify:
            ctx.check_hostname = False
            ctx.verify_mode = CERT_NONE
        if self.cert and self.key:
            ctx.load_cert_chain(
                certfile=self.cert, keyfile=self.key, password=self.key_password
            )
        return ctx

    def connect(self) -> None:
        """
        Establish the HTTP session with the configured SSLContext, auth, and proxy.

        Subsequent calls have no effect if already connected.
        """
        if self._session is not None:
            return
        self.logger.info(f"Establishing HTTP session to {self.host}")
        sess = Session()
        ctx = self.ssl_context()
        if ctx:
            sess.mount("https://", SSLAdapter(ctx))
        else:
            sess.verify = self.verify
        if self.auth:
            sess.auth = self.auth
        if self.proxy:
            proxy_url = self.proxy
            if self.proxy_auth:
                scheme, rest = proxy_url.split("://", 1)
                proxy_url = (
                    f"{scheme}://{self.proxy_auth[0]}:{self.proxy_auth[1]}@{rest}"
                )
            sess.proxies = {"http": proxy_url, "https": proxy_url}
        self._session = sess

    def disconnect(self) -> None:
        """
        Close and clear the active HTTP session.
        """
        if not self._session:
            return
        self.logger.info("Closing HTTP session")
        self._session.close()
        self._session = None

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """
        Issue a GET request to the specified endpoint.

        :param endpoint: Path to append to the base host URL.
        :param params: Query parameters to URL-encode.
        :param kwargs: Passed to Session.get().
        :return: Response with status, content, headers, and response time.
        """
        self.connect()
        url = self._build_url(endpoint, params)
        start = perf_counter()
        resp = self.client.get(url, **kwargs)
        elapsed = perf_counter() - start
        return Response(
            status=resp.status_code,
            content=resp.content,
            headers=dict(resp.headers),
            response_time=elapsed,
        )

    def head(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """
        Issue a HEAD request to the specified endpoint.
        """
        self.connect()
        url = self._build_url(endpoint, params)
        start = perf_counter()
        resp = self.client.head(url, **kwargs)
        elapsed = perf_counter() - start
        return Response(
            status=resp.status_code,
            content=resp.content,
            headers=dict(resp.headers),
            response_time=elapsed,
        )

    def post(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """
        Issue a POST request to the specified endpoint.
        """
        self.connect()
        url = self._build_url(endpoint, params)
        start = perf_counter()
        resp = self.client.post(url, **kwargs)
        elapsed = perf_counter() - start
        return Response(
            status=resp.status_code,
            content=resp.content,
            headers=dict(resp.headers),
            response_time=elapsed,
        )

    def put(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """
        Issue a PUT request to the specified endpoint.
        """
        self.connect()
        url = self._build_url(endpoint, params)
        start = perf_counter()
        resp = self.client.put(url, **kwargs)
        elapsed = perf_counter() - start
        return Response(
            status=resp.status_code,
            content=resp.content,
            headers=dict(resp.headers),
            response_time=elapsed,
        )

    def patch(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """
        Issue a PATCH request to the specified endpoint.
        """
        self.connect()
        url = self._build_url(endpoint, params)
        start = perf_counter()
        resp = self.client.patch(url, **kwargs)
        elapsed = perf_counter() - start
        return Response(
            status=resp.status_code,
            content=resp.content,
            headers=dict(resp.headers),
            response_time=elapsed,
        )

    def delete(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """
        Issue a DELETE request to the specified endpoint.
        """
        self.connect()
        url = self._build_url(endpoint, params)
        start = perf_counter()
        resp = self.client.delete(url, **kwargs)
        elapsed = perf_counter() - start
        return Response(
            status=resp.status_code,
            content=resp.content,
            headers=dict(resp.headers),
            response_time=elapsed,
        )

    def options(
        self, endpoint: str, params: dict[str, Any] | None = None, **kwargs
    ) -> Response:
        """
        Issue a OPTIONS request to the specified endpoint.
        """
        self.connect()
        url = self._build_url(endpoint, params)
        start = perf_counter()
        resp = self.client.options(url, **kwargs)
        elapsed = perf_counter() - start
        return Response(
            status=resp.status_code,
            content=resp.content,
            headers=dict(resp.headers),
            response_time=elapsed,
        )
