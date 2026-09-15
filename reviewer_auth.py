"""Server-side reviewer / admin permissions (username-based, no email required)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from database import COURSE_LANGUAGES
from db import ensure_column, get_db, row_to_dict, row_value

ROLE_STUDENT = "student"
ROLE_REVIEWER = "reviewer"
ROLE_ADMIN = "admin"
ROLES = (ROLE_STUDENT, ROLE_REVIEWER, ROLE_ADMIN)

KIND_ACADEMIC = "academic"
KIND_COMMUNITY = "community"
REVIEWER_KINDS = (KIND_ACADEMIC, KIND_COMMUNITY)

KIND_LABELS = {
    KIND_ACADEMIC: "Academic Reviewer",
    KIND_COMMUNITY: "Community Reviewer",
}

LANGUAGE_LABELS = {
    "mah-meri": "Mah Meri",
    "iban": "Iban",
    "bidayuh": "Bidayuh",
    "kadazan-dusun": "Kadazan-Dusun",
}

SCOPE_ACTIVE = "active"
SCOPE_REVOKED = "revoked"

DONE_VOCAB_STATUSES = frozenset({"academically_reviewed", "reviewed"})
PENDING_VOCAB_STATUSES = frozenset(
    {
        "needs_verification",
        "needs_revision",
        "academic_review_pending",
        "community_review_pending",
        "source_derived",
        "technically_corrected",
    }
)
VOCAB_MUTATION_STATUSES = frozenset(
    {
        "needs_verification",
        "needs_revision",
        "academic_review_pending",
        "community_review_pending",
        "academically_reviewed",
        "reviewed",
        "source_derived",
        "technically_corrected",
    }
)


def admin_usernames_from_env() -> set[str]:
    raw = (os.environ.get("ADMIN_USERNAMES") or "").strip()
    if not raw:
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def ensure_reviewer_schema(conn=None) -> None:
    own = conn is None
    if own:
        conn = get_db()
    ensure_column(conn, "users", "role", f"TEXT DEFAULT '{ROLE_STUDENT}'")
    conn.execute(
        f"""
        UPDATE users
        SET role = '{ROLE_STUDENT}'
        WHERE role IS NULL OR TRIM(role) = ''
        """
    )
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reviewer_language_scopes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            language TEXT NOT NULL,
            reviewer_kind TEXT NOT NULL,
            status TEXT NOT NULL,
            granted_by INTEGER,
            granted_at TEXT,
            revoked_by INTEGER,
            revoked_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_reviewer_scopes_user
            ON reviewer_language_scopes (user_id, status);
        CREATE INDEX IF NOT EXISTS idx_reviewer_scopes_lang
            ON reviewer_language_scopes (language, status);
        """
    )
    _apply_env_admins(conn)
    if own:
        conn.commit()
        conn.close()


def _apply_env_admins(conn) -> None:
    names = admin_usernames_from_env()
    if not names:
        return
    for username in names:
        conn.execute(
            """
            UPDATE users
            SET role = ?
            WHERE LOWER(username) = ?
            """,
            (ROLE_ADMIN, username),
        )


def apply_env_admin_for_user(user_id: int, username: str | None) -> None:
    if not username or username.strip().lower() not in admin_usernames_from_env():
        return
    conn = get_db()
    try:
        ensure_reviewer_schema(conn)
        conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (ROLE_ADMIN, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def normalize_role(value: Any) -> str:
    role = (value or ROLE_STUDENT).strip().lower()
    if role in ROLES:
        return role
    return ROLE_STUDENT


def normalize_kind(value: Any) -> str | None:
    kind = (value or "").strip().lower()
    if kind in {"academic", "academic_reviewer", "academically"}:
        return KIND_ACADEMIC
    if kind in {"community", "community_reviewer"}:
        return KIND_COMMUNITY
    return None


def normalize_vocab_status(status: str) -> str:
    raw = (status or "").strip()
    if raw == "reviewed":
        return "academically_reviewed"
    return raw


def get_user_access(user_id: int | None) -> dict[str, Any]:
    empty = {
        "user_id": user_id,
        "username": None,
        "role": ROLE_STUDENT,
        "scopes": [],
        "active_languages": set(),
        "kind_by_language": {},
        "is_admin": False,
        "is_reviewer": False,
        "can_edit_any": False,
    }
    if not user_id:
        return empty
    conn = get_db()
    try:
        ensure_reviewer_schema(conn)
        user = conn.execute(
            "SELECT id, username, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not user:
            return empty
        username = row_value(user, "username")
        role = normalize_role(row_value(user, "role"))
        if (username or "").strip().lower() in admin_usernames_from_env():
            role = ROLE_ADMIN
        scopes = [
            row_to_dict(r)
            for r in conn.execute(
                """
                SELECT id, user_id, username, language, reviewer_kind, status,
                       granted_at, revoked_at
                FROM reviewer_language_scopes
                WHERE user_id = ?
                ORDER BY language, reviewer_kind, id
                """,
                (user_id,),
            ).fetchall()
        ]
        active = [s for s in scopes if s.get("status") == SCOPE_ACTIVE]
        languages = {s.get("language") for s in active if s.get("language")}
        kind_by_language: dict[str, str] = {}
        for scope in active:
            lang = scope.get("language")
            kind = scope.get("reviewer_kind")
            if not lang or not kind:
                continue
            if lang not in kind_by_language or kind == KIND_ACADEMIC:
                kind_by_language[lang] = kind
        is_admin = role == ROLE_ADMIN
        is_reviewer = is_admin or role == ROLE_REVIEWER or bool(active)
        return {
            "user_id": user_id,
            "username": username,
            "role": ROLE_ADMIN if is_admin else (ROLE_REVIEWER if active else role),
            "scopes": scopes,
            "active_languages": languages if not is_admin else set(COURSE_LANGUAGES),
            "kind_by_language": kind_by_language,
            "is_admin": is_admin,
            "is_reviewer": is_reviewer,
            "can_edit_any": is_admin or bool(active),
        }
    finally:
        conn.close()


def can_mutate_language(access: dict[str, Any], lang_key: str) -> bool:
    if access.get("is_admin"):
        return True
    return lang_key in (access.get("active_languages") or set())


def reviewer_role_label_for_language(access: dict[str, Any], lang_key: str) -> str:
    if access.get("is_admin"):
        return ROLE_ADMIN
    return access.get("kind_by_language", {}).get(lang_key) or KIND_ACADEMIC


def find_user_by_username(username: str) -> dict[str, Any] | None:
    name = (username or "").strip()
    if not name:
        return None
    conn = get_db()
    try:
        ensure_reviewer_schema(conn)
        row = conn.execute(
            """
            SELECT id, username, role
            FROM users
            WHERE LOWER(username) = LOWER(?)
            """,
            (name,),
        ).fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def grant_reviewer_access(
    username: str,
    language: str,
    reviewer_kind: str,
    granted_by: int | None,
) -> dict[str, Any]:
    user = find_user_by_username(username)
    if not user:
        return {"ok": False, "error": "No account exists with that username."}
    if language not in COURSE_LANGUAGES:
        return {"ok": False, "error": "Choose a valid language."}
    kind = normalize_kind(reviewer_kind)
    if not kind:
        return {"ok": False, "error": "Choose Academic Reviewer or Community Reviewer."}
    if normalize_role(user.get("role")) == ROLE_ADMIN:
        return {
            "ok": False,
            "error": "That account is already an admin and can review every language.",
        }

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_db()
    try:
        ensure_reviewer_schema(conn)
        existing = conn.execute(
            """
            SELECT id, status FROM reviewer_language_scopes
            WHERE user_id = ? AND language = ? AND reviewer_kind = ?
            ORDER BY id DESC
            """,
            (user["id"], language, kind),
        ).fetchone()
        if existing and row_value(existing, "status") == SCOPE_ACTIVE:
            return {
                "ok": True,
                "message": "That username already has this reviewer access.",
            }
        if existing:
            conn.execute(
                """
                UPDATE reviewer_language_scopes
                SET status = ?, granted_by = ?, granted_at = ?,
                    revoked_by = NULL, revoked_at = NULL
                WHERE id = ?
                """,
                (SCOPE_ACTIVE, granted_by, now, row_value(existing, "id")),
            )
        else:
            conn.execute(
                """
                INSERT INTO reviewer_language_scopes
                    (user_id, username, language, reviewer_kind, status,
                     granted_by, granted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    user["username"],
                    language,
                    kind,
                    SCOPE_ACTIVE,
                    granted_by,
                    now,
                ),
            )
        conn.execute(
            "UPDATE users SET role = ? WHERE id = ? AND role != ?",
            (ROLE_REVIEWER, user["id"], ROLE_ADMIN),
        )
        conn.commit()
        return {"ok": True, "message": f"Granted {KIND_LABELS[kind]} access for {LANGUAGE_LABELS.get(language, language)} to {user['username']}."}
    finally:
        conn.close()


def revoke_reviewer_access(scope_id: int, revoked_by: int | None) -> dict[str, Any]:
    conn = get_db()
    try:
        ensure_reviewer_schema(conn)
        row = conn.execute(
            "SELECT * FROM reviewer_language_scopes WHERE id = ?",
            (scope_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "Reviewer grant not found."}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.execute(
            """
            UPDATE reviewer_language_scopes
            SET status = ?, revoked_by = ?, revoked_at = ?
            WHERE id = ?
            """,
            (SCOPE_REVOKED, revoked_by, now, scope_id),
        )
        user_id = row_value(row, "user_id")
        remaining = conn.execute(
            """
            SELECT COUNT(*) AS n FROM reviewer_language_scopes
            WHERE user_id = ? AND status = ?
            """,
            (user_id, SCOPE_ACTIVE),
        ).fetchone()
        count = int(row_value(remaining, "n", "count", index=0) or 0)
        if count == 0:
            conn.execute(
                "UPDATE users SET role = ? WHERE id = ? AND role = ?",
                (ROLE_STUDENT, user_id, ROLE_REVIEWER),
            )
        conn.commit()
        return {
            "ok": True,
            "message": f"Revoked reviewer access for {row_value(row, 'username')}.",
        }
    finally:
        conn.close()


def list_reviewer_grants() -> list[dict[str, Any]]:
    conn = get_db()
    try:
        ensure_reviewer_schema(conn)
        rows = conn.execute(
            """
            SELECT s.id, s.user_id, s.username, s.language, s.reviewer_kind,
                   s.status, s.granted_at, s.revoked_at, u.role AS user_role
            FROM reviewer_language_scopes s
            LEFT JOIN users u ON u.id = s.user_id
            ORDER BY s.status, LOWER(s.username), s.language
            """
        ).fetchall()
        out = []
        for row in rows:
            item = row_to_dict(row)
            item["kind_label"] = KIND_LABELS.get(
                item.get("reviewer_kind"), item.get("reviewer_kind")
            )
            item["language_label"] = LANGUAGE_LABELS.get(
                item.get("language"), item.get("language")
            )
            item["status_label"] = "Active" if item.get("status") == SCOPE_ACTIVE else "Revoked"
            out.append(item)
        return out
    finally:
        conn.close()
