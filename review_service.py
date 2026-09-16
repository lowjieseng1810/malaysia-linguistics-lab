"""Reusable Language Review & Documentation payloads for every course language."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from database import (
    COURSE_LANGUAGES,
    VOCAB_PACK_DIR,
    get_latest_academic_review_note,
    list_section_reviews,
    list_vocabulary_for_language,
    list_vocabulary_review_history_for_language,
)
from review_quality import (
    STATUS_LABELS,
    classify_entry,
    default_status_for_row,
    detect_entry_issues,
    is_course_pedagogical_bridge,
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
    ("pedagogical_bridge", "Pedagogical bridge"),
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
    ("pedagogical_bridge", "Pedagogical bridge"),
)

ACADEMIC_WORKSPACE_SECTION_CHOICES = (
    ("academic_review_pending", "Review pending"),
    ("academically_reviewed", "Academically reviewed"),
    ("needs_revision", "Needs revision"),
)

ACADEMIC_WORKSPACE_VOCAB_CHOICES = (
    ("academic_review_pending", "Review pending"),
    ("needs_verification", "Needs verification"),
    ("academically_reviewed", "Academically reviewed"),
    ("needs_revision", "Needs revision"),
)

EXPERT_JUDGEMENT_HEADWORDS = ("src", "raachin", "o-h")


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
        item["is_pedagogical_bridge"] = is_course_pedagogical_bridge(item, issues)
        item["in_review_queue"] = _in_review_queue(item)
        decorate_review_note_fields(item)
        out.append(item)
    return out


def _in_review_queue(item: dict[str, Any]) -> bool:
    status = item.get("review_status") or ""
    bucket = item.get("bucket") or ""
    if item.get("is_pedagogical_bridge") or status == "pedagogical_bridge":
        return False
    if status in DONE_REVIEW_STATUSES:
        return False
    if status in QUEUE_STATUSES:
        return True
    return bucket in {"technical", "suspicious"}


def _section_state(section_full: dict[str, dict[str, str]], key: str) -> tuple[str, str]:
    saved = section_full.get(key) or {}
    status = saved.get("status") or "academic_review_pending"
    if status == "reviewed":
        status = "academically_reviewed"
    return status, saved.get("note") or ""


def _academic_expert_issues(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = {key: None for key in EXPERT_JUDGEMENT_HEADWORDS}
    extras: list[dict[str, Any]] = []
    for row in rows:
        if row.get("is_pedagogical_bridge"):
            continue
        key = (row.get("word") or "").strip().lower()
        if key in wanted and wanted[key] is None:
            wanted[key] = row
        elif row.get("has_technical") or (
            row.get("bucket") == "suspicious" and row.get("in_review_queue")
        ):
            extras.append(row)
    picked = [wanted[key] for key in EXPERT_JUDGEMENT_HEADWORDS if wanted[key]]
    seen = {row.get("id") for row in picked}
    for row in extras:
        if len(picked) >= 6:
            break
        rid = row.get("id")
        if rid in seen:
            continue
        if wanted.get((row.get("word") or "").strip().lower()):
            continue
        # Only pad when a named historical/OCR form is missing.
        if any(wanted[key] is None for key in EXPERT_JUDGEMENT_HEADWORDS):
            picked.append(row)
            seen.add(rid)
    return picked


def _academic_vocab_sample(
    rows: list[dict[str, Any]],
    exclude_ids: set[int] | None = None,
    lesson_words: set[str] | None = None,
    limit: int = 14,
) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    seen: set[int] = set(exclude_ids or set())
    lesson_words = {w.strip().lower() for w in (lesson_words or set()) if w}

    def eligible(row: dict[str, Any]) -> bool:
        rid = row.get("id")
        if rid in seen:
            return False
        if row.get("is_pedagogical_bridge") or row.get("review_status") == "pedagogical_bridge":
            return False
        return True

    def take(pred, n: int) -> None:
        count = 0
        for row in rows:
            if not eligible(row):
                continue
            if pred(row):
                picked.append(row)
                seen.add(row.get("id"))
                count += 1
            if count >= n or len(picked) >= limit:
                return

    take(
        lambda r: r.get("source_derived")
        and (r.get("word") or "").strip().lower() in lesson_words,
        2,
    )
    take(
        lambda r: r.get("source_derived") and (r.get("part_of_speech") == "noun"),
        4,
    )
    take(
        lambda r: r.get("source_derived")
        and (r.get("part_of_speech") in {"verb", "pronoun", "number", "adjective"}),
        3,
    )
    take(lambda r: r.get("source_derived"), 4)
    take(
        lambda r: r.get("in_review_queue") and not r.get("has_technical"),
        2,
    )
    take(lambda r: r.get("in_review_queue"), 2)
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
    primary = quizzes[:1]
    exercise = None
    if primary:
        q = primary[0]
        opts = q.get("options") or []
        idx = q.get("correctIndex", 0)
        correct = opts[idx] if isinstance(idx, int) and 0 <= idx < len(opts) else ""
        exercise = {
            "question": q.get("question") or q.get("prompt") or "",
            "instruction": q.get("instruction") or "",
            "options": opts,
            "answer": correct,
        }
    return {
        "level": first_key,
        "title": (vocab[0].get("title") if vocab else None) or f"Level {first_key}",
        "vocabulary": vocab,
        "exercise": exercise,
        "answer_key": answer_key,
    }


def _academic_set(
    display: str,
    lang_key: str,
    course_data: dict,
    rows: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    section_full: dict[str, dict[str, str]],
    invite: dict[str, Any] | None,
) -> dict[str, Any]:
    overview_keys = ["language_overview", "community"]
    lesson = _lesson_sample(course_data, lang_key)
    expert_issues = _academic_expert_issues(rows)
    exclude_ids = {row.get("id") for row in expert_issues if row.get("id") is not None}
    lesson_words = {
        (item.get("word") or "").strip().lower()
        for item in ((lesson or {}).get("vocabulary") or [])
        if item.get("word")
    }
    lesson_status, lesson_note = _section_state(section_full, "beginner_lesson")
    exercise_status, exercise_note = _section_state(section_full, "lesson_exercise")
    latest = get_latest_academic_review_note(lang_key) or {}
    community_invite = (invite or {}).get("reviewer_kind") == "community"
    section_choices = (
        (
            ("community_review_pending", "Review pending"),
            ("community_reviewed", "Community reviewed"),
            ("needs_revision", "Needs revision"),
        )
        if community_invite
        else ACADEMIC_WORKSPACE_SECTION_CHOICES
    )
    vocab_choices = (
        (
            ("needs_verification", "Needs verification"),
            ("community_review_pending", "Review pending"),
            ("community_reviewed", "Community reviewed"),
            ("needs_revision", "Needs revision"),
        )
        if community_invite
        else ACADEMIC_WORKSPACE_VOCAB_CHOICES
    )
    categories = [
        "Language accuracy",
        "Translation quality",
        "Cultural accuracy/sensitivity",
        "Educational suitability",
        "Source/provenance",
        "Other comments",
    ]
    return {
        "intro": (
            f"Open the selected {display} content here, judge it, add a note, and save. "
            "You do not need to leave this tab to record a decision."
        ),
        "scope_title": "Suggested review scope",
        "scope_body": (
            "This is a representative sample intended to make academic review efficient. "
            "You do not need to review the entire dictionary."
        ),
        "overview_keys": overview_keys,
        "overview_sections": [s for s in sections if s.get("key") in overview_keys],
        "vocabulary": _academic_vocab_sample(rows, exclude_ids, lesson_words),
        "expert_issues": expert_issues,
        "lesson": lesson,
        "lesson_status": lesson_status,
        "lesson_note": lesson_note,
        "exercise_status": exercise_status,
        "exercise_note": exercise_note,
        "section_status_choices": [{"id": a, "label": b} for a, b in section_choices],
        "vocab_status_choices": [{"id": a, "label": b} for a, b in vocab_choices],
        "categories": categories,
        "selected_categories": latest.get("categories") or [],
        "dimension_comments": latest.get("comments") or "",
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


def _history_matches_invite(row: dict[str, Any], invite: dict[str, Any]) -> bool:
    label = (invite.get("label") or "").strip()
    for event in row.get("history") or []:
        if (event.get("review_actor_type") or "") != "private_review_link":
            continue
        event_label = (event.get("invite_label") or "").strip()
        if label and event_label == label:
            return True
        if not label and not event_label:
            return True
    return False


def _recent_reviews(rows: list[dict[str, Any]], invite: dict[str, Any] | None) -> list[dict[str, Any]]:
    recent = []
    for row in rows:
        if not (row.get("reviewed_at") or row.get("history")):
            continue
        if invite and not _history_matches_invite(row, invite):
            continue
        recent.append(row)
    recent.sort(key=lambda r: (r.get("reviewed_at") or "", int(r.get("id") or 0)), reverse=True)
    return recent


def build_language_review_payload(
    lang_key: str,
    language: dict[str, Any],
    course_data: dict,
    family: str | None = None,
    can_edit: bool = False,
    invite: dict[str, Any] | None = None,
) -> dict[str, Any]:
    display = language.get("display_name") or lang_key
    raw_rows = list_vocabulary_for_language(lang_key)
    rows = _decorate_rows(raw_rows)
    for row in rows:
        row["citation"] = _cite_vocab(row, display)

    technical = [r for r in rows if r.get("has_technical") and not r.get("is_pedagogical_bridge")]
    needs_ver = [r for r in rows if r.get("in_review_queue")]
    reviewed = [r for r in rows if r.get("review_status") in DONE_REVIEW_STATUSES]
    bridges = [r for r in rows if r.get("is_pedagogical_bridge") or r.get("review_status") == "pedagogical_bridge"]
    history_map = list_vocabulary_review_history_for_language(
        lang_key,
        [r.get("id") for r in rows],
    )
    for row in rows:
        row["history"] = history_map.get(int(row.get("id") or 0), [])[:12]
    queue = [r for r in rows if r.get("in_review_queue")]
    recent = _recent_reviews(rows, invite)

    section_full = list_section_reviews(lang_key)
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
        status, note = _section_state(section_full, key)
        sections.append(
            {
                "key": key,
                "title": title_by_key.get(key) or fallback_title,
                "body": body_by_key.get(key) or "",
                "status": status,
                "status_label": status_label(status),
                "reviewer_note": note,
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
            "pedagogical_bridge_count": len(bridges),
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
        "recent_reviews": recent,
        "can_edit": bool(can_edit),
        "vocab_status_choices": [
            {"id": a, "label": b} for a, b in VOCAB_STATUS_CHOICES
        ],
        "filters": [{"id": a, "label": b} for a, b in FILTERS],
        "issues": technical
        + [
            r
            for r in rows
            if r["bucket"] == "suspicious"
            and not r.get("has_technical")
            and not r.get("is_pedagogical_bridge")
        ],
        "provenance_groups": provenance_groups,
        "pack_sources": pack_sources,
        "listed_sources": listed,
        "gallery": language.get("gallery") or [],
        "academic_set": _academic_set(
            display,
            lang_key,
            course_data,
            rows,
            sections,
            section_full,
            invite,
        ),
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
    if filt == "pedagogical_bridge":
        return [
            r
            for r in rows
            if r.get("is_pedagogical_bridge") or r.get("review_status") == "pedagogical_bridge"
        ]
    return rows
