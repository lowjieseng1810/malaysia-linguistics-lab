"""Private review invitations (magic links) for pre-launch academic/community review.

Tokens are stored hashed. The raw token is shown once at creation and is the
only anonymous credential; it never grants admin access.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from database import COURSE_LANGUAGES
from db import get_db, row_to_dict, row_value
from reviewer_auth import (
    KIND_ACADEMIC,
    KIND_COMMUNITY,
    KIND_LABELS,
    LANGUAGE_LABELS,
    normalize_kind,
)

INVITE_ACTIVE = "active"
INVITE_REVOKED = "revoked"
ACTOR_PRIVATE_LINK = "private_review_link"
SESSION_INVITE_ID = "review_invite_id"

ACADEMIC_VOCAB_STATUSES = frozenset(
    {
        "academic_review_pending",
        "needs_verification",
        "academically_reviewed",
        "needs_revision",
    }
)
COMMUNITY_VOCAB_STATUSES = frozenset(
    {
        "community_review_pending",
        "needs_verification",
        "community_reviewed",
        "needs_revision",
        "academic_review_pending",
    }
)
ACADEMIC_SECTION_STATUSES = frozenset(
    {
        "academic_review_pending",
        "academically_reviewed",
        "needs_revision",
    }
)
COMMUNITY_SECTION_STATUSES = frozenset(
    {
        "community_review_pending",
        "community_reviewed",
        "needs_revision",
        "academic_review_pending",
    }
)

ACADEMIC_VOCAB_CHOICES = (
    ("needs_verification", "Needs verification"),
    ("academic_review_pending", "Review pending"),
    ("academically_reviewed", "Academically reviewed"),
    ("needs_revision", "Needs revision"),
)
COMMUNITY_VOCAB_CHOICES = (
    ("needs_verification", "Needs verification"),
    ("community_review_pending", "Review pending"),
    ("community_reviewed", "Community reviewed"),
    ("needs_revision", "Needs revision"),
)
ACADEMIC_SECTION_CHOICES = (
    ("academic_review_pending", "Review pending"),
    ("academically_reviewed", "Academically reviewed"),
    ("needs_revision", "Needs revision"),
)
COMMUNITY_SECTION_CHOICES = (
    ("community_review_pending", "Review pending"),
    ("community_reviewed", "Community reviewed"),
    ("needs_revision", "Needs revision"),
)


def hash_invite_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def ensure_invite_schema(conn=None) -> None:
    own = conn is None
    if own:
        conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS review_invitations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT NOT NULL,
            language TEXT NOT NULL,
            reviewer_kind TEXT NOT NULL,
            status TEXT NOT NULL,
            label TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_by INTEGER,
            revoked_at TEXT,
            last_used_at TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_review_invites_token_hash
            ON review_invitations (token_hash);
        CREATE INDEX IF NOT EXISTS idx_review_invites_status
            ON review_invitations (status, language);
        """
    )
    if own:
        conn.commit()
        conn.close()


def invite_public_status(row: dict[str, Any]) -> str:
    status = (row.get("status") or "").strip()
    if status == INVITE_REVOKED:
        return "revoked"
    expires = _parse_iso(row.get("expires_at"))
    if expires and expires <= _now():
        return "expired"
    return "active"


def _decorate(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["kind_label"] = KIND_LABELS.get(item.get("reviewer_kind"), item.get("reviewer_kind"))
    item["language_label"] = LANGUAGE_LABELS.get(item.get("language"), item.get("language"))
    item["public_status"] = invite_public_status(item)
    item["status_label"] = item["public_status"].title()
    return item


def create_review_invite(
    language: str,
    reviewer_kind: str,
    expires_days: int,
    label: str,
    created_by: int | None,
) -> dict[str, Any]:
    if language not in COURSE_LANGUAGES:
        return {"ok": False, "error": "Choose a valid language."}
    kind = normalize_kind(reviewer_kind)
    if not kind:
        return {"ok": False, "error": "Choose Academic or Community."}
    try:
        days = int(expires_days)
    except (TypeError, ValueError):
        days = 0
    if days not in {1, 7, 14, 30}:
        return {"ok": False, "error": "Choose a valid expiry."}
    raw = secrets.token_urlsafe(32)
    now = _now()
    expires = now + timedelta(days=days)
    conn = get_db()
    try:
        ensure_invite_schema(conn)
        conn.execute(
            """
            INSERT INTO review_invitations
                (token_hash, language, reviewer_kind, status, label,
                 created_by, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hash_invite_token(raw),
                language,
                kind,
                INVITE_ACTIVE,
                (label or "").strip()[:120] or None,
                created_by,
                now.isoformat(timespec="seconds"),
                expires.isoformat(timespec="seconds"),
            ),
        )
        invite_id = conn.execute(
            "SELECT id FROM review_invitations WHERE token_hash = ?",
            (hash_invite_token(raw),),
        ).fetchone()
        conn.commit()
        return {
            "ok": True,
            "token": raw,
            "invite_id": row_value(invite_id, "id") if invite_id else None,
            "language": language,
            "reviewer_kind": kind,
            "expires_at": expires.isoformat(timespec="seconds"),
        }
    finally:
        conn.close()


def list_review_invites() -> list[dict[str, Any]]:
    conn = get_db()
    try:
        ensure_invite_schema(conn)
        rows = conn.execute(
            """
            SELECT id, language, reviewer_kind, status, label, created_at,
                   expires_at, revoked_at, last_used_at
            FROM review_invitations
            ORDER BY id DESC
            """
        ).fetchall()
        return [_decorate(row_to_dict(r)) for r in rows]
    finally:
        conn.close()


def revoke_review_invite(invite_id: int, revoked_by: int | None) -> dict[str, Any]:
    conn = get_db()
    try:
        ensure_invite_schema(conn)
        row = conn.execute(
            "SELECT id, status FROM review_invitations WHERE id = ?",
            (invite_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "Invitation not found."}
        conn.execute(
            """
            UPDATE review_invitations
            SET status = ?, revoked_by = ?, revoked_at = ?
            WHERE id = ?
            """,
            (
                INVITE_REVOKED,
                revoked_by,
                _now().isoformat(timespec="seconds"),
                invite_id,
            ),
        )
        conn.commit()
        return {"ok": True, "message": "Invitation revoked. The private link no longer works."}
    finally:
        conn.close()


def lookup_invite_by_token(token: str) -> dict[str, Any] | None:
    digest = hash_invite_token(token)
    conn = get_db()
    try:
        ensure_invite_schema(conn)
        row = conn.execute(
            """
            SELECT id, language, reviewer_kind, status, label, created_at,
                   expires_at, revoked_at, last_used_at
            FROM review_invitations
            WHERE token_hash = ?
            """,
            (digest,),
        ).fetchone()
        if not row:
            return None
        return _decorate(row_to_dict(row))
    finally:
        conn.close()


def get_invite_by_id(invite_id: int) -> dict[str, Any] | None:
    conn = get_db()
    try:
        ensure_invite_schema(conn)
        row = conn.execute(
            """
            SELECT id, language, reviewer_kind, status, label, created_at,
                   expires_at, revoked_at, last_used_at
            FROM review_invitations
            WHERE id = ?
            """,
            (invite_id,),
        ).fetchone()
        if not row:
            return None
        return _decorate(row_to_dict(row))
    finally:
        conn.close()


def touch_invite_use(invite_id: int) -> None:
    conn = get_db()
    try:
        conn.execute(
            "UPDATE review_invitations SET last_used_at = ? WHERE id = ?",
            (_now().isoformat(timespec="seconds"), invite_id),
        )
        conn.commit()
    finally:
        conn.close()


def invite_is_usable(invite: dict[str, Any] | None) -> tuple[bool, str]:
    if not invite:
        return False, "invalid"
    status = invite_public_status(invite)
    if status == "revoked":
        return False, "revoked"
    if status == "expired":
        return False, "expired"
    return True, "active"


def allowed_vocab_statuses(kind: str) -> frozenset[str]:
    if kind == KIND_COMMUNITY:
        return COMMUNITY_VOCAB_STATUSES
    return ACADEMIC_VOCAB_STATUSES


def allowed_section_statuses(kind: str) -> frozenset[str]:
    if kind == KIND_COMMUNITY:
        return COMMUNITY_SECTION_STATUSES
    return ACADEMIC_SECTION_STATUSES


def vocab_choices_for_kind(kind: str) -> list[dict[str, str]]:
    source = COMMUNITY_VOCAB_CHOICES if kind == KIND_COMMUNITY else ACADEMIC_VOCAB_CHOICES
    return [{"id": a, "label": b} for a, b in source]


def section_choices_for_kind(kind: str) -> list[dict[str, str]]:
    source = COMMUNITY_SECTION_CHOICES if kind == KIND_COMMUNITY else ACADEMIC_SECTION_CHOICES
    return [{"id": a, "label": b} for a, b in source]


def actor_display(kind: str) -> str:
    if kind == KIND_COMMUNITY:
        return "Private Community Review Link"
    return "Private Academic Review Link"


def banner_text(invite: dict[str, Any]) -> str:
    lang = invite.get("language_label") or invite.get("language")
    if invite.get("reviewer_kind") == KIND_COMMUNITY:
        return f"Private Community Review Access — {lang}"
    return f"Private Academic Review Access — {lang}"
