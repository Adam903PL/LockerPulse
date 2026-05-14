import logging
import os
import asyncio
from typing import Any

from locker_pulse_api.config import Settings

logger = logging.getLogger(__name__)


try:
    from prisma import Prisma
except Exception:  # pragma: no cover - depends on generated client availability
    Prisma = None  # type: ignore[assignment]


async def connect_database(settings: Settings) -> Any | None:
    if not settings.database_url:
        logger.info("DATABASE_URL is not configured; persistence is disabled.")
        return None

    os.environ.setdefault("DATABASE_URL", settings.database_url)

    if Prisma is None:
        logger.warning("Prisma client is not generated; persistence is disabled.")
        return None

    try:
        db = Prisma()
        await asyncio.wait_for(db.connect(), timeout=10)
        logger.info("Connected to Postgres through Prisma.")
        return db
    except TimeoutError:  # pragma: no cover - depends on local DB availability
        logger.warning("Database connection timed out; continuing without persistence.")
        return None
    except Exception as exc:  # pragma: no cover - defensive startup behavior
        logger.warning("Database connection failed; continuing without persistence: %s", exc)
        return None


async def disconnect_database(db: Any | None) -> None:
    if db is not None:
        await db.disconnect()
