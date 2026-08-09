"""Append-only retrieval audit log for the AI Tutor pipeline."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Optional

_LOCK = threading.Lock()
_LAST_AUDIT: Optional[dict[str, Any]] = None

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_PATH = os.path.join(LOG_DIR, "tutor_retrieval.jsonl")


def last_audit() -> Optional[dict[str, Any]]:
    return _LAST_AUDIT


def build_audit(
    *,
    intent: str,
    sql: list[str],
    rows_returned: int,
    confidence: float,
    chosen_tables: list[str],
    gpt_invoked: bool,
    validated: bool,
    language: Optional[str] = None,
    lesson_id: Optional[int] = None,
    mode: Optional[str] = None,
    reason: str = "",
    extra: Optional[dict[str, Any]] = None,
    response_time_ms: Optional[int] = None,
) -> dict[str, Any]:
    audit = {
        "ts": time.time(),
        "intent": intent,
        "sql": sql,
        "rows_returned": rows_returned,
        "confidence": confidence,
        "chosen_tables": chosen_tables,
        "gpt_invoked": gpt_invoked,
        "validated": validated,
        "language": language,
        "lesson_id": lesson_id,
        "mode": mode,
        "reason": reason,
        "response_time_ms": response_time_ms,
    }
    if extra:
        # Flatten key planner/validator fields for easier grepping
        planner = extra.get("planner") or {}
        if planner:
            audit["planner_output"] = {
                "intent": planner.get("intent"),
                "confidence": planner.get("confidence"),
                "entities": planner.get("entities"),
                "scope": planner.get("scope"),
                "operation": planner.get("operation"),
                "execution_steps": planner.get("execution_steps"),
                "required_tables": planner.get("required_tables"),
                "required_fields": planner.get("required_fields"),
                "need_reasoning": planner.get("need_reasoning"),
                "need_generation": planner.get("need_generation"),
                "operations": planner.get("operations"),
                "notes": planner.get("notes"),
                "response_type": planner.get("response_type"),
                "unsupported": planner.get("unsupported"),
            }
            audit["entities"] = planner.get("entities")
            audit["scope"] = planner.get("scope")
            audit["execution_steps"] = planner.get("execution_steps")
            audit["response_type"] = planner.get("response_type")
        if extra.get("validator"):
            audit["validator_result"] = extra["validator"]
        if extra.get("composer"):
            composer = extra["composer"]
            audit["composer"] = composer
            audit["composer_mode"] = composer.get("composer_mode")
            audit["composer_reason"] = composer.get("composer_reason") or composer.get("reason")
            audit["composer_prompt_length"] = composer.get("composer_prompt_length")
            audit["tokens_estimate"] = composer.get("tokens_estimate")
            audit["composer_latency_ms"] = composer.get("latency_ms")
            audit["fallback_used"] = composer.get("fallback_used")
            audit["fallback_reason"] = composer.get("reason") if composer.get("fallback_used") else None
        for key in (
            "planner_languages_detected",
            "planner_entities",
            "requested_languages",
            "retrieved_languages",
            "missing_languages",
            "coverage_percent",
            "composer_sections_generated",
        ):
            if key in extra:
                audit[key] = extra[key]
        if extra.get("debug"):
            audit["debug"] = extra["debug"]
        if "coverage" in extra:
            audit["coverage"] = extra["coverage"]
        audit["extra"] = {
            k: v for k, v in extra.items()
            if k not in (
                "planner", "validator", "debug", "composer",
                "planner_languages_detected", "planner_entities",
                "requested_languages", "retrieved_languages",
                "missing_languages", "coverage_percent",
                "composer_sections_generated",
            )
        }
    return audit


def log_retrieval(audit: dict[str, Any]) -> dict[str, Any]:
    global _LAST_AUDIT
    with _LOCK:
        _LAST_AUDIT = audit
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(audit, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass
    return audit
