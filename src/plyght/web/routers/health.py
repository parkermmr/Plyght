"""
Liveness and readiness, unversioned and unauthenticated: orchestrators
probe these before any proxy or auth exists.
"""

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness: the process answers."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> dict:
    """
    Readiness: dependencies are up. A service can register an async
    ready_check on app.state returning a dict of dependency -> bool;
    any False dependency turns the answer into a 503-shaped body.
    """
    check = getattr(request.app.state, "ready_check", None)
    dependencies = await check() if check else {}
    status = "ready" if all(dependencies.values()) else "degraded"
    return {
        "status": status,
        "service": request.app.state.settings.name,
        **({"dependencies": dependencies} if dependencies else {}),
    }
