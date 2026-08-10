"""
Dynamic language registry loaded from SQLite content tables.

No hardcoded language names — any language present in the database
is supported automatically (including future inserts).
"""

from __future__ import annotations

import re
import time
from typing import Optional

from db import get_db

_CACHE: Optional[dict] = None
_CACHE_TS: float = 0.0
_TTL_SECONDS = 30.0

# English / query glue words — never treated as language names
_NON_LANGUAGE_TOKENS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "from",
    "with", "this", "that", "these", "those", "all", "every", "each",
    "lesson", "lessons", "language", "languages", "word", "words",
    "vocabulary", "grammar", "culture", "quiz", "longest", "shortest",
    "compare", "comparison", "versus", "vs", "across", "whole", "database",
    "how", "many", "what", "which", "top", "average", "beginning", "ending",
    "containing", "starts", "ends", "most", "common", "size", "count",
    "greeting", "greetings", "please", "show", "give", "tell", "me",
    "about", "today", "current", "available", "supported", "heritage",
    "malaysian", "minority", "english", "malay", "chinese", "translation",
    # Linguistics / teaching topics — never language names
    "morphology", "syntax", "semantics", "pragmatics", "phonology",
    "phonetics", "phonetic", "ipa", "orthography", "etymology",
    "typology", "discourse", "sociolinguistics", "dialectology",
    "lexicography", "prosody", "intonation", "morpheme", "phoneme",
    "allophone", "agglutination", "pronunciation", "pronounce",
    "difference", "differences", "similarity", "similarities",
    "family", "families", "austronesian", "asli", "aslian",
    "revitalization", "endangerment", "endangered", "writing", "system",
    "systems", "acquisition", "history", "historical", "linguistic",
    "linguistics", "difficulty", "difficult", "hardest", "easiest",
    "random", "alphabetically", "alphabetical", "example", "examples",
    "sentence", "sentences", "noun", "nouns", "verb", "verbs",
    "adjective", "adjectives", "phrase", "phrases", "meaning", "meanings",
}


def _normalize_alias(text: str) -> str:
    text = (text or "").strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def _aliases_for_key(key: str) -> set[str]:
    """Derive match aliases from a DB language key only (no external names)."""
    key = (key or "").strip()
    if not key:
        return set()
    spaced = key.replace("-", " ").replace("_", " ").lower()
    aliases = {
        key.lower(),
        spaced,
        key.replace("-", "").replace("_", "").lower(),
        _normalize_alias(key),
    }
    return {a for a in aliases if a}


def display_name(key: str) -> str:
    return (key or "").replace("-", " ").replace("_", " ").title()


def _load_keys_from_db() -> list[str]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT language AS lang FROM vocabulary WHERE language IS NOT NULL AND language != ''
            UNION
            SELECT language FROM grammar WHERE language IS NOT NULL AND language != ''
            UNION
            SELECT language FROM culture WHERE language IS NOT NULL AND language != ''
            UNION
            SELECT language FROM quiz WHERE language IS NOT NULL AND language != ''
            ORDER BY lang
            """
        ).fetchall()
        return [str(r[0]).strip() for r in rows if r[0]]
    finally:
        conn.close()


def refresh_registry(force: bool = False) -> dict:
    """Load / refresh cached language keys and alias map from SQLite."""
    global _CACHE, _CACHE_TS
    now = time.time()
    if (
        not force
        and _CACHE is not None
        and (now - _CACHE_TS) < _TTL_SECONDS
    ):
        return _CACHE

    keys = _load_keys_from_db()
    alias_map: dict[str, str] = {}
    for key in keys:
        for alias in _aliases_for_key(key):
            alias_map.setdefault(alias, key)

    # Unambiguous segment aliases: "kadazan" → kadazan-dusun when unique
    segment_owners: dict[str, list[str]] = {}
    for key in keys:
        parts = re.split(r"[-_\s]+", key.lower())
        for part in parts:
            if len(part) < 3 or part in _NON_LANGUAGE_TOKENS:
                continue
            segment_owners.setdefault(part, []).append(key)
    for part, owners in segment_owners.items():
        unique_owners = sorted(set(owners))
        if len(unique_owners) == 1:
            alias_map.setdefault(part, unique_owners[0])

    _CACHE = {
        "keys": keys,
        "alias_map": alias_map,
        "displays": {k: display_name(k) for k in keys},
    }
    _CACHE_TS = now
    return _CACHE


def get_language_keys() -> list[str]:
    return list(refresh_registry()["keys"])


def resolve_language(token: str) -> Optional[str]:
    """Map a user-facing name/alias to a DB language key, or None."""
    alias = _normalize_alias(token)
    if not alias or alias in _NON_LANGUAGE_TOKENS:
        return None
    registry = refresh_registry()
    if alias in registry["alias_map"]:
        return registry["alias_map"][alias]
    # Compact form
    compact = alias.replace(" ", "")
    if compact in registry["alias_map"]:
        return registry["alias_map"][compact]
    return None


def extract_languages(message: str) -> list[str]:
    """
    Find all supported language keys mentioned in the message.
    Supports multi-word names (e.g. Mah Meri) via longest-alias matching.
    Returns keys in left-to-right mention order.
    """
    registry = refresh_registry()
    text = _normalize_alias(message)
    if not text:
        return []

    aliases = sorted(registry["alias_map"].keys(), key=len, reverse=True)
    matches: list[tuple[int, str]] = []
    occupied = [False] * (len(text) + 1)

    for alias in aliases:
        if not alias:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)", re.I)
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            if any(occupied[start:end]):
                continue
            for i in range(start, end):
                occupied[i] = True
            key = registry["alias_map"][alias]
            matches.append((start, key))

    matches.sort(key=lambda x: x[0])
    found: list[str] = []
    for _, key in matches:
        if key not in found:
            found.append(key)
    return found


def extract_unsupported_language_mentions(message: str) -> list[str]:
    """
    Detect language-like mentions that are NOT in the registry.
    Looks at compare-lists and 'in/for <Name>' patterns.
    """
    registry = refresh_registry()
    text = message or ""
    candidates: list[str] = []

    # Compare X, Y and Z / Compare X and Y
    m = re.search(
        r"(?is)\bcompare\b\s+(.+?)(?:\?|$)",
        text,
    )
    if m:
        blob = m.group(1)
        parts = re.split(r"\s*(?:,|/|\band\b|\bvs\.?\b|\bversus\b)\s*", blob)
        for part in parts:
            part = part.strip(" .?\"'")
            if part:
                candidates.append(part)

    # in/for <Language Name>
    for m in re.finditer(
        r"(?i)\b(?:in|for|of)\s+([A-Za-z][A-Za-z\- ]{1,40?}?)(?=\s+(?:and|or|vs|versus|,|\.|$|\?|across|lesson|words?|vocabulary|grammar|greetings?))",
        text,
    ):
        candidates.append(m.group(1).strip())

    # "in Japanese" / "in French" end of phrase
    for m in re.finditer(r"(?i)\b(?:in|for)\s+([A-Za-z][A-Za-z\- ]{1,30})\s*$", text):
        candidates.append(m.group(1).strip())

    # Longest word in X
    for m in re.finditer(
        r"(?i)\b(?:longest|shortest|top\s+\d+|words?|greetings?|vocabulary)\s+(?:word\s+)?(?:in|for|across)\s+([A-Za-z][A-Za-z\- ]{1,40})",
        text,
    ):
        candidates.append(m.group(1).strip())

    unsupported: list[str] = []
    for cand in candidates:
        norm = _normalize_alias(cand)
        if not norm or norm in _NON_LANGUAGE_TOKENS:
            continue
        # Skip if any token is a known non-language / linguistics topic word
        tokens = [t for t in norm.split() if t not in _NON_LANGUAGE_TOKENS]
        if not tokens:
            continue
        # Whole candidate is a linguistics/topic phrase
        if all(t in _NON_LANGUAGE_TOKENS for t in norm.split()):
            continue
        # Skip "all languages" / "this lesson"
        if norm in {"all languages", "all language", "this lesson", "this language", "every language"}:
            continue
        if resolve_language(cand) is None and extract_languages(cand) == []:
            label = cand.strip()
            if label and label not in unsupported:
                if norm not in {"all", "database", "lesson"} and norm not in _NON_LANGUAGE_TOKENS:
                    unsupported.append(label)
    return unsupported


def supported_languages_message(unsupported: str | None = None) -> str:
    keys = get_language_keys()
    lines = []
    if unsupported:
        lines.append(
            f"**{unsupported}** is not currently available in the "
            "Malaysian Linguistics Lab database."
        )
        lines.append("")
    lines.append("Supported languages include:")
    lines.append("")
    if not keys:
        lines.append("- (none loaded yet — add rows to the vocabulary table)")
    else:
        for key in keys:
            lines.append(f"- {display_name(key)}")
    lines.append("")
    lines.append(
        "Adding a language only requires inserting verified rows into SQLite — "
        "no planner code changes."
    )
    return "\n".join(lines)


def domain_language_pattern() -> re.Pattern:
    """Regex matching any currently registered language alias."""
    registry = refresh_registry()
    aliases = sorted(registry["alias_map"].keys(), key=len, reverse=True)
    if not aliases:
        return re.compile(r"a^")  # never matches
    parts = [re.escape(a) for a in aliases if a]
    return re.compile(r"(?<!\w)(" + "|".join(parts) + r")(?!\w)", re.I)
