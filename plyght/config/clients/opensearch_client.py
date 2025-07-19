"""
Provides an OpenSearch client wrapper that integrates Plyght logging and
exception handling. The class is intended for use as a base class where
configuration can be injected via decorators. It includes explicit
methods for connecting and disconnecting, along with property-based
status checking and host retrieval.
"""

try:
    from opensearchpy import OpenSearch
except ImportError:
    raise ImportError(
        "Opensearch functionality requires installation with the [opensearch] extra. "
        "See https://plyght.teampixl.info/install for details on installing extras."
    )

from plyght.config.auto import get_kwargs
from plyght.config.clients.client import Client
from plyght.config.clients.exceptions import ConnectionException
from plyght.util.logging.logger import Logger


class OpensearchClient(Client):
    """
    Wrapper class for the OpenSearch Python client. Provides additional logging
    and exception handling and can be decorated for automatic configuration
    using Plyght's configuration system.

    For more information on Plyght configurations see:
        https://plyght.teampixl.info/config/intro,
        https://plyght.teampixl.info/config/clients/opensearch
    """

    def __init__(self, hosts: list[dict] = None, **kwargs) -> None:
        """
        Initialize the OpensearchClient, optionally with a list of host dictionaries.
        Other keyword arguments are merged with existing configuration if present.
        """
        super().__init__(**get_kwargs())
        self.logger = Logger(self.__class__.__name__)
        self._client = None

    @property
    def client(self) -> OpenSearch:
        """
        Explicitly returns client, opposed to implicity returning client
        through the constructor.

        :return: OpenSearch instance of client.
        """
        if not self._client:
            raise ConnectionException(
                404,
                "NoConnectionFound",
                "Connection to Opensearch not yet established, try"
                " OpensearchClient.connect().",
            )
        return self._client

    @property
    def status(self) -> bool:
        """
        Return a boolean based on the connection instantiation status of Opensearch.
        I.e. if client is connected return True else False.

        :return: Boolean of connection state.
        """
        if not self._client:
            self.logger.warning("No active connection to Opensearch is established.")
            return False

        return True

    @property
    def host(self) -> str | None:
        """
        Return a string of host URLs. E.g. "https://localhost:9200"
        or "http://localhost:9200, http://localhost:9201".

        :return: String of host URLs or None if no hosts are configured.
        """
        ssl = self._config.get("use_ssl", False)
        scheme = "https" if ssl else "http"
        hosts_data = self._config.get("hosts", [])

        if not hosts_data:
            self.logger.warning("No hosts found for Opensearch client.")
            return None

        results = []
        for item in hosts_data:
            url_prefix = item.get("url_prefix", "")
            if url_prefix:
                results.append(f"{scheme}://{item['host']}:{item['port']}/{url_prefix}")
            else:
                results.append(f"{scheme}://{item['host']}:{item['port']}")

        return ", ".join(results)

    def connect(self) -> None:
        """
        Explicit connection method for Opensearch rather than implicitly through the
        constructor itself.
        """
        if self._client is not None:
            return

        self.logger.info(f"Attempting to establish connection to clients: {self.host}")

        self._client = OpenSearch(**self._config)

        instance = self._client.ping()
        if not instance:
            raise ConnectionException(
                500,
                "InvalidConfiguration",
                "Connection to Opensearch client cannot be established"
                " caused by either an invalid configuration or unreachable host.",
            )

    def disconnect(self) -> None:
        """
        Terminate the connection to OpenSearch.
        """
        self._client = None
