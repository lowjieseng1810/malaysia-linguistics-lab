"""Compatibility shim — semantic planning lives in planner.py."""

from __future__ import annotations

from typing import Optional

from planner import classify_intent


_LEGACY = {
    "OFF_TOPIC": "off_topic",
    "UNSUPPORTED_LANGUAGE": "off_topic",
    "VOCABULARY_LOOKUP": "translation",
    "VOCABULARY": "vocabulary_list",
    "GRAMMAR_EXPLANATION": "grammar",
    "GRAMMAR": "grammar",
    "TRANSLATION": "translation",
    "EXAMPLE_SENTENCE": "example",
    "EXAMPLES": "example",
    "CULTURE": "culture",
    "QUIZ": "quiz",
    "LESSON_SUMMARY": "lesson_summary",
    "CONVERSATION": "compare",
    "PRONUNCIATION": "pronunciation",
    "IPA": "pronunciation",
    "MORPHOLOGY": "grammar",
    "SYNTAX": "grammar",
    "SEMANTICS": "grammar",
    "LINGUISTICS": "grammar",
    "DIFFICULT_WORDS": "difficult_words",
    "LONGEST_WORD": "longest_word",
    "SHORTEST_WORD": "shortest_word",
    "SEARCH": "vocabulary_list",
    "ANALYTICS": "vocabulary_list",
    "STATISTICS": "vocabulary_list",
    "RANKING": "vocabulary_list",
    "COMPARE": "compare",
    "COMPARISON": "compare",
    "TEACHING": "grammar",
    "EXPLANATION": "grammar",
    "UNKNOWN": "translation",
}


def detect_intent(message: str, mode: Optional[str] = None) -> str:
    intent, _confidence, _notes = classify_intent(message, mode)
    return _LEGACY.get(intent, intent.lower())
