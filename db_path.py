"""Single source of truth for the local SQLite database file path.

Used only when DATABASE_URL is unset (local development fallback).
Production on Render should set DATABASE_URL for PostgreSQL instead.
"""

from __future__ import annotations

import os


def resolve_database_path(fallback_dir: str | None = None) -> str:
    configured = os.environ.get("DATABASE_PATH")
    if configured:
        return os.path.abspath(configured)
    if not fallback_dir:
        fallback_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(fallback_dir, "users.db"))
