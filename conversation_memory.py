"""
Session conversation memory for follow-up tutoring turns.
"""

from __future__ import annotations

from typing import Any, Optional

from flask import session

_MEMORY_KEY = "tutor_conversation_memory"


def get_memory() -> dict[str, Any]:
    mem = session.get(_MEMORY_KEY)
    return dict(mem) if isinstance(mem, dict) else {}


def update_memory(
    *,
    language: Optional[str] = None,
    lesson_id: Optional[int] = None,
    topic: Optional[str] = None,
    intent: Optional[str] = None,
    entities: Optional[list] = None,
    linguistics_topic: Optional[str] = None,
    knowledge_route: Optional[str] = None,
    last_query: Optional[str] = None,
    word: Optional[str] = None,
    last_reply: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> dict[str, Any]:
    mem = get_memory()
    if language:
        mem["language"] = language
    if lesson_id is not None:
        mem["lesson_id"] = lesson_id
    if topic:
        mem["topic"] = topic
    if intent:
        mem["intent"] = intent
    if entities:
        mem["entities"] = list(entities)
    if linguistics_topic:
        mem["linguistics_topic"] = linguistics_topic
        mem["grammar_topic"] = (
            linguistics_topic if "grammar" in linguistics_topic else mem.get("grammar_topic")
        )
    if knowledge_route:
        mem["knowledge_route"] = knowledge_route
    if last_query:
        mem["last_query"] = last_query
    # "word" tracks the specific vocabulary item last discussed, so follow-ups
    # like "another example" / "how do I pronounce this" can refer to it
    # directly instead of falling back to a generic topic-level rewrite.
    if word:
        mem["word"] = word
    if last_reply:
        mem["last_reply"] = last_reply[:1200]
    if difficulty:
        mem["difficulty"] = difficulty
    session[_MEMORY_KEY] = mem
    return mem


def apply_followup_rewrite(
    message: str,
    lang_key: Optional[str],
    level_num: Optional[int],
) -> tuple[str, Optional[str], Optional[int], dict[str, Any]]:
    """
    Expand short follow-ups using remembered lesson/topic.
    Returns (rewritten_message, lang_key, level_num, memory).
    """
    import re

    from language_registry import extract_languages, display_name

    mem = get_memory()
    text = (message or "").strip()
    low = text.lower()

    effective_lang = lang_key or mem.get("language")
    effective_lesson = level_num if level_num is not None else mem.get("lesson_id")
    last_q = (mem.get("last_query") or "").strip()
    topic = mem.get("linguistics_topic") or mem.get("topic") or "vocabulary"
    last_word = (mem.get("word") or "").strip()

    # Standalone general-education / product questions must not be rewritten
    # into the prior heritage-language topic.
    try:
        from planner import is_general_education_request

        if is_general_education_request(text) and len(text.split()) >= 4:
            return text, effective_lang, effective_lesson, mem
    except Exception:
        pass

    # Context switch: "what about X", "and X?", "same for X"
    switch = re.search(
        r"^(?:what\s+about|how\s+about|and|same\s+for|now\s+for|also)\s+(.+?)\??$",
        low,
    )
    if switch and last_q:
        other = switch.group(1).strip(" ?.!")
        langs = extract_languages(other) or extract_languages(text)
        if langs:
            name = display_name(langs[0])
            # Re-run prior query framing against the new language
            base = re.sub(
                r"\b(mah\s*meri|bidayuh|iban|kadazan(?:[-\s]?dusun)?)\b",
                name,
                last_q,
                flags=re.I,
            )
            if base.lower() == last_q.lower():
                base = f"{last_q} for {name}"
            return base, langs[0], effective_lesson, mem

    # "another language" → cycle to a different registered language framing
    if re.search(r"^another\s+language\b", low) and last_q:
        return f"Compare the same topic across all languages: {topic}", None, effective_lesson, mem

    followup_example = bool(re_search_followup_example(low))
    followup_grammar = bool(re_search_followup_grammar(low))
    followup_pronounce = bool(
        re.search(
            r"how\s+do\s+i\s+(say|pronounce)\s+(it|that|this)\b|"
            r"^(pronounce|pronunciation)\s+(it|that|this)\??$|"
            r"^how\s+is\s+(it|that|this)\s+pronounced\??$",
            low,
        )
    )
    followup_simplify = bool(
        re.search(
            r"\bmake\s+(it|that|this)\s+(simpler|easier)\b|"
            r"\bexplain\s+(that|it)\s+(more\s+simply|more\s+simple|simpler)\b|"
            r"^(simpler|easier|simplify(?:\s+that|\s+it)?)\??$",
            low,
        )
    )
    followup_harder = bool(
        re.search(
            r"\bmake\s+(it|that|this)\s+(harder|more\s+difficult|more\s+challenging)\b|"
            r"^(harder|more\s+difficult|more\s+challenging)\??$",
            low,
        )
    )
    followup_again = bool(
        re.search(
            r"\bexplain\s+(that|it)\s+again\b|^(again|repeat\s+that)\??$",
            low,
        )
    )
    # Only short "why?" / "why is that?" follow-ups — never rewrite full
    # "Why does the discriminant…" educational questions into prior topic.
    followup_more = bool(
        re.search(
            r"^(explain\s+more|tell\s+me\s+more|go\s+deeper|continue(?:\s+teaching)?|"
            r"show\s+more|give\s+(?:me\s+)?more|more)\b|"
            r"^why\??$|"
            r"^why\s+(is|are|do|does)\s+(it|that|this)\b|"
            r"^compare\s+with\s+[\w\s\-]+\??$",
            low,
        )
        or followup_simplify
        or followup_harder
        or followup_again
    )
    followup_another = bool(
        re.search(
            r"^(give|show|get)?\s*(me\s+)?(another|one\s+more)(\s+one)?\b|"
            r"^another\s+one\b|^one\s+more\b",
            low,
        )
    )
    followup_ordinal = re.search(
        r"^(the\s+)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)(\s+one)?\??$",
        low,
    )

    if followup_pronounce and last_word:
        lang = effective_lang or "this language"
        rewritten = f'How do I pronounce the word "{last_word}" in {lang}? What is the IPA?'
        return rewritten, effective_lang, effective_lesson, mem

    if followup_example:
        lang = effective_lang or "this language"
        if last_word:
            rewritten = (
                f'Give another NEW example sentence using the word "{last_word}" '
                f"in {lang}, different from any example already given"
            )
        else:
            rewritten = (
                f"Give another example sentence for {topic} "
                f"in the current {lang} lesson"
            )
        return rewritten, effective_lang, effective_lesson, mem

    if followup_another:
        lang = effective_lang or "this language"
        if "greeting" in (topic or ""):
            rewritten = f"Give me another random greeting in {lang}"
        else:
            rewritten = f"Give me another random word in {lang}"
        return rewritten, effective_lang, effective_lesson, mem

    if followup_ordinal and last_q:
        ord_token = followup_ordinal.group(2)
        # Re-ask prior ranking with explicit ordinal
        if re.search(r"\blongest|shortest|difficult|top\b", last_q, re.I):
            rewritten = f"What is the {ord_token} longest word based on: {last_q}"
        else:
            rewritten = f"Show the {ord_token} item for: {last_q}"
        return rewritten, effective_lang, effective_lesson, mem

    if followup_grammar:
        lang = effective_lang or "this language"
        lesson = effective_lesson if effective_lesson is not None else "current"
        rewritten = (
            f"Explain the grammar we learned just now "
            f"for {lang} lesson {lesson}"
        )
        return rewritten, effective_lang, effective_lesson, mem

    if followup_more:
        lang = effective_lang or mem.get("language") or ""
        # Keep the rewritten planning text short and single-topic — the actual
        # previous answer is supplied to GPT separately via conversation
        # `history` (see composer.compose_response), never inlined here.
        # Inlining it previously confused the multi-intent decomposer into
        # treating the quoted prior answer as a fresh multi-part request.
        if followup_simplify:
            rewritten = (
                f"Re-explain your previous answer about {topic} in a SIMPLER way: "
                f"shorter sentences, easier vocabulary, fewer technical terms."
            )
        elif followup_harder:
            rewritten = (
                f"Go deeper on {topic} at a MORE ADVANCED level than your previous "
                f"answer: more technical terminology and nuance."
            )
        elif followup_again:
            rewritten = (
                f"Explain your previous answer about {topic} again, using different "
                f"wording/examples than before."
            )
        elif "compare with" in low:
            m = re.search(r"compare\s+with\s+([\w\s\-]+)", low)
            other = (m.group(1).strip() if m else "Malay").title()
            rewritten = (
                f"Compare {topic} for {lang or 'the current language'} with {other}"
            )
        elif low in ("why", "why?"):
            rewritten = f"Why is {topic} important for language learning?"
        elif re.search(r"continue\s+teaching", low):
            rewritten = f"Continue teaching {topic}" + (f" in {lang}" if lang else "")
        else:
            rewritten = f"Explain more about {topic}" + (f" in {lang}" if lang else "")
        return rewritten, effective_lang, effective_lesson, mem

    return text, effective_lang, effective_lesson, mem


def re_search_followup_example(low: str) -> bool:
    import re
    return bool(
        re.search(
            r"^(give|show|another|more)\b.*\bexample\b|"
            r"^another example\b|^one more example\b|^give me another\b.*\bexample\b",
            low,
        )
    )


def re_search_followup_grammar(low: str) -> bool:
    import re
    return bool(
        re.search(
            r"^(explain\s+)?(the\s+)?grammar\b|"
            r"\bgrammar\s+(we\s+)?learned\b|\bjust\s+now\b",
            low,
        )
    )


def topic_from_intent(intent: str, message: str = "") -> str:
    mapping = {
        "TEACHING": "teaching",
        "GRAMMAR_EXPLANATION": "grammar",
        "EXAMPLE_SENTENCE": "examples",
        "CULTURE": "culture",
        "TRANSLATION": "translation",
        "PRONUNCIATION": "pronunciation",
        "MORPHOLOGY": "morphology",
        "SYNTAX": "syntax",
        "SEMANTICS": "semantics",
        "LINGUISTICS": "linguistics",
        "STATISTICS": "vocabulary statistics",
        "RANKING": "word ranking",
        "COMPARE": "language comparison",
        "LONGEST_WORD": "longest words",
        "SHORTEST_WORD": "shortest words",
        "DIFFICULT_WORDS": "difficult words",
        "QUIZ": "quiz",
    }
    if intent in mapping:
        return mapping[intent]
    low = (message or "").lower()
    for key in (
        "morphology", "syntax", "phonology", "greeting", "vocabulary",
        "grammar", "culture", "pronunciation",
    ):
        if key in low:
            return key
    return "vocabulary"
