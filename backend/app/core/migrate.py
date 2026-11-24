"""Schema migrations at startup.

Databases created before Alembic existed already contain every table, so they are
stamped at the baseline revision instead of being recreated.
"""
from __future__ import annotations

import logging

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import BACKEND_DIR, settings

log = logging.getLogger("app.migrate")

BASELINE_REVISION = "ab7b0bf1f8bf"


def _sync_url() -> str:
    return settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg")


def upgrade_database() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", _sync_url())

    engine = create_engine(_sync_url())
    try:
        inspector = inspect(engine)
        if not inspector.has_table("alembic_version") and inspector.has_table("users"):
            log.info("existing database found: stamping baseline %s", BASELINE_REVISION)
            command.stamp(cfg, BASELINE_REVISION)
    finally:
        engine.dispose()

    command.upgrade(cfg, "head")
