"""
Every connector shares one lifecycle: settings from PLYGHT_<KIND>_*
variables, resources/.env or keyword overrides, then connect, healthy,
and aclose (or async with).

Point the variables at your services and run it. Kinds whose client
library is not installed or whose service does not answer are
reported and skipped:

    PLYGHT_KAFKA_BOOTSTRAP=localhost:9092 python connectors.py
"""

import asyncio

from plyght import configure, get_logger
from plyght.connectors.registry import available, connector

log = get_logger("connectors")


async def probe(kind: str) -> None:
    """Connect to one kind, report whether it answers, and close."""
    try:
        async with asyncio.timeout(5):
            async with connector(kind)() as client:
                log.info("probed", extra={"kind": kind, "healthy": await client.healthy()})
    except Exception as error:
        log.warning("unreachable", extra={"kind": kind, "error": repr(error)})


async def main() -> None:
    """Probe every kind that loads in this environment."""
    configure()
    for entry in available():
        if entry["loads"]:
            await probe(entry["kind"])
        else:
            log.info("skipped", extra={"kind": entry["kind"], "reason": entry["reason"]})


if __name__ == "__main__":
    asyncio.run(main())
