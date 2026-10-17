"""
db.py — Database connection pool lifecycle and raw query helpers.
All asyncpg pool management is centralized here so no endpoint
imports asyncpg directly.
"""
import logging
from typing import Optional

import asyncpg

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Module-level pool singleton, initialized at startup
db_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> None:
    """Create the asyncpg connection pool. Called on FastAPI startup."""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
        logger.info("Database pool created (min=5, max=20).")
    except Exception as exc:
        logger.error(f"Failed to create database pool: {exc}")


async def close_pool() -> None:
    """Gracefully close the pool. Called on FastAPI shutdown."""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed.")


def get_pool() -> Optional[asyncpg.Pool]:
    """
    Returns the active pool, or None if the database is unavailable.
    Callers should always guard against None to keep endpoints resilient.
    """
    return db_pool
