"""One-shot restore of known local accounts into the active DB.

Applies hashed credentials from ``account_bootstrap_data`` exactly once
(marker row in ``app_meta``). Never logs password hashes. Safe to leave
in place after the marker is written — subsequent starts are no-ops.
"""

from __future__ import annotations

import logging

from db import get_db, row_value, table_columns

logger = logging.getLogger(__name__)


def _ensure_app_meta(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )


def apply_local_account_bootstrap() -> dict:
    """Upsert bootstrap users once. Returns a small status dict (no secrets)."""
    try:
        from account_bootstrap_data import BOOTSTRAP_KEY, BOOTSTRAP_USERS
    except Exception as exc:
        return {"applied": False, "reason": f"payload_unavailable:{type(exc).__name__}"}

    conn = get_db()
    try:
        _ensure_app_meta(conn)
        conn.commit()

        done = conn.execute(
            "SELECT value FROM app_meta WHERE key = ?",
            (BOOTSTRAP_KEY,),
        ).fetchone()
        if done:
            return {"applied": False, "reason": "already_applied"}

        cols = table_columns(conn, "users")
        updated = 0
        inserted = 0
        email_skipped = 0

        for entry in BOOTSTRAP_USERS:
            username = (entry.get("username") or "").strip()
            password = entry.get("password")
            if not username or not password:
                continue
            provider = (entry.get("provider") or "local") or "local"
            provider_user_id = entry.get("provider_user_id")
            email = entry.get("email")

            existing = conn.execute(
                "SELECT id FROM users WHERE LOWER(username) = LOWER(?)",
                (username,),
            ).fetchone()

            # Avoid stealing another account's email.
            email_to_set = email
            if email and str(email).strip():
                owner = conn.execute(
                    """
                    SELECT username FROM users
                    WHERE email IS NOT NULL
                      AND TRIM(email) != ''
                      AND LOWER(email) = LOWER(?)
                    """,
                    (email,),
                ).fetchone()
                if owner:
                    owner_name = row_value(owner, "username")
                    if owner_name and owner_name.lower() != username.lower():
                        email_to_set = None
                        email_skipped += 1

            if existing:
                if "provider" in cols and "email" in cols:
                    conn.execute(
                        """
                        UPDATE users
                        SET password = ?,
                            provider = ?,
                            provider_user_id = ?,
                            email = COALESCE(?, email)
                        WHERE LOWER(username) = LOWER(?)
                        """,
                        (
                            password,
                            provider,
                            provider_user_id,
                            email_to_set,
                            username,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE users
                        SET password = ?
                        WHERE LOWER(username) = LOWER(?)
                        """,
                        (password, username),
                    )
                updated += 1
            else:
                if "provider" in cols and "email" in cols:
                    conn.execute(
                        """
                        INSERT INTO users (
                            username, password, provider, provider_user_id, email
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            username,
                            password,
                            provider,
                            provider_user_id,
                            email_to_set,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO users (username, password)
                        VALUES (?, ?)
                        """,
                        (username, password),
                    )
                inserted += 1

        conn.execute(
            """
            INSERT INTO app_meta (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (BOOTSTRAP_KEY, "done"),
        )
        conn.commit()
        status = {
            "applied": True,
            "updated": updated,
            "inserted": inserted,
            "email_skipped": email_skipped,
        }
        logger.info(
            "account bootstrap applied updated=%s inserted=%s email_skipped=%s",
            updated,
            inserted,
            email_skipped,
        )
        return status
    finally:
        conn.close()
