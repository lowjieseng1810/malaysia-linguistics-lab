"""
LLM Composer — GPT teaching layer for the AI Tutor.

Primary path (GPT-first):
  compose_general_tutor_response() — direct educational answers, no DB gate.

Legacy evidence-mode helpers (compose_response) remain for optional tooling /
older call sites, but the live tutor chat path must not require them.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import traceback
from typing import Any, Optional

from language_registry import display_name
from planner import (
    ANALYTICS,
    COMPARE,
    CONVERSATION,
    CULTURE,
    EXAMPLE_SENTENCE,
    EXPLANATION,
    GRAMMAR_EXPLANATION,
    LESSON_SUMMARY,
    LINGUISTICS,
    MORPHOLOGY,
    PRONUNCIATION,
    RANKING,
    SEMANTICS,
    STATISTICS,
    SYNTAX,
    TEACHING,
    TRANSLATION,
)

logger = logging.getLogger(__name__)

_MAX_FACTS_CHARS = 14000
_PLACEHOLDER_KEYS = {
    "",
    "your_openai_api_key_here",
    "sk-your-key",
    "changeme",
}


def refresh_composer_enabled() -> bool:
    """Re-read enable flag (call after load_dotenv)."""
    global COMPOSER_ENABLED
    raw = (
        os.getenv("TUTOR_LLM_COMPOSER")
        or os.getenv("TUTOR_LLM_REWRITE")
        or "true"
    ).strip().lower()
    COMPOSER_ENABLED = raw == "true"
    return COMPOSER_ENABLED


COMPOSER_ENABLED = True
refresh_composer_enabled()


def get_api_key() -> str:
    """Accept OPENAI_API_KEY or AI_TUTOR_API_KEY."""
    key = (
        (os.getenv("OPENAI_API_KEY") or "").strip()
        or (os.getenv("AI_TUTOR_API_KEY") or "").strip()
    )
    if key.lower() in _PLACEHOLDER_KEYS:
        return ""
    return key


def get_model_name() -> str:
    """Accept OPENAI_MODEL or AI_TUTOR_MODEL."""
    return (
        (os.getenv("OPENAI_MODEL") or "").strip()
        or (os.getenv("AI_TUTOR_MODEL") or "").strip()
        or "gpt-4o-mini"
    )


def _classify_exception(exc: BaseException) -> str:
    """Map SDK/network errors to stable reason codes for logs + UX."""
    text = f"{type(exc).__name__}: {exc}".lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status in (401, 403) or "invalid_api_key" in text or "incorrect api key" in text:
        return "invalid_api_key"
    if status == 404 or "model_not_found" in text or "does not exist" in text and "model" in text:
        return "model_unavailable"
    if status in (429,) or "rate_limit" in text:
        return "responses_api_error"
    if any(
        token in text
        for token in (
            "connection",
            "timeout",
            "timed out",
            "network",
            "name or service not known",
            "temporarily unavailable",
            "connecterror",
        )
    ):
        return "network_error"
    if "api" in text or status is not None:
        return "responses_api_error"
    return "responses_api_error"


def _friendly_user_message(reason: str) -> str:
    mapping = {
        "missing_api_key": (
            "The AI tutor could not reach GPT because no API key is configured. "
            "Set OPENAI_API_KEY or AI_TUTOR_API_KEY on the server."
        ),
        "invalid_api_key": (
            "The AI tutor could not authenticate with GPT (invalid API key). "
            "Please ask the site administrator to check the API key."
        ),
        "model_unavailable": (
            "The configured GPT model is unavailable. "
            "Please ask the site administrator to check OPENAI_MODEL / AI_TUTOR_MODEL."
        ),
        "network_error": (
            "The AI tutor could not reach OpenAI due to a network problem. "
            "Please try again in a moment."
        ),
        "responses_api_error": (
            "The AI tutor hit an error calling the OpenAI Responses API. "
            "Please try again shortly."
        ),
        "composer_disabled": (
            "The GPT composer is disabled on this server "
            "(TUTOR_LLM_COMPOSER=false)."
        ),
        "sdk_import_error": (
            "The OpenAI Python SDK is not installed on this server."
        ),
        "empty_output": (
            "GPT returned an empty reply. Please try asking again."
        ),
        "no_api_client": (
            "The AI tutor could not initialize the GPT client."
        ),
    }
    return mapping.get(
        reason,
        "The AI tutor could not generate a GPT reply right now. Please try again.",
    )


def _client():
    """
    Build OpenAI client or return (None, reason).
    reason: missing_api_key | sdk_import_error | None on success
    """
    api_key = get_api_key()
    if not api_key:
        return None, "missing_api_key"
    try:
        from openai import OpenAI
    except ImportError as exc:
        logger.error(
            "Composer OpenAI SDK import failed: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return None, "sdk_import_error"
    return OpenAI(api_key=api_key), None


def composer_status() -> dict[str, Any]:
    refresh_composer_enabled()
    key = get_api_key()
    model = get_model_name()
    client, reason = _client() if COMPOSER_ENABLED else (None, "composer_disabled")
    ready = bool(COMPOSER_ENABLED and client is not None)
    return {
        "enabled": bool(COMPOSER_ENABLED),
        "api_key_loaded": bool(key),
        "model": model,
        "responses_api_ready": ready,
        "init_reason": reason,
    }


def print_composer_startup_status() -> dict[str, Any]:
    status = composer_status()
    print(
        "Composer:\n"
        f"Enabled: {str(status['enabled']).lower()}\n"
        f"API key loaded: {'yes' if status['api_key_loaded'] else 'no'}\n"
        f"Model: {status['model']}\n"
        f"Responses API ready: {'yes' if status['responses_api_ready'] else 'no'}"
    )
    if not status["responses_api_ready"]:
        logger.warning(
            "Composer not ready at startup: enabled=%s api_key_loaded=%s reason=%s",
            status["enabled"],
            status["api_key_loaded"],
            status.get("init_reason"),
        )
    return status


def run_composer_health_check() -> dict[str, Any]:
    """
    Tiny Responses API probe. Prints PASS/FAIL.
    Does not raise — returns a result dict for callers.
    """
    refresh_composer_enabled()
    if not COMPOSER_ENABLED:
        msg = "Composer health check: FAIL (composer disabled)"
        print(msg)
        logger.error(msg)
        return {"ok": False, "reason": "composer_disabled"}

    client, reason = _client()
    if client is None:
        msg = f"Composer health check: FAIL ({reason or 'missing_api_key'})"
        print(msg)
        logger.error(msg)
        return {"ok": False, "reason": reason or "missing_api_key"}

    model = get_model_name()
    try:
        response = _create_responses_call(
            client,
            model=model,
            input_messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: OK",
                }
            ],
            max_output_tokens=16,
            temperature=0,
        )
        text = _extract_reply(response)
        if not text:
            msg = "Composer health check: FAIL (empty_output)"
            print(msg)
            logger.error("%s raw=%r", msg, response)
            return {"ok": False, "reason": "empty_output"}
        msg = "Composer health check: PASS"
        print(msg)
        logger.info("%s model=%s reply=%r", msg, model, text[:80])
        return {"ok": True, "reason": "ok", "reply": text}
    except Exception as exc:
        reason = _classify_exception(exc)
        msg = f"Composer health check: FAIL ({reason})"
        print(msg)
        logger.error(
            "%s model=%s exception=%s\n%s",
            msg,
            model,
            exc,
            traceback.format_exc(),
        )
        return {
            "ok": False,
            "reason": reason,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }


def _fail(
    *,
    mode: str,
    evidence_mode: str,
    reason: str,
    error: str,
    started: float,
    prompt_length: int = 0,
    tokens_estimate: int = 0,
    exc: BaseException | None = None,
) -> dict[str, Any]:
    """Log failure loudly and return a structured compose failure."""
    if exc is not None:
        logger.error(
            "Composer failure reason=%s error=%s\n%s",
            reason,
            error,
            traceback.format_exc(),
        )
    else:
        logger.error("Composer failure reason=%s error=%s", reason, error)
    return {
        "ok": False,
        "error": error,
        "composer_mode": mode,
        "composer_reason": reason,
        "user_message": _friendly_user_message(reason),
        "composer_prompt_length": prompt_length,
        "latency_ms": int((time.time() - started) * 1000),
        "tokens_estimate": tokens_estimate,
        "evidence_mode": evidence_mode,
        "logged": True,
    }


def _create_responses_call(
    client,
    *,
    model: str,
    input_messages: list,
    max_output_tokens: int,
    temperature: Optional[float] = None,
):
    """
    Call Responses API with model-compatible parameters.
    Some models (e.g. gpt-5.x) reject temperature — omit / retry without it.
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "input": input_messages,
        "max_output_tokens": max_output_tokens,
    }
    model_l = (model or "").lower()
    supports_temperature = not (
        model_l.startswith("gpt-5") or model_l.startswith("o1") or model_l.startswith("o3")
    )
    if temperature is not None and supports_temperature:
        kwargs["temperature"] = temperature
    try:
        return client.responses.create(**kwargs)
    except Exception as exc:
        err = str(exc).lower()
        if "temperature" in err and "temperature" in kwargs:
            logger.warning(
                "Model %s rejected temperature; retrying without it. error=%s",
                model,
                exc,
            )
            kwargs.pop("temperature", None)
            return client.responses.create(**kwargs)
        raise


def _extract_reply(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    chunks = []
    for item in getattr(response, "output", None) or []:
        for content in getattr(item, "content", None) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
            elif isinstance(text, dict):
                value = text.get("value")
                if isinstance(value, str) and value.strip():
                    chunks.append(value.strip())
    return "\n".join(chunks).strip()


def composer_mode_for(plan, evidence_mode: str = "database") -> str:
    if evidence_mode == "linguistics":
        return "linguistics_only"
    if evidence_mode == "hybrid":
        return "hybrid"
    intent = getattr(plan, "intent", "") or ""
    if intent == TEACHING or intent == EXPLANATION:
        return "teaching"
    if intent == TRANSLATION:
        return "translation"
    if intent == CONVERSATION:
        return "conversation"
    if intent in (COMPARE, ANALYTICS, STATISTICS, RANKING) or getattr(plan, "response_type", "") in (
        "comparison",
        "analytics",
    ):
        return "analytics_compare"
    if intent == GRAMMAR_EXPLANATION:
        return "grammar"
    if intent == EXAMPLE_SENTENCE:
        return "example"
    if intent == CULTURE:
        return "culture"
    if intent == LESSON_SUMMARY:
        return "lesson_summary"
    if intent in (LINGUISTICS, MORPHOLOGY, SYNTAX, SEMANTICS, PRONUNCIATION):
        return "linguistics"
    return "general"


def _sanitize_rows(rows: list[dict], limit: int = 40) -> list[dict]:
    clean = []
    drop = {"audio_path", "image_path"}
    for row in rows[:limit]:
        item = {
            k: v for k, v in dict(row).items()
            if not str(k).startswith("_") and k not in drop and v not in (None, "")
        }
        if item:
            clean.append(item)
    return clean


def build_composer_payload(
    *,
    user_question: str,
    plan,
    bundle,
    validation,
    coaching_note: str = "",
    evidence_mode: str = "database",
    knowledge_route: Optional[dict] = None,
) -> dict[str, Any]:
    """Rich RAG / linguistics context for the LLM composer."""
    facts_by_source = {
        name: _sanitize_rows(rows)
        for name, rows in (getattr(bundle, "by_name", None) or {}).items()
    }
    languages = list(getattr(plan, "entities", None) or [])
    if not languages and getattr(plan, "language", None):
        languages = [plan.language]
    mode_hint = composer_mode_for(plan, evidence_mode)

    return {
        "user_question": user_question,
        "evidence_mode": evidence_mode,
        "knowledge_route": knowledge_route or {},
        "planner": {
            "intent": plan.intent,
            "operation": plan.operation,
            "reasoning_notes": plan.notes,
            "entities": plan.entities,
            "languages": [display_name(x) for x in languages],
            "language_keys": languages,
            "scope": plan.scope,
            "execution_steps": plan.execution_steps,
            "analytics_kind": plan.analytics_kind,
            "compare_metric": plan.compare_metric,
            "query_spec": getattr(plan, "query_spec", None) or {},
            "knowledge_policy": getattr(plan, "knowledge_policy", "database_first"),
            "source_text": plan.source_text,
            "tokens": plan.tokens,
            "confidence": plan.confidence,
            "response_type": plan.response_type,
        },
        "retrieved_facts": {
            "by_source": facts_by_source,
            "all_rows": _sanitize_rows(getattr(bundle, "rows", None) or [], limit=50),
            "row_count": getattr(bundle, "row_count", 0) or 0,
            "coverage": getattr(bundle, "coverage", None) or {},
        },
        "sql_summary": list(getattr(bundle, "sql_statements", None) or []),
        "validation": {
            "ok": getattr(validation, "ok", True),
            "confidence": getattr(validation, "confidence", 1.0),
            "reason": getattr(validation, "reason", ""),
            "evidence_rows": getattr(validation, "evidence_rows", 0),
            "tables": getattr(validation, "tables", None) or [],
            "missing_requirements": getattr(validation, "missing_requirements", None) or [],
        },
        "response_constraints": {
            "sqlite_is_only_lesson_knowledge_source": True,
            "may_not_invent_vocabulary": True,
            "may_not_invent_translations": True,
            "may_not_invent_grammar": True,
            "may_not_invent_culture": True,
            "may_not_invent_ipa": True,
            "may_not_invent_examples": True,
            "if_missing_say_database_lacks_info": True,
            "must_cover_every_requested_language": (
                len(languages) > 1 and evidence_mode != "linguistics"
            ),
            "requested_language_keys": languages,
            "coaching_note": coaching_note or None,
            "evidence_mode": evidence_mode,
            "composer_sections_preferred": (
                ["## Course database information", "## General linguistic knowledge"]
                if evidence_mode == "hybrid"
                else (
                    ["Definition", "Explanation", "Simple example", "Key terms"]
                    if evidence_mode == "linguistics"
                    else (
                        ["Summary", "Per-language results", "Comparison", "Observations"]
                        if mode_hint == "analytics_compare"
                        else (
                            [
                                "Definition",
                                "Explanation",
                                "Vocabulary",
                                "Grammar",
                                "Examples",
                                "Common mistakes",
                                "Practice tip",
                            ]
                            if mode_hint in ("teaching", "linguistics", "hybrid")
                            else []
                        )
                    )
                )
            ),
            "knowledge_policy": getattr(plan, "knowledge_policy", "database_first"),
        },
    }


_FOLLOWUP_ADDENDUM = """
FOLLOW-UP TURN
This message is a natural continuation of the conversation above (conversation
history is included as prior turns). Use that history to understand what
"it"/"that"/"another one" refers to instead of re-explaining from scratch.
Respond conversationally and directly — you do NOT need to force the rigid
"Course database information" / "General linguistic knowledge" section split
for a short follow-up unless the user is asking to compare specific course
facts. If asked for "another example", produce a genuinely NEW example,
different from any already given in the conversation; it does not need to
exist in the course database — just don't claim it does (e.g. you may add a
short parenthetical like "(new example, not from the course database)" when
you generate one). If asked to make something "easier" or "harder", adjust
the depth/vocabulary of your explanation accordingly rather than repeating
the previous answer unchanged.
"""


def _system_prompt(mode: str, evidence_mode: str = "database", is_followup: bool = False) -> str:
    mission = (
        "MISSION\n"
        "Malaysia Linguistics Lab + Language Learning + Linguistics Education.\n"
        "You are NOT a general chatbot. Stay within language learning and linguistics.\n"
    )

    if evidence_mode == "linguistics":
        text = (
            "You are an educational tutor for Malaysia Linguistics Lab.\n\n"
            + """
EVIDENCE MODE: GENERAL EDUCATIONAL KNOWLEDGE (GPT)

You may answer:
1) Language-learning and linguistics questions
2) General educational questions (mathematics, economics, computer-science
   concepts, science, study skills)
3) How this website/product works (Achievements, Passport, Dictionary, Quiz,
   Explorer, Settings, AI Tutor, mascot)

Behave like a careful educator:
- Use accurate terminology
- Give structured explanations
- Include simple examples where helpful
- Adapt depth to the learner's apparent level
- Be clear and educational

YOU MUST NOT
- Invent Malaysian minority-language lesson vocabulary, grammar, culture notes,
  IPA, rankings, or translations as if they came from this course database
- Pretend you retrieved SQLite facts for a heritage language when none were provided
- Answer unsafe requests (hacking, passwords, phishing) or pure entertainment
  trivia (sports scores, celebrity gossip, crypto tips, weather)

IMPORTANT
Do NOT say "the course database does not contain this" for ordinary educational
or website questions. That phrase is ONLY for unsupported heritage-language
lesson facts.

FORMAT
Use short markdown sections, e.g. Definition → Explanation → Simple example → Key terms.
"""
        )
        return text + (_FOLLOWUP_ADDENDUM if is_followup else "")

    if evidence_mode == "hybrid":
        text = (
            "You are a university linguistics lecturer and Malaysian heritage language tutor.\n\n"
            + mission
            + """
EVIDENCE MODE: HYBRID — Course database + General linguistic knowledge

Restrict by DOMAIN, not by knowledge source.
Answer language / linguistics questions fluently. The course database is
authoritative ONLY for lesson-specific facts.

You MUST structure the answer with these two clearly separated sections:

## Course database information
Only facts from retrieved SQLite rows / validation package.
If retrieval is empty or incomplete, say explicitly that the course database
does not contain that lesson-specific information. Never invent it.

## General linguistic knowledge
Educational linguistics explanation from your linguistic expertise.
Never present this as course-database content.

RULES
- NEVER invent lesson vocabulary, grammar, examples, culture, or IPA
- NEVER mix the two sections together
- NEVER claim a general fact is from the database
- If lesson rows are missing, still teach the general linguistic part
- Keep the mission focused on heritage languages + linguistics education
- Use accurate terminology and structured explanations
"""
        )
        return text + (_FOLLOWUP_ADDENDUM if is_followup else "")

    base = (
        "You are the teaching composer for Malaysia Linguistics Lab.\n\n"
        + mission
        + """
EVIDENCE MODE: COURSE DATABASE (lesson facts)

ROLE
You are a warm university-style language tutor.
SQLite retrieved rows are the single source of truth for lesson-specific content
(vocabulary, grammar rows, examples, culture, quiz items, lesson IPA).

YOU MAY
- Understand complicated / natural English questions
- Merge multiple SQL result sets
- Compare languages using retrieved numbers and words
- Explain grammar, vocabulary, examples, and culture that appear in the facts
- Produce educational answers (headings, bullets, short tables)

YOU MUST NOT
- Invent vocabulary, translations, grammar, culture, IPA, or examples
- Use world knowledge to fabricate lesson-specific gaps
- Answer off-domain topics

IF LESSON INFORMATION IS MISSING
Say clearly that the course database does not contain it.
Do not guess lesson facts.

FORMAT
Prefer clear markdown with short sections. Be concise but complete.
"""
    )

    mode_extra = {
        "analytics_compare": (
            "\nMODE: ANALYTICS / COMPARE\n"
            "Cover EVERY language in planner.languages — never skip one.\n"
            "Structure: Summary → Per-language results → Comparison → Observations.\n"
            "Use ONLY retrieved metrics and words."
        ),
        "grammar": "\nMODE: GRAMMAR\nTeach using retrieved grammar + supporting vocabulary only.",
        "example": "\nMODE: EXAMPLE\nBuild examples from retrieved sentences / words only.",
        "culture": "\nMODE: CULTURE\nExplain only retrieved culture rows.",
        "lesson_summary": (
            "\nMODE: LESSON SUMMARY\nSummarize from retrieved vocabulary, grammar, culture."
        ),
        "teaching": (
            "\nMODE: TEACHING\n"
            "Prefer: Definition → Explanation → Vocabulary → Grammar → Examples → "
            "Common mistakes → Practice tip. Omit missing sections."
        ),
        "translation": (
            "\nMODE: TRANSLATION\n"
            "Use coverage in retrieved_facts.coverage. Never invent missing tokens."
        ),
        "conversation": (
            "\nMODE: CONVERSATION\nOnly use retrieved local-language vocabulary."
        ),
        "linguistics": (
            "\nMODE: LINGUISTICS (database-first)\n"
            "Prefer retrieved facts; if empty, say the database lacks evidence."
        ),
        "general": "\nMODE: GENERAL\nAnswer using retrieved facts as a careful tutor.",
    }.get(mode, "")

    return base + mode_extra + (_FOLLOWUP_ADDENDUM if is_followup else "")


_GENERAL_TUTOR_SYSTEM = """You are the language and linguistics tutor inside Malaysia Linguistics Lab.

PRIMARY FOCUS
Help with languages, linguistics, and language learning, including:
vocabulary, grammar, pronunciation, writing systems, language families,
phonetics, phonology, morphology, syntax, semantics, pragmatics, etymology,
sociolinguistics, language preservation, Malaysian heritage languages, and
Malaysian language/culture topics connected to language.

HOW TO TEACH
- Answer language/linguistics questions directly and clearly.
- Adapt to the learner's apparent level.
- Prefer concrete examples when helpful.
- Handle multi-part questions in one coherent reply.
- Use conversation history for follow-ups ("why?", "example?", "explain more").
- If uncertain about a specific heritage-language or cultural fact, say so briefly
  and still offer a careful, useful explanation — never invent citations.

LEARNING ACTIONS (when mentioned in the user message)
- Explain: simple explanation → concrete example → short takeaway
- Example: CONCEPT → EXAMPLE → SHORT EXPLANATION (do not only restate a definition)
- Culture: connect language to community, greetings, politeness, kinship, oral
  tradition, multilingualism, identity, or preservation — stay language-linked
  and respectful; mark uncertainty instead of inventing specific cultural claims
- Free chat: answer natural language/linguistics questions

OUT OF SCOPE
If the user asks something clearly unrelated to languages/linguistics
(for example general coding homework, economics, physics, gaming, or
unrelated entertainment), do NOT become a general-purpose assistant.
Reply briefly and politely that you are a language and linguistics tutor and
invite a language-related question. Use wording close to:
"I'm your language and linguistics tutor, so I'm best at questions about
languages, linguistics, language learning, and Malaysian language heritage.
Ask me something about those and I'll help."

Do not mention databases, retrieval systems, planners, validators, or other
internal architecture.
"""


def compose_general_tutor_response(
    *,
    user_question: str,
    history: Optional[list[dict]] = None,
    ui_language: Optional[str] = None,
    ui_lesson: Optional[int] = None,
    action_mode: Optional[str] = None,
    ui_page: Optional[str] = None,
) -> dict[str, Any]:
    """
    GPT-first tutor answer. No planner, no retrieval, no domain gate.

    Soft UI/action context may be attached to help GPT answer naturally.
    That context must never become a hard refusal gate.
    """
    refresh_composer_enabled()
    started = time.time()
    mode = "general_tutor"

    if not COMPOSER_ENABLED:
        return _fail(
            mode=mode,
            evidence_mode="general",
            reason="composer_disabled",
            error="TUTOR_LLM_COMPOSER is not true",
            started=started,
        )

    client, init_reason = _client()
    if client is None:
        return _fail(
            mode=mode,
            evidence_mode="general",
            reason=init_reason or "missing_api_key",
            error=init_reason or "missing_api_key",
            started=started,
        )

    question = (user_question or "").strip()
    if not question:
        return _fail(
            mode=mode,
            evidence_mode="general",
            reason="empty_output",
            error="empty_user_question",
            started=started,
        )

    # Soft browsing / action context — never a topic blacklist.
    context_bits: list[str] = []
    if ui_language:
        try:
            context_bits.append(
                f"Current UI language focus: {display_name(ui_language)}."
            )
        except Exception:
            context_bits.append(f"Current UI language focus: {ui_language}.")
    if ui_lesson is not None:
        context_bits.append(f"Current UI lesson number: {ui_lesson}.")
    if ui_page:
        context_bits.append(f"Current app page: {ui_page}.")
    if action_mode:
        context_bits.append(f"Learning action selected: {action_mode}.")

    user_content = question
    if context_bits:
        user_content = (
            "Optional UI context (soft hints only — never refuse because of these):\n"
            + "\n".join(f"- {b}" for b in context_bits)
            + "\n\nUser message:\n"
            + question
        )

    history_turns = [
        {"role": h.get("role"), "content": h.get("content")}
        for h in (history or [])
        if h.get("role") in ("user", "assistant") and (h.get("content") or "").strip()
    ]
    # Keep history bounded for latency / token use
    if len(history_turns) > 16:
        history_turns = history_turns[-16:]

    prompt_length = len(_GENERAL_TUTOR_SYSTEM) + len(user_content) + sum(
        len(h.get("content") or "") for h in history_turns
    )
    tokens_estimate = max(1, prompt_length // 4)
    model = get_model_name()

    try:
        response = _create_responses_call(
            client,
            model=model,
            input_messages=(
                [{"role": "system", "content": _GENERAL_TUTOR_SYSTEM}]
                + history_turns
                + [{"role": "user", "content": user_content}]
            ),
            max_output_tokens=1400,
            temperature=0.45,
        )
        reply = _extract_reply(response)
        latency_ms = int((time.time() - started) * 1000)
        if not reply:
            return _fail(
                mode=mode,
                evidence_mode="general",
                reason="empty_output",
                error="Responses API returned empty output_text",
                started=started,
                prompt_length=prompt_length,
                tokens_estimate=tokens_estimate,
            )
        return {
            "ok": True,
            "reply": reply,
            "composer_mode": mode,
            "composer_reason": "composed_general_tutor",
            "composer_prompt_length": prompt_length,
            "latency_ms": latency_ms,
            "tokens_estimate": tokens_estimate,
            "evidence_mode": "general",
            "model": model,
            "gpt_invoked": True,
        }
    except Exception as exc:
        reason = _classify_exception(exc)
        return _fail(
            mode=mode,
            evidence_mode="general",
            reason=reason,
            error=f"{type(exc).__name__}: {exc}",
            started=started,
            prompt_length=prompt_length,
            tokens_estimate=tokens_estimate,
            exc=exc,
        )


def compose_response(
    *,
    user_question: str,
    plan,
    bundle,
    validation,
    coaching_note: str = "",
    evidence_mode: str = "database",
    knowledge_route: Optional[dict] = None,
    history: Optional[list[dict]] = None,
    is_followup: bool = False,
) -> dict[str, Any]:
    """
    Legacy evidence-mode composer (database / linguistics / hybrid).

    Live AI Tutor chat uses compose_general_tutor_response() instead.
    Kept for optional tooling and older call sites only.
    """
    refresh_composer_enabled()
    mode = composer_mode_for(plan, evidence_mode)
    started = time.time()

    if not COMPOSER_ENABLED:
        return _fail(
            mode=mode,
            evidence_mode=evidence_mode,
            reason="composer_disabled",
            error="TUTOR_LLM_COMPOSER is not true",
            started=started,
        )

    client, init_reason = _client()
    if client is None:
        return _fail(
            mode=mode,
            evidence_mode=evidence_mode,
            reason=init_reason or "missing_api_key",
            error=init_reason or "missing_api_key",
            started=started,
        )

    payload = build_composer_payload(
        user_question=user_question,
        plan=plan,
        bundle=bundle,
        validation=validation,
        coaching_note=coaching_note,
        evidence_mode=evidence_mode,
        knowledge_route=knowledge_route,
    )
    facts_json = json.dumps(payload, ensure_ascii=False, default=str)
    if len(facts_json) > _MAX_FACTS_CHARS:
        payload["retrieved_facts"]["all_rows"] = payload["retrieved_facts"]["all_rows"][:20]
        facts_json = json.dumps(payload, ensure_ascii=False, default=str)[:_MAX_FACTS_CHARS]

    system = _system_prompt(mode, evidence_mode, is_followup=is_followup)
    if evidence_mode == "linguistics":
        user = (
            "Answer this learner question as an educational tutor.\n"
            "No course-database rows are required for this route.\n"
            "If it is a general/math/economics/CS/study/website question, answer "
            "normally — do NOT mention a missing course database.\n"
            "Do not invent lesson-specific Malaysian heritage-language data.\n\n"
            f"{facts_json}"
        )
    elif evidence_mode == "hybrid":
        user = (
            (
                "This is a conversational follow-up — see FOLLOW-UP TURN rules above "
                "and the conversation history included as prior turns. Respond "
                "naturally; you do not have to use the two-section format for a "
                "short follow-up.\n\n"
                if is_followup
                else (
                    "Compose a hybrid educational reply for an in-domain "
                    "language/linguistics question.\n"
                    "Use TWO separated sections: Course database information, then "
                    "General linguistic knowledge.\n"
                    "If course rows are empty, say the course database lacks that "
                    "lesson fact, then still teach the general linguistic part.\n"
                    "Never invent database facts. Never mix the sections.\n\n"
                )
            )
            + f"{facts_json}"
        )
    else:
        user = (
            "Compose the best educational tutor reply for the user question.\n"
            "Use ONLY the verified database package below.\n\n"
            f"{facts_json}"
        )

    prompt_length = len(system) + len(user)
    tokens_estimate = max(1, prompt_length // 4)
    model = get_model_name()

    history_turns = [
        {"role": h.get("role"), "content": h.get("content")}
        for h in (history or [])
        if h.get("role") in ("user", "assistant") and (h.get("content") or "").strip()
    ]

    try:
        response = _create_responses_call(
            client,
            model=model,
            input_messages=(
                [{"role": "system", "content": system}]
                + history_turns
                + [{"role": "user", "content": user}]
            ),
            max_output_tokens=1100 if evidence_mode != "database" else 900,
            temperature=0.35 if evidence_mode == "database" else 0.45,
        )
        reply = _extract_reply(response)
        latency_ms = int((time.time() - started) * 1000)
        if not reply:
            return _fail(
                mode=mode,
                evidence_mode=evidence_mode,
                reason="empty_output",
                error="Responses API returned empty output_text",
                started=started,
                prompt_length=prompt_length,
                tokens_estimate=tokens_estimate,
            )
        return {
            "ok": True,
            "reply": reply,
            "composer_mode": mode,
            "composer_reason": f"composed_{evidence_mode}",
            "composer_prompt_length": prompt_length,
            "latency_ms": latency_ms,
            "tokens_estimate": tokens_estimate,
            "evidence_mode": evidence_mode,
            "model": model,
        }
    except Exception as exc:
        reason = _classify_exception(exc)
        return _fail(
            mode=mode,
            evidence_mode=evidence_mode,
            reason=reason,
            error=f"{type(exc).__name__}: {exc}",
            started=started,
            prompt_length=prompt_length,
            tokens_estimate=tokens_estimate,
            exc=exc,
        )


_QUIZ_SYSTEM_PROMPT = """You are a quiz-question generator for Malaysia Linguistics \
Lab, an app teaching Iban, Kadazan-Dusun, Bidayuh, and Mah Meri, plus \
general linguistics.

Generate exactly ONE multiple-choice question as strict JSON (no markdown fences, \
no commentary) with this shape:
{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0, \
"explanation": "..."}

RULES
- Exactly 4 options, plausible distractors, only one clearly correct.
- correct_index is 0-based and MUST point at the correct option.
- explanation is 1-2 short sentences a learner can read after answering.
- If asked about a specific heritage language and you are NOT confident of the
  exact verified word/translation, do NOT invent a specific vocabulary fact as
  if it were course-verified — instead write a conceptual/linguistics question
  about the topic (e.g. general morphology/grammar concept) rather than a
  fabricated word-translation pair.
- Keep the question and options short and classroom-appropriate.
- Prefer a meaningfully NEW learning check: different concept, different correct
  answer, and/or a different question form when the learner already saw related
  recent questions. Do not merely rephrase a recent question.
- Return ONLY the JSON object, nothing else.
"""


def generate_quiz_question(
    *,
    topic: str,
    language_display: Optional[str] = None,
    difficulty: Optional[str] = None,
    course_context: Optional[list[dict]] = None,
    history: Optional[list[dict]] = None,
    avoid_recent: Optional[list[dict]] = None,
    preferred_question_types: Optional[list[str]] = None,
    attempt: int = 0,
) -> dict[str, Any]:
    """
    GPT-generated quiz question for topics/languages with no (or insufficient)
    course-database quiz rows. Kept deterministically gradable (multiple choice)
    even though the question itself is model-generated — marked source=gpt_generated
    so it is never confused with a verified course-database quiz item.
    """
    refresh_composer_enabled()
    started = time.time()
    if not COMPOSER_ENABLED:
        return {"ok": False, "reason": "composer_disabled"}
    client, init_reason = _client()
    if client is None:
        return {"ok": False, "reason": init_reason or "missing_api_key"}

    model = get_model_name()
    ask = f"Topic: {topic or 'general language learning'}\n"
    if language_display:
        ask += f"Heritage language in focus: {language_display}\n"
    if difficulty:
        ask += f"Target difficulty: {difficulty}\n"
    if preferred_question_types:
        ask += (
            "Prefer one of these underused question forms when possible "
            f"(do not force if the topic cannot support it): "
            f"{', '.join(preferred_question_types[:4])}.\n"
        )
    if avoid_recent:
        avoid_lines = []
        for item in avoid_recent[-8:]:
            q = (item.get("question") or "").strip()
            a = (item.get("correct_answer") or "").strip()
            concept = (item.get("concept") or "").strip()
            qtype = (item.get("question_type") or "").strip()
            if q:
                avoid_lines.append(
                    f"- Q: {q} | answer: {a} | type: {qtype} | concept: {concept}"
                )
        if avoid_lines:
            ask += (
                "Avoid repeating these recent quiz checks. Do not ask the same "
                "fact with different wording, and do not test the same concept "
                "with the same answer:\n"
                + "\n".join(avoid_lines)
                + "\n"
            )
    if course_context:
        ask += (
            "Optional course-database context you may draw on (do not assume it "
            "is complete, and do not invent extra facts beyond it):\n"
            + json.dumps(_sanitize_rows(course_context, limit=15), ensure_ascii=False, default=str)
            + "\n"
        )
    if history:
        ask = (
            "The conversation history above shows what the learner just discussed — "
            "if the topic is vague (e.g. \"what I just learned\"), base the question "
            "on that recent conversation instead of guessing.\n\n"
        ) + ask
    if attempt > 0:
        ask += (
            f"\nRetry #{attempt + 1}: previous candidate was too similar to a "
            "recent question. Generate a clearly different check.\n"
        )
    ask += "\nGenerate the quiz question JSON now."

    history_turns = [
        {"role": h.get("role"), "content": h.get("content")}
        for h in (history or [])
        if h.get("role") in ("user", "assistant") and (h.get("content") or "").strip()
    ]

    try:
        response = _create_responses_call(
            client,
            model=model,
            input_messages=(
                [{"role": "system", "content": _QUIZ_SYSTEM_PROMPT}]
                + history_turns
                + [{"role": "user", "content": ask}]
            ),
            max_output_tokens=500,
            temperature=min(0.9, 0.55 + 0.1 * max(0, int(attempt or 0))),
        )
        raw = _extract_reply(response)
        if not raw:
            return {"ok": False, "reason": "empty_output"}
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned.strip(), flags=re.I)
        data = json.loads(cleaned)
        question = str(data.get("question") or "").strip()
        options = [str(o).strip() for o in (data.get("options") or []) if str(o).strip()]
        correct_index = data.get("correct_index")
        explanation = str(data.get("explanation") or "").strip()
        if not question or len(options) < 2 or not isinstance(correct_index, int):
            return {"ok": False, "reason": "malformed_quiz_json"}
        correct_index = max(0, min(correct_index, len(options) - 1))
        return {
            "ok": True,
            "question": question,
            "options": options,
            "correct_index": correct_index,
            "explanation": explanation,
            "source": "gpt_generated",
            "model": model,
            "latency_ms": int((time.time() - started) * 1000),
            "attempt": int(attempt or 0),
        }
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("GPT quiz generation returned invalid JSON: %s", exc)
        return {"ok": False, "reason": "malformed_quiz_json", "error": str(exc)}
    except Exception as exc:
        reason = _classify_exception(exc)
        logger.error("GPT quiz generation failed: reason=%s error=%s", reason, exc)
        return {"ok": False, "reason": reason, "error": str(exc)}
