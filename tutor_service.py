"""
AI Tutor chat — GPT-first learning companion.

Runtime path for ordinary chat / learning actions:
  user message + history + soft UI/action context
    → compose_general_tutor_response() / OpenAI
    → reply

Quiz action uses a separate interactive MCQ helper (quiz_service) for
clickable options; it does not reintroduce domain/database answer gating
for free-form chat.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from flask import session

from composer import compose_general_tutor_response
from conversation_memory import update_memory
from quiz_service import (
    active_quiz_card,
    grade_quiz_answer_structured,
    has_active_quiz,
    start_quiz,
)
from retrieval_log import build_audit, log_retrieval

logger = logging.getLogger(__name__)


def _mode_prompt(mode: str, lang_key=None, level_num=None) -> str:
    """Soft learning-action prompts (never hard-coded answer content)."""
    lang_bit = ""
    if lang_key:
        lang_bit = f" The learner is currently looking at {lang_key}"
        if level_num is not None:
            lang_bit += f" lesson {level_num}"
        lang_bit += "."

    if mode == "explain":
        return (
            "Learning action: Explain.\n"
            f"{lang_bit}\n"
            "If a clear language/linguistics topic is available from context or "
            "history, explain it using: (1) a simple explanation, (2) a concrete "
            "example, (3) a short takeaway. Adapt to a beginner-friendly level "
            "unless the learner seems advanced.\n"
            "If no specific topic is clear, ask: "
            "\"What language topic would you like me to explain?\""
        )
    if mode == "example":
        return (
            "Learning action: Example.\n"
            f"{lang_bit}\n"
            "Give a concrete example related to the current language/linguistics "
            "context. Use the structure CONCEPT → EXAMPLE → SHORT EXPLANATION. "
            "Do not only restate a definition.\n"
            "If no concept is clear, ask what concept they want an example for."
        )
    if mode == "culture":
        return (
            "Learning action: Culture.\n"
            f"{lang_bit}\n"
            "Provide a language-connected cultural explanation (community use, "
            "greetings, politeness, kinship terms, oral tradition, multilingualism, "
            "identity, or language preservation). Stay respectful. If you are "
            "uncertain about a specific factual claim, say so clearly."
        )
    if mode == "chat":
        return (
            "Learning action: Free Chat.\n"
            f"{lang_bit}\n"
            "Invite the learner to ask any language or linguistics question. "
            "Keep the reply short and welcoming; do not dump a long lecture yet."
        )
    return ""


def _gpt_unavailable_reply(composer_meta: Optional[dict] = None) -> str:
    meta = composer_meta or {}
    friendly = (meta.get("user_message") or "").strip()
    if friendly:
        return friendly
    return (
        "I couldn't reach the AI tutor service just now. "
        "Please try again in a moment."
    )


def answer_tutor_query(
    lang_key=None,
    level_num=None,
    user_message="",
    mode=None,
    history=None,
    user_id=None,
    debug: bool = False,
    ui_page: Optional[str] = None,
    quiz_continue: bool = False,
) -> dict[str, Any]:
    """
    Tutor chat entry point.

    Call graph for free-form / Explain / Example / Culture / Free Chat:
      answer_tutor_query → compose_general_tutor_response → OpenAI → reply

    Quiz action uses interactive MCQ helpers (still no planner/DB gate for chat).
    """
    history = list(history) if isinstance(history, list) else []
    started = time.time()

    normalized_mode = (mode or "").strip().lower()
    text = (user_message or "").strip()

    if user_id is None:
        try:
            user_id = session.get("user_id")
        except RuntimeError:
            # Outside a Flask request (scripts/tests): keep user_id unset.
            user_id = None

    composer_meta: dict[str, Any] = {}

    def _finish(
        reply: str,
        audit: dict,
        status: str = "ok",
        *,
        quiz: Optional[dict] = None,
        quiz_result: Optional[dict] = None,
    ) -> dict[str, Any]:
        audit["response_time_ms"] = int((time.time() - started) * 1000)
        log_retrieval(audit)
        debug_trace = None
        if debug:
            debug_trace = {
                "architecture": "gpt_first",
                "composer_meta": composer_meta,
                "history_turns": len(history),
                "action_mode": normalized_mode or None,
                "database_used": False,
                "gating": None,
            }
        return {
            "reply": reply,
            "audit": audit,
            "status": status,
            "no_evidence": None,
            "debug_trace": debug_trace,
            "answer": reply,
            "gpt_invoked": bool(audit.get("gpt_invoked")),
            "quiz": quiz,
            "quiz_result": quiz_result,
        }

    # ---- Active interactive quiz answer (click or typed option) ----
    if has_active_quiz() and text:
        state = session.get("tutor_quiz_state") or {}
        options = state.get("options") or []
        looks_like_answer = (
            text.isdigit()
            or text.lower() in {"a", "b", "c", "d", "e", "f"}
            or any(text.lower() == (opt or "").strip().lower() for opt in options)
        )
        if looks_like_answer:
            graded = grade_quiz_answer_structured(text, user_id=user_id)
            audit = build_audit(
                intent="quiz_grade",
                sql=["SESSION tutor_quiz_state + user_progress"],
                rows_returned=1,
                confidence=1.0,
                chosen_tables=["quiz", "user_progress"],
                gpt_invoked=False,
                validated=True,
                language=lang_key,
                lesson_id=level_num,
                mode=normalized_mode,
                reason="quiz_answer_graded",
            )
            return _finish(
                graded.get("reply") or "",
                audit,
                status="quiz_grade",
                quiz_result=graded.get("quiz_result"),
            )

    if normalized_mode == "quiz":
        # Prefer GPT-generated MCQ for the Tutor Quiz learning action.
        reply = start_quiz(
            lang_key,
            level_num,
            user_id=user_id,
            topic_text=text or None,
            history=history,
            prefer_gpt=True,
            quiz_continue=bool(quiz_continue),
        )
        card = active_quiz_card()
        quiz_state = session.get("tutor_quiz_state") or {}
        quiz_is_gpt = quiz_state.get("source") == "gpt_generated"
        update_memory(
            language=lang_key,
            lesson_id=level_num,
            topic="quiz",
            intent="QUIZ",
            knowledge_route="TUTOR_QUIZ_UI",
            last_query=text or "quiz",
            last_reply=reply,
        )
        audit = build_audit(
            intent="QUIZ",
            sql=[],
            rows_returned=1 if card else 0,
            confidence=1.0,
            chosen_tables=["quiz"],
            gpt_invoked=quiz_is_gpt,
            validated=True,
            language=lang_key,
            lesson_id=level_num,
            mode=normalized_mode,
            reason="tutor_quiz_card",
            extra={"prefer_gpt": True, "has_card": bool(card)},
        )
        # Prefer a short intro when a clickable card is available.
        intro = "Here's a quick check. Choose an option below."
        return _finish(
            intro if card else reply,
            audit,
            status="quiz",
            quiz=card,
        )

    # Empty non-quiz modes: use soft learning-action prompts
    if not text and normalized_mode in ("explain", "example", "culture", "chat"):
        text = _mode_prompt(normalized_mode, lang_key, level_num)

    if not text:
        audit = build_audit(
            intent="empty",
            sql=[],
            rows_returned=0,
            confidence=0.0,
            chosen_tables=[],
            gpt_invoked=False,
            validated=False,
            language=lang_key,
            lesson_id=level_num,
            mode=normalized_mode,
            reason="empty_message",
        )
        return _finish(
            "Ask me anything about languages or linguistics — or choose Explain, "
            "Example, Quiz, Culture, or Free Chat.",
            audit,
            status="empty",
        )

    # ---- USER → GPT → ANSWER ----
    composed = compose_general_tutor_response(
        user_question=text,
        history=history,
        ui_language=lang_key,
        ui_lesson=level_num,
        action_mode=normalized_mode or None,
        ui_page=ui_page,
    )
    composer_meta = {
        "invoked": bool(composed.get("ok")),
        "composer_mode": composed.get("composer_mode"),
        "composer_reason": composed.get("composer_reason"),
        "latency_ms": composed.get("latency_ms") or 0,
        "error": composed.get("error"),
        "user_message": composed.get("user_message"),
        "architecture": "gpt_first",
        "action_mode": normalized_mode or None,
        "database_used": False,
    }

    if composed.get("ok") and composed.get("reply"):
        reply = composed["reply"]
        update_memory(
            language=lang_key,
            lesson_id=level_num,
            topic=normalized_mode or "general_tutor",
            intent="GENERAL_TUTOR",
            knowledge_route="GPT_FIRST",
            last_query=text,
            last_reply=reply,
        )
        audit = build_audit(
            intent="GENERAL_TUTOR",
            sql=[],
            rows_returned=0,
            confidence=0.9,
            chosen_tables=[],
            gpt_invoked=True,
            validated=True,
            language=lang_key,
            lesson_id=level_num,
            mode=normalized_mode,
            reason="gpt_first_direct",
            extra={
                "architecture": "gpt_first",
                "composer": composer_meta,
                "history_turns": len(history),
                "database_used": False,
                "gating": None,
            },
        )
        return _finish(reply, audit, status="ok")

    reply = _gpt_unavailable_reply(composed)
    update_memory(
        language=lang_key,
        lesson_id=level_num,
        topic="general_tutor",
        intent="GENERAL_TUTOR",
        knowledge_route="GPT_FIRST_UNAVAILABLE",
        last_query=text,
        last_reply=reply,
    )
    audit = build_audit(
        intent="GENERAL_TUTOR",
        sql=[],
        rows_returned=0,
        confidence=0.0,
        chosen_tables=[],
        gpt_invoked=False,
        validated=False,
        language=lang_key,
        lesson_id=level_num,
        mode=normalized_mode,
        reason=composed.get("composer_reason") or "composer_failed",
        extra={
            "architecture": "gpt_first",
            "composer": composer_meta,
            "database_used": False,
            "gating": None,
        },
    )
    return _finish(reply, audit, status="composer_unavailable")


def get_tutor_reply(
    lang_key=None,
    level_num=None,
    user_message="",
    system_prompt=None,
    mode=None,
    history=None,
) -> str:
    del system_prompt
    result = answer_tutor_query(
        lang_key=lang_key,
        level_num=level_num,
        user_message=user_message,
        mode=mode,
        history=history,
    )
    return result["reply"]
