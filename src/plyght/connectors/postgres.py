"""
Postgres behind the Connector protocol via psycopg 3's async
connection, plus the two helpers that cover most needs.

    async with PostgresConnector() as pg:
        await pg.execute("insert into events (id) values (%s)", (1,))
        rows = await pg.fetch("select * from events")

TLS follows libpq: sslmode unset keeps libpq's own default and the
connection string exactly as before; require encrypts, verify-ca
also checks the server against sslrootcert, verify-full also checks
its hostname. sslcert/sslkey present a client certificate.
"""

from typing import Any, Literal, Self, Sequence

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from pydantic import Field, field_validator, model_validator

from plyght.connector import Connector
from plyght.settings import ConnectorSettings, connector_config


Mode = Literal["disable", "require", "verify-ca", "verify-full"]


def quote(value: str) -> str:
    """A libpq connection string value, quoted when it needs to be."""
    if value and not any(character in value for character in " '\\"):
        return value
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


class PostgresSettings(ConnectorSettings):
    """Connection settings; PLYGHT_POSTGRES_* in the environment."""

    model_config = connector_config("postgres")

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = Field(default="postgres", repr=False)
    database: str = "postgres"
    sslmode: Mode | None = None
    sslrootcert: str | None = None
    sslcert: str | None = None
    sslkey: str | None = None

    @field_validator("sslmode", mode="before")
    @classmethod
    def normalize(cls, value: Any) -> Any:
        """Accept any case; an empty value means unset."""
        if isinstance(value, str):
            return value.strip().lower() or None
        return value

    @model_validator(mode="after")
    def check(self) -> Self:
        """Refuse certificate settings the sslmode would ignore."""
        files = [self.sslrootcert, self.sslcert, self.sslkey]
        if any(files) and self.sslmode in (None, "disable"):
            raise ValueError(
                f"{self.variable('sslrootcert')}/_SSLCERT/_SSLKEY are set but "
                f"{self.variable('sslmode')} is {self.sslmode or 'unset'}; "
                "use require, verify-ca or verify-full"
            )
        if bool(self.sslcert) != bool(self.sslkey):
            raise ValueError(
                f"{self.variable('sslcert')} and {self.variable('sslkey')} "
                "go together"
            )
        if self.sslrootcert != "system":
            self.require_file("sslrootcert")
        self.require_file("sslcert", "sslkey")
        return self

    def conninfo(self) -> str:
        """The libpq connection string these settings describe."""
        return " ".join(
            f"{name}={quote(str(value))}"
            for name, value in [
                ("host", self.host),
                ("port", self.port),
                ("user", self.user),
                ("password", self.password),
                ("dbname", self.database),
                ("sslmode", self.sslmode),
                ("sslrootcert", self.sslrootcert),
                ("sslcert", self.sslcert),
                ("sslkey", self.sslkey),
            ]
            if value
        )


class PostgresConnector(Connector):
    """
    One async connection with dict rows and autocommit. For
    transactions or pools, reach through .client (a psycopg
    AsyncConnection) - the wrapper does not hide it.
    """

    Settings = PostgresSettings

    async def connect(self) -> None:
        """Open the connection (autocommit, dict rows)."""
        self._client = await AsyncConnection.connect(
            self.settings.conninfo(), autocommit=True, row_factory=dict_row
        )
        self.log.debug(
            "connected",
            extra={"host": self.settings.host, "database": self.settings.database},
        )

    async def aclose(self) -> None:
        """Close the connection; safe when never connected."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def healthy(self) -> bool:
        """SELECT 1 round trip."""
        try:
            cursor = await self.client.execute("select 1")
            return (await cursor.fetchone()) is not None
        except Exception:
            return False

    async def execute(self, query: str, params: Sequence | None = None) -> int:
        """Run a statement; returns the affected row count."""
        cursor = await self.client.execute(query, params)
        return cursor.rowcount

    async def fetch(self, query: str, params: Sequence | None = None) -> list[dict[str, Any]]:
        """Run a query; returns every row as a dict."""
        cursor = await self.client.execute(query, params)
        return await cursor.fetchall()
