"""
Knowledge Router — sits between Planner and Retriever.

Policy:
- Unsafe / entertainment off-topic → refuse
- General education / website help → GPT general knowledge (NOT language-DB gate)
- Language / linguistics questions → GPT and/or DB
- Lesson-specific heritage-language facts → DB-authoritative; never invent
- Empty DB must not invent language facts; must not block non-language questions

Mission: Malaysia Linguistics Lab + Language Learning + Linguistics Education
         + general educational help when the question is not a language-fact claim.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from planner import (
    ANALYTICS,
    COMPARE,
    CONVERSATION,
    CULTURE,
    DIFFICULT_WORDS,
    EXAMPLE_SENTENCE,
    EXPLANATION,
    GENERAL_KNOWLEDGE,
    GRAMMAR_EXPLANATION,
    IPA,
    LESSON_SUMMARY,
    LINGUISTICS,
    LONGEST_WORD,
    MORPHOLOGY,
    OFF_TOPIC,
    PRONUNCIATION,
    QUIZ,
    RANKING,
    SEARCH,
    SEMANTICS,
    SHORTEST_WORD,
    STATISTICS,
    SYNTAX,
    TEACHING,
    TRANSLATION,
    UNKNOWN,
    UNSUPPORTED_LANGUAGE,
    VOCABULARY_LOOKUP,
    is_general_education_request,
    is_off_topic,
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

DATABASE_ONLY = "DATABASE_ONLY"
GENERAL_LINGUISTICS_ONLY = "GENERAL_LINGUISTICS_ONLY"
DATABASE_PLUS_LINGUISTICS = "DATABASE_PLUS_LINGUISTICS"
ROUTE_OFF_TOPIC = "OFF_TOPIC"
ROUTE_UNKNOWN = "UNKNOWN"

# Lesson-fact intents: DB is authoritative; empty DB must not invent rows.
# Still allow linguistics enrichment via hybrid for teaching-shaped asks.
_LESSON_FACT_INTENTS = {
    QUIZ,
    TRANSLATION,
    CONVERSATION,
    CULTURE,
    EXAMPLE_SENTENCE,
    VOCABULARY_LOOKUP,
    SEARCH,
    ANALYTICS,
    STATISTICS,
    RANKING,
    COMPARE,
    LONGEST_WORD,
    SHORTEST_WORD,
    DIFFICULT_WORDS,
    LESSON_SUMMARY,
}

# Pure metalinguistic intents (GPT-first)
_LINGUISTICS_INTENTS = {
    LINGUISTICS,
    MORPHOLOGY,
    SYNTAX,
    SEMANTICS,
    PRONUNCIATION,
    IPA,
    EXPLANATION,
}

# Teaching-shaped intents: always hybrid (DB when present + GPT linguistics)
_TEACHING_INTENTS = {
    TEACHING,
    GRAMMAR_EXPLANATION,
    LESSON_SUMMARY,
    CULTURE,
    EXAMPLE_SENTENCE,
    CONVERSATION,
    PRONUNCIATION,
    EXPLANATION,
}

# Quantitative / lookup queries where the answer *is* a DB fact
_STRICT_DB_INTENTS = {
    QUIZ,
    LONGEST_WORD,
    SHORTEST_WORD,
    STATISTICS,
    ANALYTICS,
    RANKING,
    COMPARE,
    SEARCH,
    VOCABULARY_LOOKUP,
    DIFFICULT_WORDS,
}

_PURE_LINGUISTICS = re.compile(
    r"\b("
    r"morphology|syntax|phonology|phonetics?|ipa|international\s+phonetic|"
    r"semantics|pragmatics|discourse|sociolinguistics|"
    r"historical\s+linguistics|language\s+acquisition|"
    r"language\s+famil(?:y|ies)|austronesian|asli(?:an)?|"
    r"writing\s+system(?:s)?|orthography|etymology|"
    r"language\s+revitalization|endangered\s+languages?|"
    r"language\s+endangerment|language\s+death|"
    r"typology|linguistic(?:s)?|dialectology|lexicography|"
    r"prosody|intonation|morpheme|phoneme|allophone|"
    r"agglutination|isolating\s+language|analytic\s+language|"
    r"synthetic\s+language|case\s+system|word\s+order|"
    r"svo|sov|vso|constituent|clause\s+structure|"
    r"discourse\s+analysis|speech\s+act|code[\s\-]?switching|"
    r"pronunc\w*|articulation|"
    r"polyglot|bilingual|multilingual|second\s+language|"
    r"language\s+learning|language\s+teaching|pedagogy"
    r")\b",
    re.I,
)

_LESSON_FACT_SIGNALS = re.compile(
    r"\b("
    r"this\s+lesson|current\s+lesson|level\s+\d+|quiz|"
    r"vocabulary\s+size|vocab\s+size|word\s+count|longest|shortest|"
    r"top\s+\d+|how\s+many|random\s+word|alphabetically|median|"
    r"most\s+common|second\s+longest|third\s+longest"
    r")\b",
    re.I,
)

_DOMAIN_SIGNALS = re.compile(
    r"\b("
    r"language|languages|linguistic|linguistics|grammar|pronounc\w*|ipa|"
    r"morphology|syntax|phonology|semantics|pragmatics|translate|translation|"
    r"vocabulary|vocab|word|words|sentence|dialect|orthography|writing\s+system|"
    r"language\s+famil|austronesian|asli|endangered|heritage|greeting|"
    r"iban|bidayuh|mah\s*meri|kadazan|dusun|malay|lesson|quiz|tutor|"
    r"learn|teach|meaning|phrase|dialogue|culture|tradition"
    r")\b",
    re.I,
)


@dataclass
class RouteDecision:
    route: str
    reason: str
    database_used: bool
    linguistics_used: bool
    hybrid_mode: bool
    confidence: float = 0.9
    notes: list[str] = field(default_factory=list)
    # When True, empty DB must not hard-refuse — continue with linguistics
    allow_linguistics_fallback: bool = True

    def to_audit(self) -> dict[str, Any]:
        return {
            "knowledge_route": self.route,
            "database_used": self.database_used,
            "linguistics_used": self.linguistics_used,
            "hybrid_mode": self.hybrid_mode,
            "reason": self.reason,
            "confidence": self.confidence,
            "notes": list(self.notes),
            "allow_linguistics_fallback": self.allow_linguistics_fallback,
        }


def is_in_domain(message: str, plan=None) -> bool:
    """True if the question belongs to language learning / linguistics."""
    text = message or getattr(plan, "message", "") or ""
    if not text.strip():
        return False
    if is_off_topic(text):
        return False
    intent = getattr(plan, "intent", "") or ""
    if intent == OFF_TOPIC:
        return False
    if intent and intent != UNKNOWN:
        # Planner already classified into a tutor intent
        if intent != UNSUPPORTED_LANGUAGE:
            return True
    if _DOMAIN_SIGNALS.search(text) or _PURE_LINGUISTICS.search(text):
        return True
    if getattr(plan, "entities", None):
        return True
    return False


def _mentions_heritage_language(message: str, plan) -> bool:
    if getattr(plan, "entities", None):
        return True
    return bool(
        re.search(
            r"\b(mah\s*meri|bidayuh|iban|kadazan|dusun|semai|temiar|"
            r"jakun|orang\s+asli|malay(?:sian)?\s+heritage)\b",
            message or "",
            re.I,
        )
    )


def _wants_strict_lesson_facts(text: str, intent: str) -> bool:
    """Quantitative / quiz / lookup where inventing a DB row would be harmful."""
    if intent == QUIZ:
        return True
    if intent in _STRICT_DB_INTENTS and _LESSON_FACT_SIGNALS.search(text or ""):
        return True
    if intent in (LONGEST_WORD, SHORTEST_WORD, STATISTICS, RANKING, ANALYTICS, COMPARE):
        return True
    return bool(_LESSON_FACT_SIGNALS.search(text or ""))


def route_knowledge(plan, message: str = "") -> RouteDecision:
    """
    Domain-first routing.

    Prefer answering in-domain questions with GPT linguistics and/or DB.
    Never refuse solely because SQLite returned zero rows.
    """
    text = message or getattr(plan, "message", "") or ""
    intent = getattr(plan, "intent", "") or ""
    notes: list[str] = []

    # ---- OFF DOMAIN only (unsafe / entertainment) ----
    if intent == OFF_TOPIC or is_off_topic(text):
        return RouteDecision(
            route=ROUTE_OFF_TOPIC,
            reason="off_domain_refused",
            database_used=False,
            linguistics_used=False,
            hybrid_mode=False,
            confidence=0.98,
            allow_linguistics_fallback=False,
        )

    # ---- General education / product help: GPT only, never language-DB refusal ----
    if intent == GENERAL_KNOWLEDGE or is_general_education_request(text):
        return RouteDecision(
            route=GENERAL_LINGUISTICS_ONLY,
            reason="general_education_or_product_help",
            database_used=False,
            linguistics_used=True,
            hybrid_mode=False,
            confidence=0.94,
            notes=notes + ["general_knowledge"],
            allow_linguistics_fallback=True,
        )

    if intent == UNSUPPORTED_LANGUAGE:
        # Registry message is DB-backed UX; still in language domain
        return RouteDecision(
            route=DATABASE_ONLY,
            reason="unsupported_language_registry_message",
            database_used=False,
            linguistics_used=False,
            hybrid_mode=False,
            confidence=0.95,
            notes=["unsupported_language"],
            allow_linguistics_fallback=False,
        )

    pure_ling = bool(_PURE_LINGUISTICS.search(text))
    lesson_signal = bool(_LESSON_FACT_SIGNALS.search(text))
    heritage = _mentions_heritage_language(text, plan)
    has_ops = bool(getattr(plan, "operations", None))
    in_domain = is_in_domain(text, plan)
    strict_facts = _wants_strict_lesson_facts(text, intent)

    # ---- Quiz: database only (progress + items) ----
    if intent == QUIZ:
        return RouteDecision(
            route=DATABASE_ONLY,
            reason="quiz_requires_lesson_database",
            database_used=True,
            linguistics_used=False,
            hybrid_mode=False,
            confidence=0.98,
            allow_linguistics_fallback=False,
        )

    # ---- Pure linguistics / metalinguistic concepts ----
    if intent in _LINGUISTICS_INTENTS or (pure_ling and not strict_facts):
        if heritage or lesson_signal:
            return RouteDecision(
                route=DATABASE_PLUS_LINGUISTICS,
                reason="in_domain_linguistics_with_lesson_or_heritage_context",
                database_used=True,
                linguistics_used=True,
                hybrid_mode=True,
                confidence=0.93,
                notes=notes + ["domain_hybrid"],
                allow_linguistics_fallback=True,
            )
        return RouteDecision(
            route=GENERAL_LINGUISTICS_ONLY,
            reason="in_domain_general_linguistics",
            database_used=False,
            linguistics_used=True,
            hybrid_mode=False,
            confidence=0.95,
            notes=notes + ["domain_linguistics"],
            allow_linguistics_fallback=True,
        )

    # ---- Teaching / grammar / culture / examples: hybrid by default ----
    if intent in _TEACHING_INTENTS or (
        intent in (TEACHING, GRAMMAR_EXPLANATION) or
        re.search(r"(?i)\b(teach|explain|how\s+do\s+i|introduce|greet)\b", text)
    ):
        return RouteDecision(
            route=DATABASE_PLUS_LINGUISTICS,
            reason="in_domain_teaching_hybrid",
            database_used=True,
            linguistics_used=True,
            hybrid_mode=True,
            confidence=0.92,
            allow_linguistics_fallback=True,
        )

    # ---- Translation: DB for tokens + linguistics for method/gaps ----
    if intent == TRANSLATION:
        return RouteDecision(
            route=DATABASE_PLUS_LINGUISTICS,
            reason="translation_db_plus_linguistics_for_gaps",
            database_used=True,
            linguistics_used=True,
            hybrid_mode=True,
            confidence=0.92,
            allow_linguistics_fallback=True,
        )

    # ---- Strict lesson analytics / ranking / compare ----
    if strict_facts or intent in _STRICT_DB_INTENTS:
        # Still hybrid-capable fallback so empty DB does not hard-refuse domain UX
        # for compare/explain mixes; pure counts stay DB-first.
        # "Compare X and Y grammar" is a linguistics comparison even though
        # "grammar" alone doesn't match the pure-linguistics vocabulary regex —
        # it must not collapse into a bare vocabulary-count DB-only answer.
        compare_wants_linguistics = pure_ling or bool(
            re.search(r"\b(grammar|morpholog\w*|syntax|pronunciation|phonolog\w*)\b", text, re.I)
        )
        if intent in (COMPARE,) and heritage and compare_wants_linguistics:
            return RouteDecision(
                route=DATABASE_PLUS_LINGUISTICS,
                reason="compare_with_linguistics_context",
                database_used=True,
                linguistics_used=True,
                hybrid_mode=True,
                confidence=0.9,
                allow_linguistics_fallback=True,
            )
        return RouteDecision(
            route=DATABASE_ONLY,
            reason=f"lesson_fact_query:{intent or 'analytics'}",
            database_used=True,
            linguistics_used=False,
            hybrid_mode=False,
            confidence=0.94,
            # Allow soft linguistics note when empty (e.g. explain what the metric means)
            allow_linguistics_fallback=True,
            notes=notes + ["strict_lesson_facts"],
        )

    # ---- Other lesson-fact intents with ops ----
    if intent in _LESSON_FACT_INTENTS or has_ops:
        return RouteDecision(
            route=DATABASE_PLUS_LINGUISTICS,
            reason=f"in_domain_lesson_intent_hybrid:{intent or 'operations'}",
            database_used=True,
            linguistics_used=True,
            hybrid_mode=True,
            confidence=0.88,
            allow_linguistics_fallback=True,
        )

    # ---- Unknown but in domain → linguistics tutor, not refuse ----
    if in_domain or intent == UNKNOWN:
        return RouteDecision(
            route=GENERAL_LINGUISTICS_ONLY if pure_ling else DATABASE_PLUS_LINGUISTICS,
            reason="in_domain_unsure_answer_with_linguistics",
            database_used=not pure_ling,
            linguistics_used=True,
            hybrid_mode=not pure_ling,
            confidence=0.7,
            notes=["domain_prefer_answer_over_refusal"],
            allow_linguistics_fallback=True,
        )

    # ---- Default: if somehow reached, prefer hybrid over silence ----
    return RouteDecision(
        route=DATABASE_PLUS_LINGUISTICS,
        reason="default_in_domain_hybrid",
        database_used=True,
        linguistics_used=True,
        hybrid_mode=True,
        confidence=0.55,
        allow_linguistics_fallback=True,
    )


def needs_retrieval(decision: RouteDecision) -> bool:
    return decision.route in (DATABASE_ONLY, DATABASE_PLUS_LINGUISTICS) and decision.database_used


def evidence_mode_for(decision: RouteDecision) -> str:
    """Composer evidence mode: database | linguistics | hybrid."""
    if decision.route == GENERAL_LINGUISTICS_ONLY:
        return "linguistics"
    if decision.route == DATABASE_PLUS_LINGUISTICS or decision.hybrid_mode:
        return "hybrid"
    return "database"
