"""Single source of truth for the SQLite database file path.

Both app.py and database.py must resolve the same absolute path:
- If DATABASE_PATH is set in the environment, use that (e.g. Render disk).
- Otherwise fall back to <project_root>/users.db for local development.
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
