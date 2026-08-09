"""
Final response validator — refuse incomplete / ungrounded answers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from language_registry import display_name


@dataclass
class ResponseCheck:
    ok: bool
    reason: str
    message: str = ""
    missing_languages: list[str] = field(default_factory=list)
    retrieved_languages: list[str] = field(default_factory=list)
    requested_languages: list[str] = field(default_factory=list)
    coverage_percent: float = 0.0
    checks: dict[str, bool] = field(default_factory=dict)


def languages_from_bundle(bundle, plan=None) -> list[str]:
    found: list[str] = []
    for hit in getattr(bundle, "hits", None) or []:
        if not hit.rows:
            continue
        lang = None
        if "__" in hit.name:
            parts = hit.name.split("__")
            if len(parts) >= 2 and parts[1] not in ("all", "None"):
                lang = parts[1]
        if not lang:
            lang = (
                hit.rows[0].get("query_language")
                or hit.rows[0].get("_plan_language")
            )
        # Prefer scoped query language over mixed row.language when present
        if lang and lang not in ("all", "None") and lang not in found:
            found.append(str(lang))

    if not found and plan is not None:
        entities = list(getattr(plan, "entities", None) or [])
        if entities:
            return entities
        if getattr(plan, "language", None):
            return [plan.language]
    return found


def missing_entity_message(requested: list[str], retrieved: list[str]) -> str:
    missing = [r for r in requested if r not in retrieved]
    found = [r for r in requested if r in retrieved]
    if not found and missing:
        names = ", ".join(display_name(m) for m in missing)
        return (
            f"I could not find data for {names} in the lesson database."
        )
    found_txt = ", ".join(display_name(f) for f in found) or "none"
    missing_txt = ", ".join(display_name(m) for m in missing)
    return (
        f"I found data for {found_txt} but not for {missing_txt}."
    )


def validate_entity_coverage(plan, bundle) -> ResponseCheck:
    requested = list(getattr(plan, "entities", None) or [])
    retrieved = languages_from_bundle(bundle, plan)
    if len(requested) <= 1:
        # Single-language / lesson-scoped — coverage is about rows, not entities
        ok = bundle.row_count > 0
        return ResponseCheck(
            ok=ok,
            reason="single_scope" if ok else "no_rows",
            requested_languages=requested,
            retrieved_languages=retrieved,
            missing_languages=[],
            coverage_percent=100.0 if ok else 0.0,
            checks={
                "every_requested_language_answered": True,
                "has_rows": ok,
            },
        )

    missing = [r for r in requested if r not in retrieved]
    coverage = (100.0 * (len(requested) - len(missing)) / len(requested)) if requested else 0.0
    if missing:
        return ResponseCheck(
            ok=False,
            reason="missing_requested_languages",
            message=missing_entity_message(requested, retrieved),
            missing_languages=missing,
            retrieved_languages=retrieved,
            requested_languages=requested,
            coverage_percent=round(coverage, 1),
            checks={
                "every_requested_language_answered": False,
                "has_rows": bundle.row_count > 0,
                "no_skipped_entities": False,
            },
        )

    return ResponseCheck(
        ok=True,
        reason="all_entities_present",
        requested_languages=requested,
        retrieved_languages=retrieved,
        missing_languages=[],
        coverage_percent=100.0,
        checks={
            "every_requested_language_answered": True,
            "has_rows": True,
            "no_skipped_entities": True,
            "comparison_possible": len(retrieved) >= 2,
        },
    )


def validate_composed_response(
    reply: str,
    plan,
    bundle,
    entity_check: ResponseCheck,
) -> ResponseCheck:
    """
    Lightweight post-composition checks (no NLP claim extraction).
    Ensures multi-language answers mention each requested language display name
    when entities were requested.
    """
    requested = entity_check.requested_languages or list(getattr(plan, "entities", None) or [])
    checks = dict(entity_check.checks or {})
    text = (reply or "").lower()

    if not reply or not str(reply).strip():
        return ResponseCheck(
            ok=False,
            reason="empty_response",
            message="I could not compose a grounded answer from the retrieved facts.",
            missing_languages=entity_check.missing_languages,
            retrieved_languages=entity_check.retrieved_languages,
            requested_languages=requested,
            coverage_percent=entity_check.coverage_percent,
            checks={**checks, "non_empty": False},
        )

    # Forbidden hallucination markers the model sometimes emits when inventing
    banned = [
        "as an ai",
        "i made up",
        "based on my training data",
        "i don't have access to the database",
    ]
    if any(b in text for b in banned):
        return ResponseCheck(
            ok=False,
            reason="ungrounded_response_markers",
            message="The composed answer failed grounding checks.",
            missing_languages=entity_check.missing_languages,
            retrieved_languages=entity_check.retrieved_languages,
            requested_languages=requested,
            coverage_percent=entity_check.coverage_percent,
            checks={**checks, "no_invented_content_markers": False},
        )

    skipped = []
    if len(requested) > 1:
        for key in requested:
            label = display_name(key).lower()
            # Also accept raw key forms
            compact = key.replace("-", " ").lower()
            if label not in text and compact not in text and key.lower() not in text:
                skipped.append(key)
        checks["every_requested_language_answered"] = not skipped
        checks["no_skipped_entities"] = not skipped
        if skipped:
            return ResponseCheck(
                ok=False,
                reason="response_skipped_entities",
                message=missing_entity_message(requested, [r for r in requested if r not in skipped]),
                missing_languages=skipped,
                retrieved_languages=entity_check.retrieved_languages,
                requested_languages=requested,
                coverage_percent=entity_check.coverage_percent,
                checks=checks,
            )

    checks["non_empty"] = True
    checks["no_invented_content_markers"] = True
    return ResponseCheck(
        ok=True,
        reason="response_validated",
        requested_languages=requested,
        retrieved_languages=entity_check.retrieved_languages,
        missing_languages=[],
        coverage_percent=entity_check.coverage_percent,
        checks=checks,
    )
