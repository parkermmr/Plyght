try:
    from neo4j import Driver, GraphDatabase
except ImportError:
    raise ImportError(
        "Neo4j functionality requires installation with the [neo4j] extra. "
        "See https://plyght.teampixl.info/install for details on installing extras."
    )


from plyght.config.auto import get_kwargs
from plyght.config.clients.client import Client
from plyght.config.clients.exceptions import ConnectionException, QueryException
from plyght.util.logging.logger import Logger


class Neo4jClient(Client):
    """
    Wrapper class for the Neo4j Python client. Provides additional logging
    and exception handling and can be decorated for automatic configuration
    using Plyght's configuration system.

    For more information on Plyght configurations see:
        https://plyght.teampixl.info/config/intro,
        https://plyght.teampixl.info/config/clients/neo4j
    """

    def __init__(self, uri: str = None, auth: tuple[str, str] = None, **kwargs) -> None:
        """
        Initialize the Neo4jClient, optionally with a uri and auth tuple.
        Other keyword arguments are merged with existing configuration if present.
        """
        super().__init__(**get_kwargs())
        self.logger = Logger(self.__class__.__name__)
        self._client = None

    @property
    def client(self) -> Driver:
        """
        Explicitly returns client, opposed to implicity returning client
        through the constructor. In this case return GDBMS driver.

        :raises ConnectionException: If not connected.
        :returns Driver: Instance of client.
        """
        if not self._client:
            raise ConnectionException(
                404,
                "NoConnectionFound",
                "Connection to Neo4j not yet established, try"
                " Neo4jClient.connect().",
            )
        return self._client

    @property
    def status(self) -> bool:
        """
        Return a boolean based on the connection instantiation status of Neo4j.
        I.e. if client is connected return True else False.

        :returns bool: Boolean of connection state.
        """
        if not self._client:
            self.logger.warning("No active connection to Neo4j is established.")
            return False
        try:
            self._client.verify_connectivity()
            return True
        except Exception as e:
            self.logger.warning(f"Connectivity check failed: {e}")
            return False

    @property
    def host(self) -> str | None:
        """
        Return a string of URLs. E.g. "bolt+ssc://localhost:7687"

        :returns str: Host URLs or None if no hosts are configured.
        """
        uri = self._config.get("uri", "")

        if not uri:
            self.logger.warning("No hosts found for Neo4j client.")
            return None

        return uri

    def connect(self) -> None:
        """
        Explicit connection method for Neo4j rather than implicitly through the
        constructor itself.
        """
        if self._client is not None:
            return

        self.logger.info(f"Attempting to establish connection to clients: {self.host}")

        self._client = GraphDatabase.driver(**self._config)

        instance = self._client
        if not instance:
            raise ConnectionException(
                500,
                "InvalidConfiguration",
                "Connection to Neo4j client cannot be established"
                " caused by either an invalid configuration or unreachable host.",
            )

    def disconnect(self) -> None:
        """
        Terminate the connection to Neo4j.
        """
        if not self._client:
            return
        self._client.close()
        self._client = None

    def execute_safe_query(self, query: str, params: dict | None = None) -> dict:
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
                "Connection to Neo4j not yet established, try"
                " Neo4jClient.connect().",
            )

        with self._client.session() as session:
            tx = session.begin_transaction()
            try:
                result = tx.run(query, params)
                records = result.data()
                tx.commit()
                return records
            except Exception as e:
                tx.rollback()
                raise QueryException(
                    error_type="REFUSED", info=f"Query failed: {str(e)}"
                )

    def export_rdf(
        self, query: str, params: dict | None = None, format: str = "Turtle"
    ):
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
                "Connection to Neo4j not yet established, try"
                " Neo4jClient.connect().",
            )
        cypher = "CALL n10s.rdf.export.cypher($query, $config)"
        result = self.execute_safe_query(
            cypher,
            {
                "cypherQuery": query,
                "config": {"format": format, "cypherParams": params},
            },
        )
        return result

    @property
    def labels(self):
        """
        Retrieve all labels in the database.
        """
        query = "CALL db.labels() YIELD label RETURN label as labels"
        result = self.execute_safe_query(query=query)
        return result
