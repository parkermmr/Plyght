try:
    from opensearchpy import AsyncOpenSearch
except ImportError:
    raise ImportError(
        "Opensearch functionality requires installation with the [opensearch] extra. "
        "See https://plyght.teampixl.info/install for details on installing extras."
    )

from async_property import async_property

from plyght.config.auto import get_kwargs
from plyght.config.clients.concurrent.async_client import AsyncClient
from plyght.config.clients.exceptions import ConnectionException
from plyght.util.logging.logger import Logger


class AsyncOpensearchClient(AsyncClient):
    """
    Async wrapper for the OpenSearch Python client. Provides logging,
    exception handling, and can be decorated for automatic configuration
    via Plyght.

    For more information on Plyght configurations see:
        https://plyght.teampixl.info/config/intro,
        https://plyght.teampixl.info/config/clients/concurrent/opensearch
    """

    def __init__(self, hosts: list[dict] = None, **kwargs) -> None:
        """
        Initialize the AsyncOpensearchClient.

        :param hosts: List of host dicts for OpenSearch.
        """
        super().__init__(**get_kwargs())
        self.logger = Logger(self.__class__.__name__)
        self._client: AsyncOpenSearch | None = None

    @async_property
    async def client(self) -> AsyncOpenSearch:
        """
        Explicitly returns client, opposed to implicitly returning client
        through the constructor.

        :returns AsyncOpenSearch: Instance of client.
        :raises ConnectionException: If not yet connected.
        """
        if not self._client:
            raise ConnectionException(
                404,
                "NoConnectionFound",
                "Async connection to Opensearch not yet established; "
                "call AsyncOpensearchClient.connect()."
            )
        return self._client

    @async_property
    async def status(self) -> bool:
        """
        Return a boolean based on the connection instantiation status of Opensearch.
        I.e. if client is connected return True else False.

        :returns bool: Boolean of connection state.
        """
        if not self._client:
            self.logger.warning("No active connection to Opensearch is established.")
            return False
        try:
            alive = await self._client.ping()
            if not alive:
                self.logger.warning("Opensearch ping returned False.")
            return alive
        except Exception as e:
            self.logger.warning(f"Opensearch ping failed: {e}")
            return False

    @async_property
    async def host(self) -> str | None:
        """
        Return a string of host URLs. E.g. "https://localhost:9200"
        or "http://localhost:9200, http://localhost:9201".

        :returns str: String of host URLs or None if no hosts are configured.
        """
        ssl = self._config.get("use_ssl", False)
        scheme = "https" if ssl else "http"
        hosts_data = self._config.get("hosts", [])
        if not hosts_data:
            self.logger.warning("No hosts found for Opensearch client.")
            return None
        parts = []
        for h in hosts_data:
            prefix = h.get("url_prefix", "").strip("/")
            net = f"{h['host']}:{h['port']}"
            parts.append(f"{scheme}://{net}/{prefix}" if prefix else f"{scheme}://{net}")
        return ", ".join(parts)

    async def connect(self) -> None:
        """
        Establish the AsyncOpenSearch client using configuration.
        Subsequent calls are no-ops if already connected.

        :raises ConnectionException: If ping fails.
        """
        if self._client:
            return
        self.logger.info(f"Connecting to Opensearch at {await self.host}")
        self._client = AsyncOpenSearch(**self._config)
        if not await self._client.ping():
            raise ConnectionException(
                500,
                "InvalidConfiguration",
                "Async connection to Opensearch cannot be established; "
                "invalid config or unreachable host."
            )

    async def disconnect(self) -> None:
        """
        Close and clear the AsyncOpenSearch client connection.
        """
        if not self._client:
            return
        await self._client.close()
        self._client = None