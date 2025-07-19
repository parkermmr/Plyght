try:
    from neo4j import AsyncDriver, AsyncGraphDatabase
except ImportError:
    raise ImportError(
        "Neo4j functionality requires installation with the [neo4j] extra. "
        "See https://plyght.teampixl.info/install for details on installing extras."
    )

from async_property import async_property

from plyght.config.auto import get_kwargs
from plyght.config.clients.concurrent.async_client import AsyncClient
from plyght.config.clients.exceptions import ConnectionException, QueryException
from plyght.util.logging.logger import Logger


class AsyncNeo4jClient(AsyncClient):
    """
    Wrapper class for the Neo4j Python async client. Provides logging,
    exception handling, and can be auto-configured via Plyght.

    For more information on Plyght configurations see:
        https://plyght.teampixl.info/config/intro,
        https://plyght.teampixl.info/config/clients/concurrent/neo4j
    """

    def __init__(self, uri: str = None, auth: tuple[str, str] = None, **kwargs) -> None:
        """
        Initialize the AsyncNeo4jClient.
        :param uri: Bolt URI, e.g. "bolt://localhost:7687"
        :param auth: Tuple of (username, password)
        """
        super().__init__(**get_kwargs())
        self.logger = Logger(self.__class__.__name__)
        self._client: AsyncDriver | None = None

    @async_property
    async def client(self) -> AsyncDriver:
        """
        Explicitly returns client, opposed to implicity returning client
        through the constructor. In this case return GDBMS driver.

        :raises ConnectionException: If not connected.
        :returns AsyncDriver: Instance of client.
        """
        if not self._client:
            raise ConnectionException(
                404,
                "NoConnectionFound",
                "Async connection to Neo4j not yet established; call connect()."
            )
        return self._client

    @async_property
    async def status(self) -> bool:
        """
        Return a boolean based on the connection instantiation status of Neo4j.
        I.e. if client is connected return True else False.

        :returns bool: Boolean of connection state.
        """
        if not self._client:
            self.logger.warning("No active connection to Neo4j is established.")
            return False
        try:
            await self._client.verify_connectivity()
            return True
        except Exception as e:
            self.logger.warning(f"Connectivity check failed: {e}")
            return False

    @async_property
    async def host(self) -> str | None:
        """
        Return a string of URLs. E.g. "bolt+ssc://localhost:7687"

        :returns str: Host URLs or None if no hosts are configured.
        """
        uri = self._config.get("uri", "")
        if not uri:
            self.logger.warning("No URI configured for Neo4j client.")
            return None
        return uri

    async def connect(self) -> None:
        """
        Establish an async connection to Neo4j.
        """
        if self._client is not None:
            return
        self.logger.info(f"Connecting to Neo4j at {await self.host}")
        self._client = AsyncGraphDatabase.driver(**self._config)
        if not self._client:
            raise ConnectionException(
                500,
                "InvalidConfiguration",
                "Async connection to Neo4j cannot be established."
            )

    async def disconnect(self) -> None:
        """
        Close the async connection to Neo4j.
        """
        if not self._client:
            return
        await self._client.close()
        self._client = None

    async def execute_safe_query(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        """
        Transaction execution wrapper for Neo4j. Wraps connection in a session and upon
        failure automatically rolls back changes made to GDBMS. Adds an additional
        safeguard to generic query execution by paramaterizing a query str.

        :param query: A valid Neo4j paramaterized query string.
        :param params: A valid dictionary of query paramaters.

        :returns dict: Data dictionary response from Neo4j based on query result.
        """
        if not self._client:
            raise ConnectionException(
                404,
                "NoConnectionFound",
                "Async connection to Neo4j not yet established; call connect()."
            )
        async with self._client.session() as session:
            tx = await session.begin_transaction()
            try:
                result = await tx.run(query, params or {})
                records = await result.data()
                await tx.commit()
                return records
            except Exception as e:
                await tx.rollback()
                raise QueryException(error_type="REFUSED", info=f"Query failed: {e}")

    async def export_rdf(
        self, query: str, params: dict | None = None, format: str = "Turtle"
    ) -> list[dict]:
        """
        Generic exportation wrapper for n10s RDF formatted data.

        :param query: A valid Neo4j paramaterized query string.
        :param params: A valid dictionary of query paramaters.
        :param format: Neo4j RDF format to be exported. Defaults to 'Turtle'.

        :returns dict: Data dictionary response from Neo4j based on query result.
        """
        if not self._client:
            raise ConnectionException(
                404,
                "NoConnectionFound",
                "Async connection to Neo4j not yet established; call connect()."
            )
        cypher = "CALL n10s.rdf.export.cypher($query, $config)"
        return await self.execute_safe_query(
            cypher,
            {
                "cypherQuery": query,
                "config": {"format": format, "cypherParams": params},
            },
        )

    @async_property
    async def labels(self) -> list[dict]:
        """
        Retrieve all labels in the database.
        """
        query = "CALL db.labels() YIELD label RETURN label AS labels"
        return await self.execute_safe_query(query)
