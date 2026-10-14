"""
SQLite behind the Connector protocol over the stdlib sqlite3 module.
No extra dependency: sqlite3 is synchronous, so every call runs in a
worker thread like the s3 connector.

    async with SqliteConnector(path="./data/app.db") as db:
        await db.execute("create table if not exists events (id text)")
        await db.execute("insert into events values (?)", ("1",))
        rows = await db.fetch("select * from events")
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Any, Sequence

from plyght.connector import Connector
from plyght.settings import ConnectorSettings, connector_config


class SqliteSettings(ConnectorSettings):
    """Database location; PLYGHT_SQLITE_* in the environment."""

    model_config = connector_config("sqlite")

    path: str = "./sqlite.db"
    timeout: float = 30.0


class SqliteConnector(Connector):
    """
    One connection with dict-like rows and autocommit, mirroring the
    postgres connector's execute/fetch surface so code can move
    between the two. The raw sqlite3.Connection stays reachable via
    .client for anything not surfaced here.
    """

    Settings = SqliteSettings

    async def connect(self) -> None:
        """Open the database, creating parent directories as needed."""

        def _open() -> sqlite3.Connection:
            location = Path(self.settings.path)
            location.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(
                location,
                timeout=self.settings.timeout,
                isolation_level=None,
                check_same_thread=False,
            )
            connection.row_factory = sqlite3.Row
            return connection

        self._client = await asyncio.to_thread(_open)
        self.log.debug("connected", extra={"path": self.settings.path})

    async def aclose(self) -> None:
        """Close the connection; safe when never connected."""
        if self._client is not None:
            await asyncio.to_thread(self._client.close)
            self._client = None

    async def healthy(self) -> bool:
        """One trivial statement against the open database."""
        try:
            await asyncio.to_thread(self.client.execute, "select 1")
            return True
        except Exception:
            return False

    async def execute(self, statement: str, parameters: Sequence = ()) -> None:
        """Run one statement (DDL or write)."""
        await asyncio.to_thread(self.client.execute, statement, parameters)

    async def executemany(
        self, statement: str, rows: Sequence[Sequence]
    ) -> None:
        """Run one statement for every parameter row."""
        await asyncio.to_thread(self.client.executemany, statement, rows)

    async def fetch(
        self, query: str, parameters: Sequence = ()
    ) -> list[dict[str, Any]]:
        """Run one query and return every row as a dict."""

        def _fetch() -> list[dict[str, Any]]:
            cursor = self.client.execute(query, parameters)
            return [dict(row) for row in cursor.fetchall()]

        return await asyncio.to_thread(_fetch)
