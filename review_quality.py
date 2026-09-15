"""Automated technical/data-quality checks for language vocabulary.

These checks never treat an unfamiliar indigenous form as an error.
They flag extraction artefacts, empty fields, and malformed metadata only.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Status labels shown in the review UI. Human review is never inferred
# from automated checks.
STATUS_SOURCE_DERIVED = "source_derived"
STATUS_NEEDS_VERIFICATION = "needs_verification"
STATUS_TECHNICALLY_CORRECTED = "technically_corrected"
STATUS_ACADEMIC_REVIEW_PENDING = "academic_review_pending"
STATUS_COMMUNITY_REVIEW_PENDING = "community_review_pending"
STATUS_REVIEWED = "reviewed"
STATUS_NEEDS_REVISION = "needs_revision"

STATUS_LABELS = {
    STATUS_SOURCE_DERIVED: "Source-derived",
    STATUS_NEEDS_VERIFICATION: "Needs verification",
    STATUS_TECHNICALLY_CORRECTED: "Technically corrected",
    STATUS_ACADEMIC_REVIEW_PENDING: "Academic review pending",
    STATUS_COMMUNITY_REVIEW_PENDING: "Community review pending",
    STATUS_REVIEWED: "Reviewed",
    STATUS_NEEDS_REVISION: "Needs revision",
}

SEVERITY_TECHNICAL = "technical"
SEVERITY_SUSPICIOUS = "suspicious"

_HTML_RE = re.compile(r"</?[a-zA-Z][^>]*>")
_REPLACEMENT = "\ufffd"
_MULTI_SPACE = re.compile(r"\s{2,}")
_ASJP_HEADER = re.compile(
    r"\d+\.\d+\s+\d+\.\d+|^\d{3,}$|\b(mhm|mhe|dtp|iba|bit|bth)\b",
    re.I,
)
_ISO_NOISE = re.compile(r"\b[a-z]{3}\s+[a-z]{3}\s+\d+\s+[A-Za-z]+\b")
_PIPE_OCR = re.compile(r"\|")
_MARKDOWN_TABLE = re.compile(r"---")
_CONTROL_OK = {"\n", "\t"}
_MIXED_OCR = re.compile(r"[a-z][A-Z]|[A-Z]{2,}[a-z]+[A-Z]")
_TRAILING_TO = re.compile(r"\s+To$", re.I)
_LEADING_TO = re.compile(r"^TO\s+", re.I)

# Malay-looking closed-class items used as pedagogical bridges in COURSE_DATA.
_BRIDGE_MALAY = {
    "selamat",
    "terima kasih",
    "ya",
    "tak",
    "nama?",
    "nama saya ...",
}


def _text(*parts: Any) -> str:
    return " ".join((p or "") if isinstance(p, str) else "" for p in parts)


def detect_entry_issues(row: dict[str, Any]) -> list[dict[str, str]]:
    """Return issue dicts: {code, severity, label, detail}."""
    word = (row.get("word") or "").strip()
    en = (row.get("meaning_en") or "").strip()
    ms = (row.get("meaning_ms") or "").strip()
    src = (row.get("source_ref") or "").strip()
    blob = _text(word, en, ms)
    issues: list[dict[str, str]] = []

    def add(code: str, severity: str, label: str, detail: str) -> None:
        issues.append(
            {
                "code": code,
                "severity": severity,
                "label": label,
                "detail": detail,
            }
        )

    if not word:
        add("empty_term", SEVERITY_TECHNICAL, "Empty term", "The headword field is empty.")
    if not en and not ms:
        add(
            "empty_translation",
            SEVERITY_TECHNICAL,
            "Empty translations",
            "Neither English nor Malay gloss is present.",
        )
    if word and re.fullmatch(r"\d+", word):
        add(
            "isolated_number",
            SEVERITY_TECHNICAL,
            "Numeric headword",
            "The term is only digits (likely an extraction ID, not a word).",
        )
    if word and re.fullmatch(r"[0-9.\s]+", word):
        add(
            "numeric_garbage",
            SEVERITY_TECHNICAL,
            "Numeric garbage",
            "The term contains no letters.",
        )
    if _REPLACEMENT in blob:
        add(
            "replacement_char",
            SEVERITY_TECHNICAL,
            "Replacement character",
            "U+FFFD present — Unicode was lost during extraction.",
        )
    if _HTML_RE.search(blob):
        add(
            "html_markup",
            SEVERITY_TECHNICAL,
            "HTML/markup",
            "Angle-bracket markup leaked into a lexical field.",
        )
    if _PIPE_OCR.search(blob) or _MARKDOWN_TABLE.search(blob):
        add(
            "ocr_table_artefact",
            SEVERITY_TECHNICAL,
            "Table/OCR artefact",
            "Pipe or markdown-table characters suggest a broken column parse.",
        )
    if _ASJP_HEADER.search(en) or _ISO_NOISE.search(en) or _ASJP_HEADER.search(word):
        add(
            "asjp_header_bleed",
            SEVERITY_TECHNICAL,
            "Wordlist header bleed",
            "Coordinates, ISO codes, or numeric IDs appear in a lexical field.",
        )
    if any(
        unicodedata.category(ch).startswith("C") and ch not in _CONTROL_OK
        for ch in blob
    ):
        add(
            "control_chars",
            SEVERITY_TECHNICAL,
            "Control characters",
            "Non-printable characters in a lexical field.",
        )
    if word != (row.get("word") or "") or _MULTI_SPACE.search(word):
        add(
            "inconsistent_whitespace",
            SEVERITY_SUSPICIOUS,
            "Whitespace",
            "Leading, trailing, or doubled spaces on the term.",
        )
    if en.endswith("...") or ms.endswith("..."):
        add(
            "truncated_value",
            SEVERITY_SUSPICIOUS,
            "Possibly truncated",
            "Gloss ends with an ellipsis.",
        )
    if _MIXED_OCR.search(en) or _TRAILING_TO.search(en) or _LEADING_TO.search(en):
        add(
            "ocr_capitalization",
            SEVERITY_TECHNICAL,
            "OCR capitalization artefact",
            "English gloss has mixed-case or table-header 'To' residue.",
        )
    if not src:
        add(
            "missing_source",
            SEVERITY_SUSPICIOUS,
            "Missing source reference",
            "No source_ref is stored for this row.",
        )
    lang = (row.get("language") or "").strip()
    if lang == "mah-meri" and word.lower() in _BRIDGE_MALAY:
        add(
            "pedagogical_bridge",
            SEVERITY_SUSPICIOUS,
            "Pedagogical bridge form",
            "This item comes from a beginner lesson that uses a Malay/multilingual "
            "bridge expression. It is not automatically a Mah Meri lexeme.",
        )
    # Malay gloss parked in the English field (ms.wiktionary extracts).
    if (
        "wiktionary" in src.lower()
        and en
        and not ms
        and re.fullmatch(r"[a-zA-Zà-ÿĉéíóúă'’\-,\.\s()]+", en)
        and not re.search(r"\b(the|a|to|of|and|person|you|water|fish)\b", en, re.I)
        and re.search(
            r"\b(minum|anak|besar|makan|rumah|lepas|lebah|longgokan)\b",
            en,
            re.I,
        )
    ):
        add(
            "malay_in_english_field",
            SEVERITY_SUSPICIOUS,
            "Malay gloss in English field",
            "The English column holds a Malay Wiktionary definition. "
            "English translation still needs verification.",
        )
    pos = (row.get("part_of_speech") or "").strip().lower()
    if pos == "pronoun" and en.lower() in {
        "fish", "drink", "die", "fire", "mountain", "night", "liver", "boil",
    }:
        add(
            "pos_mismatch",
            SEVERITY_SUSPICIOUS,
            "Part-of-speech mismatch",
            "Stored POS is pronoun but the gloss is not pronominal.",
        )
    return issues


def classify_entry(
    row: dict[str, Any],
    issues: list[dict[str, str]] | None = None,
) -> str:
    """Bucket: technical | suspicious | source_ok | reviewed."""
    stored = (row.get("review_status") or "").strip()
    if stored == STATUS_REVIEWED:
        return "reviewed"
    found = issues if issues is not None else detect_entry_issues(row)
    if any(i["severity"] == SEVERITY_TECHNICAL for i in found):
        return "technical"
    if stored in {
        STATUS_NEEDS_VERIFICATION,
        STATUS_NEEDS_REVISION,
        STATUS_ACADEMIC_REVIEW_PENDING,
        STATUS_COMMUNITY_REVIEW_PENDING,
    }:
        return "suspicious"
    if found:
        return "suspicious"
    return "source_ok"


def default_status_for_row(row: dict[str, Any], issues: list[dict[str, str]]) -> str:
    stored = (row.get("review_status") or "").strip()
    if stored:
        return stored
    if any(i["severity"] == SEVERITY_TECHNICAL for i in issues):
        return STATUS_NEEDS_VERIFICATION
    src = (row.get("source_ref") or "").strip()
    if src in {"course_database", "course_quiz_stem"}:
        return STATUS_NEEDS_VERIFICATION
    if src:
        return STATUS_SOURCE_DERIVED
    return STATUS_NEEDS_VERIFICATION


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status.replace("_", " ").title())
