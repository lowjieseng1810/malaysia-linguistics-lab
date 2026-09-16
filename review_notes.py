"""Separate automated issue explanations from human reviewer notes."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

VOCAB_PACK_DIR = Path(__file__).resolve().parent / "data" / "vocabulary"

WIKTIONARY_MALAY_NOTE = (
    "Wiktionary source is Malay. English translation is not in this extract."
)

# Whole-string patterns for repair/seed explanations written into review_note.
_AUTO_NOTE_PATTERNS = (
    re.compile(r"^Wiktionary source is Malay\.", re.I),
    re.compile(r"^Headword '.+' and gloss '.+' look like extraction damage", re.I),
    re.compile(r"^OCR mixed-case\b", re.I),
    re.compile(r"^OCR '", re.I),
    re.compile(r"^Removed table-header\b", re.I),
    re.compile(r"^Original Malay field was OCR\b", re.I),
    re.compile(r"^Malay field was markdown/OCR\b", re.I),
    re.compile(r"^POS was pronoun;", re.I),
    re.compile(r"^Headword\b.+\b(OCR|extraction)", re.I),
    re.compile(r"^English field '.+' is not a recoverable OCR", re.I),
    re.compile(r"^This item comes from a beginner lesson", re.I),
    re.compile(r"^Possible pedagogical bridge", re.I),
    re.compile(r"^Possible truncation", re.I),
    re.compile(r"^The English column holds a Malay Wiktionary", re.I),
    re.compile(r"^Pipe or markdown-table characters", re.I),
    re.compile(r"^The term is only digits", re.I),
    re.compile(r"^Gloss ends with an ellipsis", re.I),
    re.compile(r"^English gloss has mixed-case or table-header", re.I),
    re.compile(r"^Stored POS is pronoun but the gloss is not pronominal", re.I),
    re.compile(r"^This item comes from a beginner lesson that uses a Malay", re.I),
)


@lru_cache(maxsize=1)
def pack_repair_notes() -> frozenset[str]:
    path = VOCAB_PACK_DIR / "mah_meri_pack_repairs.json"
    notes: set[str] = {WIKTIONARY_MALAY_NOTE}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset(notes)
    for item in payload.get("update") or []:
        text = ((item.get("set") or {}).get("review_note") or "").strip()
        if text:
            notes.add(text)
    return frozenset(notes)


def is_automated_issue_explanation(text: str | None) -> bool:
    """True when the whole string is a known automated/source-quality note."""
    raw = (text or "").strip()
    if not raw:
        return False
    if raw in pack_repair_notes():
        return True
    return any(pattern.search(raw) for pattern in _AUTO_NOTE_PATTERNS)


def _issue_lines(issues: Iterable[dict[str, Any]] | None) -> list[str]:
    lines: list[str] = []
    for issue in issues or []:
        label = (issue.get("label") or "").strip()
        detail = (issue.get("detail") or "").strip()
        if label and detail:
            if detail.lower().startswith(label.lower()):
                lines.append(detail)
            else:
                lines.append(f"{label}. {detail}")
        elif detail:
            lines.append(detail)
        elif label:
            lines.append(label)
    return lines


def _dedupe(parts: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        text = re.sub(r"\s+", " ", (part or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def split_review_note_fields(
    stored_note: str | None,
    issues: list[dict[str, Any]] | None = None,
    existing_issue_context: str | None = None,
) -> tuple[str, str]:
    """Return (issue_context, reviewer_note).

    Automated/source-quality explanations become read-only context.
    Only text that cannot be identified as automated stays a human note.
    """
    context = _dedupe(
        [existing_issue_context or ""]
        + _issue_lines(issues)
        + [
            chunk
            for chunk in re.split(r"\n+", stored_note or "")
            if is_automated_issue_explanation(chunk)
        ]
    )
    human_chunks = []
    for chunk in re.split(r"\n+", stored_note or ""):
        text = chunk.strip()
        if not text:
            continue
        if is_automated_issue_explanation(text):
            continue
        if text.lower() in {c.lower() for c in context}:
            continue
        human_chunks.append(text)
    return " ".join(context).strip(), "\n".join(human_chunks).strip()


def decorate_review_note_fields(row: dict[str, Any]) -> dict[str, Any]:
    """Attach display fields without mutating stored history."""
    from review_quality import detect_entry_issues

    issues = row.get("issues")
    if issues is None:
        issues = detect_entry_issues(row)
        row["issues"] = issues
    context, human = split_review_note_fields(
        row.get("review_note"),
        issues,
        row.get("issue_context"),
    )
    row["issue_context"] = context
    row["reviewer_note"] = human
    row["review_note"] = human
    return row
