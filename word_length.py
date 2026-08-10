"""
Deterministic lexical word-length normalization for structured vocab analytics.

Used by longest/shortest/rank/filter operations. Display spelling is never mutated —
only the length measurement uses the normalized form.
"""

from __future__ import annotations

import re
import unicodedata

from db import row_to_dict


def normalized_word_form(word: str) -> str:
    """
    Lexical form used only for length measurement:
    - Unicode NFC
    - trim whitespace
    - drop whitespace / separator / punctuation characters
    - keep letters, marks, and digits
    """
    text = unicodedata.normalize("NFC", (word or "").strip())
    chars: list[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("Z"):  # separators / whitespace
            continue
        if cat.startswith("P"):  # punctuation
            continue
        if cat == "Cc":  # control
            continue
        chars.append(ch)
    return "".join(chars)


def normalized_word_length(word: str) -> int:
    """Count lexical characters after normalization (never counts punctuation)."""
    return len(normalized_word_form(word))


def rank_rows_by_word_length(
    rows: list[dict],
    *,
    descending: bool,
    limit: int,
    offset: int = 0,
    length_filters: list[dict] | None = None,
) -> list[dict]:
    """
    Rank a COMPLETE vocabulary result set by normalized length.

    Preserves original `word` spelling; attaches `word_len` for analytics display.
    """
    enriched: list[dict] = []
    for row in rows or []:
        item = row_to_dict(row)
        item["word_len"] = normalized_word_length(item.get("word") or "")
        enriched.append(item)

    for filt in length_filters or []:
        op = (filt.get("op") or "=").strip()
        value = filt.get("value")
        if op == "between" and isinstance(value, (list, tuple)) and len(value) == 2:
            lo, hi = int(value[0]), int(value[1])
            enriched = [r for r in enriched if lo <= int(r["word_len"]) <= hi]
            continue
        try:
            threshold = int(value)
        except (TypeError, ValueError):
            continue
        if op == ">":
            enriched = [r for r in enriched if int(r["word_len"]) > threshold]
        elif op == ">=":
            enriched = [r for r in enriched if int(r["word_len"]) >= threshold]
        elif op == "<":
            enriched = [r for r in enriched if int(r["word_len"]) < threshold]
        elif op == "<=":
            enriched = [r for r in enriched if int(r["word_len"]) <= threshold]
        elif op == "=":
            enriched = [r for r in enriched if int(r["word_len"]) == threshold]

    enriched.sort(
        key=lambda r: (
            -int(r["word_len"]) if descending else int(r["word_len"]),
            str(r.get("word") or "").lower(),
        )
    )
    start = max(0, int(offset or 0))
    end = start + max(1, int(limit or 1))
    return enriched[start:end]


# Shared documentation string for SQL audit trails
COMPLETE_SCAN_NOTE = "complete_vocabulary_scan+normalized_word_length_rank"
