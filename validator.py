"""
Validator: reject weak/incomplete evidence before any LLM rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from planner import (
    CONVERSATION,
    CONVERSATION_INSUFFICIENT,
    TEACHING,
    TRANSLATION,
    TRANSLATION_INSUFFICIENT,
)


NO_EVIDENCE_MESSAGE = (
    "No evidence found in the lesson database for this query."
)

TOPIC_MISSING_MESSAGE = (
    "This topic is not yet included in the current lesson database."
)


@dataclass
class ValidationResult:
    ok: bool
    confidence: float
    reason: str
    message: str
    evidence_rows: int
    tables: list[str]
    missing_requirements: list[str]


def _row_richness(row: dict) -> float:
    if not row:
        return 0.0
    score = 0.2
    if row.get("word") and (row.get("meaning_en") or row.get("meaning_ms")):
        score += 0.5
    if row.get("title") and (row.get("content") or row.get("explanation")):
        score += 0.5
    if row.get("question") and row.get("correct_answer"):
        score += 0.5
    if row.get("example_sentence") or row.get("ipa") or row.get("examples"):
        score += 0.15
    if row.get("part_of_speech") or row.get("difficulty"):
        score += 0.1
    if row.get("count") is not None:
        score += 0.5
    return min(1.0, score)


def validate_evidence(
    plan,
    bundle,
) -> ValidationResult:
    """
    Deterministic gate using the execution plan requirements.
    """
    tables = list(getattr(plan, "required_tables", None) or bundle.tables or [])
    rows = list(bundle.rows or [])
    count = len(rows)
    missing: list[str] = []
    intent = getattr(plan, "intent", "") or bundle.intent

    # Required ops must return rows
    for hit in bundle.hits:
        if hit.required and not hit.rows:
            missing.append(f"required_op:{hit.name}")

    # Required tables present in hits with data
    for table in tables:
        table_rows = [r for r in rows if r.get("_source_table") == table]
        if not table_rows and any(h.table == table and h.required for h in bundle.hits):
            missing.append(f"required_table:{table}")

    # Required fields on at least some rows
    for field in getattr(plan, "required_fields", None) or []:
        if not any((r.get(field) not in (None, "")) for r in rows):
            missing.append(f"required_field:{field}")

    min_rows = int(getattr(plan, "min_rows", 1) or 1)

    # Translation coverage tiers:
    # 0% → no_evidence
    # >0% → allow (composer highlights missing tokens; never invent)
    if intent == TRANSLATION:
        coverage = bundle.coverage or {}
        ratio = float(coverage.get("coverage_ratio") or 0.0)
        missing_tokens = coverage.get("missing") or []
        if count == 0 or ratio <= 0.0:
            return ValidationResult(
                ok=False,
                confidence=ratio,
                reason="translation_zero_coverage",
                message=TRANSLATION_INSUFFICIENT,
                evidence_rows=count,
                tables=tables,
                missing_requirements=missing_tokens or missing,
            )

    if intent == CONVERSATION and count < 4:
        return ValidationResult(
            ok=False,
            confidence=0.2,
            reason="conversation_insufficient_vocab",
            message=CONVERSATION_INSUFFICIENT,
            evidence_rows=count,
            tables=tables,
            missing_requirements=missing,
        )

    if intent == TEACHING:
        # Only enforce greeting evidence when the plan requested greetings
        # (introduction / hello teaching), not for all teaching-shaped intents.
        wants_greetings = any(
            getattr(op, "name", "") == "greetings"
            or (getattr(op, "params", None) or {}).get("part_of_speech") == "greeting"
            for op in (getattr(plan, "operations", None) or [])
        )
        greetings = bundle.rows_for("greetings")
        grammar = bundle.rows_for("grammar")
        if wants_greetings and not greetings:
            missing.append("greetings")
            return ValidationResult(
                ok=False,
                confidence=0.15,
                reason="teaching_missing_greetings",
                message=NO_EVIDENCE_MESSAGE,
                evidence_rows=count,
                tables=tables,
                missing_requirements=missing,
            )
        if not grammar:
            missing.append("grammar")

    if count == 0:
        message = (
            TOPIC_MISSING_MESSAGE
            if getattr(bundle, "require_topic_match", False)
            else NO_EVIDENCE_MESSAGE
        )
        return ValidationResult(
            ok=False,
            confidence=0.0,
            reason="zero_rows",
            message=message,
            evidence_rows=0,
            tables=tables,
            missing_requirements=missing,
        )

    if count < min_rows:
        return ValidationResult(
            ok=False,
            confidence=0.2,
            reason="too_few_rows",
            message=NO_EVIDENCE_MESSAGE,
            evidence_rows=count,
            tables=tables,
            missing_requirements=missing + [f"min_rows:{min_rows}"],
        )

    if missing and any(m.startswith("required_op:") or m.startswith("required_table:") for m in missing):
        # Soft-required optional ops should not fail; only required ones.
        hard = [m for m in missing if m.startswith("required_op:") or m.startswith("required_table:")]
        # Check if those ops were actually marked required
        hard_fail = []
        for m in hard:
            name = m.split(":", 1)[1]
            if m.startswith("required_op:"):
                hit = next((h for h in bundle.hits if h.name == name), None)
                if hit and hit.required:
                    hard_fail.append(m)
            else:
                hard_fail.append(m)
        if hard_fail and count == 0:
            return ValidationResult(
                ok=False,
                confidence=0.1,
                reason="missing_requirements",
                message=NO_EVIDENCE_MESSAGE,
                evidence_rows=count,
                tables=tables,
                missing_requirements=hard_fail,
            )

    richness = sum(_row_richness(r) for r in rows) / max(1, count)
    volume = min(1.0, 0.45 + 0.08 * count)
    confidence = round(min(0.99, 0.55 * volume + 0.45 * richness), 3)

    if intent in ("LONGEST_WORD", "SHORTEST_WORD", "STATISTICS", "RANKING", "ANALYTICS", "COMPARE") and count >= 1:
        confidence = max(confidence, 0.92)
    if intent == "QUIZ" and count >= 1:
        confidence = max(confidence, 0.85)
    if intent == "ANALYTICS" and count >= 1:
        confidence = max(confidence, 0.9)
    if intent == TRANSLATION:
        confidence = max(confidence, float((bundle.coverage or {}).get("coverage_ratio") or 0))

    plan_confidence = float(getattr(plan, "confidence", 0.5) or 0.5)
    confidence = round(min(0.99, 0.6 * confidence + 0.4 * plan_confidence), 3)

    if confidence < 0.35:
        return ValidationResult(
            ok=False,
            confidence=confidence,
            reason="low_confidence",
            message=NO_EVIDENCE_MESSAGE,
            evidence_rows=count,
            tables=tables,
            missing_requirements=missing,
        )

    return ValidationResult(
        ok=True,
        confidence=confidence,
        reason="evidence_accepted",
        message="validated",
        evidence_rows=count,
        tables=tables,
        missing_requirements=[],
    )


def no_evidence_payload(
    intent: str,
    tables: list[str],
    sql_statements: list[str],
    validation: ValidationResult,
    gpt_invoked: bool = False,
) -> dict[str, Any]:
    return {
        "status": "no_evidence",
        "message": validation.message or NO_EVIDENCE_MESSAGE,
        "intent": intent,
        "tables_searched": tables,
        "sql": sql_statements,
        "rows_returned": validation.evidence_rows,
        "confidence": validation.confidence,
        "gpt_invoked": gpt_invoked,
        "reason": validation.reason,
        "missing_requirements": validation.missing_requirements,
    }
