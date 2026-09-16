"""Reusable Language Review & Documentation payloads for every course language."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from database import (
    COURSE_LANGUAGES,
    VOCAB_PACK_DIR,
    list_section_review_statuses,
    list_vocabulary_for_language,
    list_vocabulary_review_history_for_language,
)
from review_quality import (
    STATUS_LABELS,
    classify_entry,
    default_status_for_row,
    detect_entry_issues,
    status_label,
)
from review_notes import decorate_review_note_fields

SECTION_KEYS = (
    ("language_overview", "Language overview"),
    ("community", "Community / speakers"),
    ("location", "Place and setting"),
    ("preservation", "Learning and documentation note"),
    ("course_intent", "What this platform teaches"),
)

SECTION_STATUS_CHOICES = (
    ("academic_review_pending", "Review pending"),
    ("academically_reviewed", "Academically reviewed"),
    ("needs_revision", "Needs revision"),
    ("community_review_pending", "Community review pending"),
)

COLLAB_PATHWAYS = (
    ("academic_review", "Academic review", "Comment on accuracy, sources, and educational suitability."),
    ("community_review", "Community review", "Review cultural framing and whether examples are appropriate."),
    ("language_consultation", "Language / content consultation", "Advise on terms, spellings, or missing senses."),
    ("student_pilot", "Student pilot", "Try the lessons with a class or small learner group."),
    ("educational_feedback", "Educational feedback", "Comment on lesson pacing, quizzes, and clarity."),
    ("cultural_context", "Cultural / context review", "Advise on community context shown on the language pages."),
)

FILTERS = (
    ("all", "All"),
    ("needs_verification", "Needs verification"),
    ("technical_issues", "Technical issues"),
    ("reviewed", "Academically reviewed"),
    ("newly_added", "Newly added"),
    ("source_derived", "Source-derived"),
)

QUEUE_STATUSES = {
    "needs_verification",
    "needs_revision",
    "academic_review_pending",
    "community_review_pending",
}

DONE_REVIEW_STATUSES = {"reviewed", "academically_reviewed", "community_reviewed"}

VOCAB_STATUS_CHOICES = (
    ("needs_verification", "Needs verification"),
    ("needs_revision", "Needs revision"),
    ("academically_reviewed", "Academically reviewed"),
    ("community_review_pending", "Community review pending"),
    ("academic_review_pending", "Academic review pending"),
    ("source_derived", "Source-derived"),
)


def _pack_sources() -> list[dict[str, Any]]:
    path = VOCAB_PACK_DIR / "sources.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("external_packs_present") or [])


def _cite_vocab(row: dict[str, Any], display_name: str) -> str:
    word = row.get("word") or ""
    en = row.get("meaning_en") or ""
    ms = row.get("meaning_ms") or ""
    src = row.get("source_ref") or "source not recorded"
    dialect = row.get("dialect_variant") or ""
    gloss = en or ms or ""
    extra = f"; variety: {dialect}" if dialect else ""
    return (
        f"{word} ({display_name}"
        f"{': ' + gloss if gloss else ''}). "
        f"Malaysia Linguistics Lab dictionary entry. Source: {src}{extra}."
    )


def _decorate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter((r.get("word") or "").strip().lower() for r in rows)
    out = []
    for row in rows:
        issues = detect_entry_issues(row)
        key = (row.get("word") or "").strip().lower()
        if key and counts[key] > 1:
            issues.append(
                {
                    "code": "duplicate_headword",
                    "severity": "suspicious",
                    "label": "Duplicate headword",
                    "detail": "The same spelling appears more than once (often from overlapping sources).",
                }
            )
        status = default_status_for_row(row, issues)
        bucket = classify_entry({**row, "review_status": status}, issues)
        newly = int(row.get("is_newly_added") or 0) == 1
        if status == "technically_corrected":
            newly = newly or False
        src = (row.get("source_ref") or "")
        if src and src not in {"course_database", "course_quiz_stem"}:
            source_derived = True
        else:
            source_derived = False
        item = dict(row)
        item["issues"] = issues
        item["issue_labels"] = [i["label"] for i in issues]
        item["review_status"] = status
        item["review_status_label"] = status_label(status)
        item["bucket"] = bucket
        item["has_technical"] = any(i["severity"] == "technical" for i in issues)
        item["source_derived"] = source_derived
        item["is_newly_added"] = newly
        item["in_review_queue"] = _in_review_queue(status, bucket)
        decorate_review_note_fields(item)
        out.append(item)
    return out


def _in_review_queue(status: str, bucket: str) -> bool:
    if status in DONE_REVIEW_STATUSES:
        return False
    if status in QUEUE_STATUSES:
        return True
    return bucket in {"technical", "suspicious"}


def _academic_vocab_sample(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    seen: set[int] = set()

    def take(pred, n: int) -> None:
        count = 0
        for row in rows:
            rid = row.get("id")
            if rid in seen:
                continue
            if pred(row):
                picked.append(row)
                seen.add(rid)
                count += 1
            if count >= n or len(picked) >= limit:
                return

    take(lambda r: r.get("has_technical"), 3)
    take(lambda r: r["bucket"] == "suspicious" and not r.get("has_technical"), 2)
    # spread by first letter / gloss length as a crude category spread
    take(lambda r: r.get("source_derived") and (r.get("part_of_speech") == "noun"), 2)
    take(lambda r: r.get("source_derived") and (r.get("part_of_speech") in {"verb", "pronoun", "number"}), 2)
    take(lambda r: r.get("source_derived"), 4)
    take(lambda r: True, limit)
    return picked[:limit]


def _lesson_sample(course_data: dict, lang_key: str) -> dict[str, Any] | None:
    levels = (course_data or {}).get(lang_key) or {}
    if not levels:
        return None
    first_key = sorted(levels.keys(), key=lambda x: int(x) if str(x).isdigit() else 99)[0]
    level = levels[first_key]
    steps = level.get("steps") or []
    vocab = [s for s in steps if s.get("type") == "vocabulary"][:6]
    quizzes = [s for s in steps if s.get("type") == "quiz"][:4]
    if not vocab and not quizzes:
        return None
    answer_key = []
    for q in quizzes:
        opts = q.get("options") or []
        idx = q.get("correctIndex", 0)
        correct = opts[idx] if isinstance(idx, int) and 0 <= idx < len(opts) else ""
        answer_key.append(
            {
                "question": q.get("question") or q.get("prompt") or "",
                "answer": correct,
            }
        )
    return {
        "level": first_key,
        "title": (vocab[0].get("title") if vocab else None) or f"Level {first_key}",
        "vocabulary": vocab,
        "exercise": quizzes[:1],
        "answer_key": answer_key,
    }


def collaboration_copy(display_name: str) -> dict[str, Any]:
    return {
        "headline": f"Interested in supporting or reviewing this {display_name} resource?",
        "intro": (
            f"This is a student-built educational resource for {display_name}. "
            "It is not a community endorsement, not a complete dictionary, and not "
            "an official archive. Organisations, researchers, and lecturers can help "
            "by reviewing what is already here, advising on sources, or running a small pilot."
        ),
        "pathways": [
            {"id": p[0], "title": p[1], "blurb": p[2]} for p in COLLAB_PATHWAYS
        ],
        "disclaimer": (
            "Registering interest does not create a partnership. "
            "No organisation is listed as an endorser unless that is separately documented."
        ),
    }


def build_language_review_payload(
    lang_key: str,
    language: dict[str, Any],
    course_data: dict,
    family: str | None = None,
    can_edit: bool = False,
) -> dict[str, Any]:
    display = language.get("display_name") or lang_key
    raw_rows = list_vocabulary_for_language(lang_key)
    rows = _decorate_rows(raw_rows)
    for row in rows:
        row["citation"] = _cite_vocab(row, display)

    technical = [r for r in rows if r.get("has_technical")]
    needs_ver = [r for r in rows if r.get("in_review_queue")]
    reviewed = [r for r in rows if r.get("review_status") in DONE_REVIEW_STATUSES]
    history_map = list_vocabulary_review_history_for_language(
        lang_key,
        [r.get("id") for r in rows if r.get("in_review_queue") or r.get("review_status") in DONE_REVIEW_STATUSES],
    )
    for row in rows:
        row["history"] = history_map.get(int(row.get("id") or 0), [])[:8]
    queue = [r for r in rows if r.get("in_review_queue")]

    section_saved = list_section_review_statuses(lang_key)
    sections = []
    body_by_key = {
        "language_overview": language.get("about") or "",
        "community": language.get("speakers") or "",
        "location": language.get("location") or "",
        "preservation": language.get("preservation") or "",
        "course_intent": (
            f"The platform currently offers source-derived dictionary entries, "
            f"a small beginner course where available, and cultural context pages "
            f"for {display}. Course items harvested from lessons are pedagogical "
            f"and still require expert review."
        ),
    }
    title_by_key = {
        "language_overview": language.get("about_title") or "Language overview",
        "community": language.get("speakers_title") or "Community",
        "location": language.get("location_title") or "Place",
        "preservation": language.get("preservation_title") or "Documentation note",
        "course_intent": "What this platform teaches",
    }
    for key, fallback_title in SECTION_KEYS:
        status = (
            "academically_reviewed"
            if (section_saved.get(key) or "") == "reviewed"
            else (section_saved.get(key) or "academic_review_pending")
        )
        sections.append(
            {
                "key": key,
                "title": title_by_key.get(key) or fallback_title,
                "body": body_by_key.get(key) or "",
                "status": status,
                "status_label": status_label(status),
            }
        )

    pack_sources = [
        p
        for p in _pack_sources()
        if p.get("language") == lang_key
        or lang_key in (p.get("languages") or [])
        or (isinstance(p.get("files"), list) and lang_key in str(p))
    ]
    listed = language.get("sources") or language.get("references") or []
    vocab_source_counts = Counter(
        (r.get("source_ref") or "source not recorded").strip() or "source not recorded"
        for r in rows
    )
    provenance_groups = [
        {"source_ref": src, "count": n} for src, n in vocab_source_counts.most_common()
    ]

    academic_status = language.get("verification_status") or "Pending"
    community_status = "Pending"
    if language.get("verification_status", "").lower() in {"community verified", "verified"}:
        community_status = language.get("verification_status")

    return {
        "lang_key": lang_key,
        "display_name": display,
        "family": family or "",
        "region": language.get("region") or "",
        "summary": {
            "entry_count": len(rows),
            "needs_verification_count": len(needs_ver),
            "technical_issue_count": len(technical),
            "reviewed_count": len(reviewed),
            "academic_review": academic_status,
            "community_review": community_status,
            "method_note": (
                "This resource is based on currently available documented sources. "
                "Automated checks identify possible technical inconsistencies. "
                "Linguistic and cultural accuracy requires human review and is not "
                "established by passing automated checks."
            ),
        },
        "sections": sections,
        "section_status_choices": [
            {"id": a, "label": b} for a, b in SECTION_STATUS_CHOICES
        ],
        "vocabulary": rows,
        "review_queue": queue,
        "can_edit": bool(can_edit),
        "vocab_status_choices": [
            {"id": a, "label": b} for a, b in VOCAB_STATUS_CHOICES
        ],
        "filters": [{"id": a, "label": b} for a, b in FILTERS],
        "issues": technical
        + [r for r in rows if r["bucket"] == "suspicious" and not r.get("has_technical")],
        "provenance_groups": provenance_groups,
        "pack_sources": pack_sources,
        "listed_sources": listed,
        "gallery": language.get("gallery") or [],
        "academic_set": {
            "intro": (
                f"This is a representative sample for {display}, not a complete "
                "evaluation of every dictionary row. It is intended to make "
                "academic review efficient."
            ),
            "overview_keys": ["language_overview", "community"],
            "vocabulary": _academic_vocab_sample(rows),
            "lesson": _lesson_sample(course_data, lang_key),
            "categories": [
                "Language accuracy",
                "Translation quality",
                "Cultural accuracy/sensitivity",
                "Educational suitability",
                "Source/provenance",
                "Other comments",
            ],
        },
        "collaboration": collaboration_copy(display),
        "status_labels": STATUS_LABELS,
        "course_languages": list(COURSE_LANGUAGES),
    }


def filter_vocabulary(rows: list[dict[str, Any]], filt: str) -> list[dict[str, Any]]:
    if filt in (None, "", "all"):
        return rows
    if filt == "technical_issues":
        return [r for r in rows if r.get("has_technical")]
    if filt == "reviewed":
        return [r for r in rows if r.get("review_status") in DONE_REVIEW_STATUSES]
    if filt == "needs_verification":
        return [r for r in rows if r.get("in_review_queue")]
    if filt == "newly_added":
        return [r for r in rows if r.get("is_newly_added")]
    if filt == "source_derived":
        return [r for r in rows if r.get("source_derived")]
    return rows
