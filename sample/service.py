"""
A small notes service on the plyght.web spine, backed by sqlite.

Needs plyght[web]. Run it from this directory, then open /docs:

    python service.py
    NOTES_AUTH_ENABLED=true NOTES_AUTH_PROXY_SECRET=s3cret python service.py
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel

from plyght import get_logger
from plyght.connectors import SqliteConnector
from plyght.web import Identity, WebSettings, create_app, require_groups, web_config

log = get_logger("notes")


class Settings(WebSettings):
    """NOTES_ prefixed settings, resources/.env aware."""

    model_config = web_config("NOTES")

    name: str = "notes"
    version: str = "1.0.0"
    port: int = 8080
    database: str = "./data/notes.db"


class Note(BaseModel):
    """A note as the api accepts it."""

    text: str


settings = Settings()
database = SqliteConnector(path=settings.database)
router = APIRouter(tags=["notes"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the database for the life of the process."""
    await database.connect()
    await database.execute("create table if not exists notes (author text, text text)")

    async def ready() -> dict:
        return {"database": await database.healthy()}

    app.state.ready_check = ready
    yield
    await database.aclose()


@router.get("/notes")
async def notes() -> list[dict]:
    """Every note, oldest first."""
    return await database.fetch("select rowid as id, author, text from notes")


@router.post("/notes", status_code=201)
async def add(note: Note, identity: Identity = Depends(require_groups("writers"))) -> dict:
    """Add a note; with auth on, only the writers group may."""
    author = identity.user or "anonymous"
    await database.execute("insert into notes values (?, ?)", (author, note.text))
    log.info("added", extra={"author": author})
    return {"author": author, "text": note.text}


app = create_app(settings, lifespan=lifespan)
app.include_router(router, prefix=settings.api_prefix)


if __name__ == "__main__":
    uvicorn.run(app, port=settings.port, log_config=None)
