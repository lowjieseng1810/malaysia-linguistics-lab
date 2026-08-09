"""
Universal Linguistics Query Engine (Planner).

Converts every tutor question into a structured execution plan:
  Intent → Entities → Operations → Parameters

Multi-intent messages are decomposed into an ordered list of sub-plans.
No per-question hardcoded handlers (no "if contains longest").
Analytics are compositional: metric + aggregation + order + limit + filters.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from language_registry import (
    display_name,
    domain_language_pattern,
    extract_languages,
    extract_unsupported_language_mentions,
    get_language_keys,
    resolve_language,
    supported_languages_message,
)


NO_EVIDENCE_MESSAGE = (
    "No evidence found in the lesson database for this query."
)

OFF_TOPIC_MESSAGE = (
    "I'm your Malaysian Linguistics Lab tutor.\n\n"
    "I can answer questions about vocabulary, grammar, pronunciation, "
    "culture and lessons.\n\n"
    "I can't answer unrelated questions."
)

TRANSLATION_INSUFFICIENT = (
    "I don't yet know enough vocabulary in this lesson to translate "
    "this sentence accurately."
)

CONVERSATION_INSUFFICIENT = (
    "This lesson does not yet contain enough vocabulary for a full "
    "conversation. Try a shorter exchange using the words you have learned."
)


# ---------------------------------------------------------------------------
# Universal intents
# ---------------------------------------------------------------------------

GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
OFF_TOPIC = "OFF_TOPIC"
VOCABULARY_LOOKUP = "VOCABULARY_LOOKUP"
VOCABULARY = "VOCABULARY"
GRAMMAR_EXPLANATION = "GRAMMAR_EXPLANATION"
GRAMMAR = "GRAMMAR"
TRANSLATION = "TRANSLATION"
EXAMPLE_SENTENCE = "EXAMPLE_SENTENCE"
EXAMPLES = "EXAMPLES"
CULTURE = "CULTURE"
QUIZ = "QUIZ"
LESSON_SUMMARY = "LESSON_SUMMARY"
CONVERSATION = "CONVERSATION"
PRONUNCIATION = "PRONUNCIATION"
IPA = "IPA"
MORPHOLOGY = "MORPHOLOGY"
SYNTAX = "SYNTAX"
SEMANTICS = "SEMANTICS"
LINGUISTICS = "LINGUISTICS"
DIFFICULT_WORDS = "DIFFICULT_WORDS"
LONGEST_WORD = "LONGEST_WORD"  # compat alias → statistics(max length)
SHORTEST_WORD = "SHORTEST_WORD"  # compat alias
SEARCH = "SEARCH"
ANALYTICS = "ANALYTICS"
STATISTICS = "STATISTICS"
RANKING = "RANKING"
COMPARE = "COMPARE"
COMPARISON = "COMPARISON"
TEACHING = "TEACHING"
EXPLANATION = "EXPLANATION"
WRITING = "WRITING"
READING = "READING"
LISTENING = "LISTENING"
UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
UNKNOWN = "UNKNOWN"

SCOPE_LESSON = "lesson"
SCOPE_LANGUAGE = "language"
SCOPE_DATABASE = "database"
SCOPE_SELECTED = "selected_languages"
SCOPE_ALL_LANGUAGES = "all_languages"


# ---------------------------------------------------------------------------
# Plan schema
# ---------------------------------------------------------------------------

@dataclass
class RetrievalOp:
    """
    One retrieval step. Prefer kind='query' with compositional params:

      operation, table, language, metric, aggregation, field,
      order, limit, offset, filters, search_all, lesson_id, ...
    """
    name: str
    table: str
    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    required: bool = True


@dataclass
class TutorPlan:
    intent: str
    language: Optional[str]
    lesson_id: Optional[int]
    search_all: bool
    message: str
    mode: Optional[str]
    required_tables: list[str] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)
    lesson_scope: Optional[int] = None
    language_scope: Optional[str] = None
    need_reasoning: bool = False
    need_generation: bool = False
    confidence: float = 0.5
    operations: list[RetrievalOp] = field(default_factory=list)
    require_evidence: bool = True
    allow_llm_rewrite: bool = False
    min_rows: int = 1
    notes: list[str] = field(default_factory=list)
    source_text: str = ""
    source_lang: str = "en"
    target_lang: str = ""
    tokens: list[str] = field(default_factory=list)
    analytics_kind: str = ""
    entities: list[str] = field(default_factory=list)
    scope: str = SCOPE_LESSON
    operation: str = ""
    execution_steps: list[dict[str, Any]] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    response_type: str = "answer"
    compare_metric: str = ""
    quiz_difficulty: Optional[str] = None
    # Universal query engine fields
    query_spec: dict[str, Any] = field(default_factory=dict)
    knowledge_policy: str = "database_first"  # database_first | linguistics_with_disclaimer

    def to_audit(self) -> dict[str, Any]:
        data = asdict(self)
        data["operations"] = [
            {
                "name": op["name"],
                "table": op["table"],
                "kind": op["kind"],
                "params": op.get("params") or {},
                "required": op.get("required", True),
            }
            for op in data.get("operations") or []
        ]
        return data


@dataclass
class IntentStep:
    """One independent sub-request in a multi-intent execution plan."""
    index: int
    message: str
    plan: TutorPlan
    topic: str = ""
    languages: list[str] = field(default_factory=list)

    def to_audit(self) -> dict[str, Any]:
        return {
            "step": self.index,
            "message": self.message,
            "intent": self.plan.intent,
            "topic": self.topic,
            "languages": self.languages or list(self.plan.entities or []),
            "language": self.plan.language,
            "confidence": self.plan.confidence,
            "operations": len(self.plan.operations or []),
            "notes": list(self.plan.notes or []),
        }


@dataclass
class MultiIntentPlan:
    """Ordered execution plan for one or more independent user requests."""
    original_message: str
    steps: list[IntentStep] = field(default_factory=list)
    multi: bool = False

    @property
    def primary(self) -> Optional[TutorPlan]:
        return self.steps[0].plan if self.steps else None

    def to_audit(self) -> dict[str, Any]:
        return {
            "multi_intent": self.multi,
            "step_count": len(self.steps),
            "original_message": self.original_message,
            "steps": [s.to_audit() for s in self.steps],
        }


# ---------------------------------------------------------------------------
# Multi-intent decomposition (general — not prompt-specific)
# ---------------------------------------------------------------------------

# Cue that a clause is likely a new independent request
_REQUEST_CUE = re.compile(
    r"(?i)^\s*(?:"
    r"explain|teach|compare|translate|give|show|list|find|tell|"
    r"continue|another|what|how|why|when|which|define|describe|"
    r"quiz|summarise|summarize|pronounce|provide|help|can\s+you|"
    r"please|also|then|next|finally|and\s+then|and\s+also"
    r")\b"
)

_NUMBERED_ITEM = re.compile(r"(?m)^\s*(?:\d+[\.\)]\s+|[-*•]\s+)")


def _normalize_segment(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip(" \t\r\n\"'")).strip()


def _is_viable_segment(text: str) -> bool:
    t = _normalize_segment(text)
    if not t:
        return False
    # Keep short follow-ups: "Continue.", "IPA", "Why?"
    if len(t) <= 2 and not re.search(r"[A-Za-z]", t):
        return False
    return True


def decompose_message(message: str) -> list[str]:
    """
    Split an arbitrary user message into ordered independent request segments.

    Uses structural cues only (newlines, lists, sentence boundaries, request
    verbs) — never a fixed list of example prompts.
    """
    text = (message or "").strip()
    if not text:
        return []

    # 1) Newline / numbered / bullet blocks
    blocks: list[str] = []
    if "\n" in text or _NUMBERED_ITEM.search(text):
        raw_lines = re.split(r"[\r\n]+", text)
        for line in raw_lines:
            line = _NUMBERED_ITEM.sub("", line).strip()
            if line:
                blocks.append(line)
    else:
        blocks = [text]

    # 2) Split each block on sentence terminators and semicolons
    segments: list[str] = []
    for block in blocks:
        parts = re.split(r"(?<=[.!?])\s+|\s*;\s+", block)
        for part in parts:
            part = _normalize_segment(part)
            if not part:
                continue
            # 3) Further split long clauses joined by request cues after "and"
            subparts = _split_conjoined_requests(part)
            segments.extend(subparts)

    # 4) Drop empty / merge stray conjunction fragments into previous
    cleaned: list[str] = []
    for seg in segments:
        if not _is_viable_segment(seg):
            continue
        low = seg.lower()
        if cleaned and re.match(r"^(and|also|then|please)\b", low) and len(seg.split()) <= 2:
            cleaned[-1] = f"{cleaned[-1]} {seg}".strip()
            continue
        cleaned.append(seg)

    return cleaned or [_normalize_segment(text)]


def _split_heterogeneous_metric_clauses(clause: str) -> list[str]:
    """
    Split when one message binds different structured metrics to different
    languages, e.g. "longest Bidayuh … and shortest Mah Meri …".

    Same-metric multi-language compares ("longest in A and B") stay intact.
    Structural only — never hard-codes full example questions.
    """
    text = (clause or "").strip()
    if not text:
        return []
    markers = [
        (m.start(), m.group(1).lower())
        for m in re.finditer(r"\b(longest|shortest)\b", text, re.I)
    ]
    if len(markers) < 2:
        return [text]
    if len({metric for _, metric in markers}) < 2:
        return [text]

    parts: list[str] = []
    cursor = 0
    for idx, (pos, _) in enumerate(markers):
        if idx == 0:
            continue
        prefix = text[cursor:pos]
        conj_matches = list(
            re.finditer(
                r"(?i)\s+(?:and\s+also|and\s+then|and|then|also)\s+|,\s*",
                prefix,
            )
        )
        if not conj_matches:
            continue
        cut = cursor + conj_matches[-1].start()
        left = _normalize_segment(text[cursor:cut])
        if left:
            parts.append(left)
        cursor = cursor + conj_matches[-1].end()
    rest = _normalize_segment(text[cursor:])
    if rest:
        parts.append(rest)
    return parts if len(parts) >= 2 else [text]


def _split_conjoined_requests(clause: str) -> list[str]:
    """
    Split 'Do X. Also do Y' style already handled; here handle
    'Do X and also teach Y' / 'Do X then compare Y' within one clause.
    Also split heterogeneous longest/shortest metric bindings.
    """
    text = clause.strip()
    if len(text) < 12:
        return [text]

    hetero = _split_heterogeneous_metric_clauses(text)
    if len(hetero) > 1:
        return hetero

    # Split before a new request cue after a soft boundary (and/then/also/,)
    pattern = re.compile(
        r"(?i)(?:\s+(?:and\s+also|and\s+then|then|also|,)\s+)(?="
        r"(?:explain|teach|compare|translate|give|show|list|find|"
        r"continue|another|what|how|why|define|describe|quiz|pronounce|"
        r"provide|summarise|summarize|"
        r"(?:the\s+)?(?:\d+\s+|top\s+\d+\s+)?(?:longest|shortest))\b)"
    )
    parts = pattern.split(text)
    if len(parts) <= 1:
        return [text]

    out = [_normalize_segment(p) for p in parts if _normalize_segment(p)]
    return out or [text]


def topic_from_message(message: str, intent: str = "") -> str:
    """Derive a short topic label for a sub-request (for merge headings)."""
    low = (message or "").lower()
    for label, pat in (
        ("Morphology", r"\bmorphology\b"),
        ("Pronunciation", r"\bpronounc\w*|\bipa\b"),
        ("Syntax", r"\bsyntax\b|\bword\s+order\b"),
        ("Semantics", r"\bsemantics\b"),
        ("Phonology", r"\bphonology\b|\bphonetics?\b"),
        ("Grammar comparison", r"\bcompare\b.*\bgrammar\b|\bgrammar\b.*\bcompare\b"),
        ("Grammar", r"\bgrammar\b"),
        ("Translation", r"\btranslate\b|\bhow\s+do\s+(?:i|you)\s+say\b"),
        ("Example", r"\bexample\b"),
        ("Follow-up", r"^(continue|another|more|why\??)$"),
        ("Culture", r"\bculture\b"),
        ("Quiz", r"\bquiz\b"),
        ("Vocabulary", r"\bvocab|longest|shortest|greeting|words?\b"),
    ):
        if re.search(pat, low):
            return label
    if intent:
        return intent.replace("_", " ").title()
    return "Request"


def build_multi_plan(
    message: str,
    lang_key: Optional[str] = None,
    level_num: Optional[int] = None,
    mode: Optional[str] = None,
) -> MultiIntentPlan:
    """
    Decompose a user message into an ordered MultiIntentPlan.

    Single-request messages yield one step (multi=False).
    Multi-request messages yield N steps, each with its own TutorPlan.
    """
    text = (message or "").strip()
    segments = decompose_message(text)

    # If decomposition produced many tiny fragments of the same short message, collapse
    if len(segments) > 1:
        # Keep only segments that look like requests OR are the sole content of a line
        filtered = []
        for seg in segments:
            if _REQUEST_CUE.search(seg) or len(segments) <= 12:
                filtered.append(seg)
        segments = filtered or segments

    # Single-intent fast path: one segment OR decomposition didn't add value
    if len(segments) <= 1:
        plan = build_plan(text, lang_key, level_num, mode)
        step = IntentStep(
            index=1,
            message=text,
            plan=plan,
            topic=topic_from_message(text, plan.intent),
            languages=list(plan.entities or ([plan.language] if plan.language else [])),
        )
        return MultiIntentPlan(original_message=text, steps=[step], multi=False)

    steps: list[IntentStep] = []
    for i, seg in enumerate(segments, start=1):
        # Carry UI language context; each segment extracts its own entities
        plan = build_plan(seg, lang_key, level_num, mode if i == 1 else None)
        langs = list(plan.entities or [])
        # Only attach UI language when the segment itself mentions a language
        # or clearly needs lesson scope (not pure metalinguistic prompts).
        if not langs and plan.language and (
            extract_languages(seg)
            or plan.intent
            in (
                TEACHING,
                TRANSLATION,
                EXAMPLE_SENTENCE,
                VOCABULARY_LOOKUP,
                STATISTICS,
                ANALYTICS,
                RANKING,
                SEARCH,
                CULTURE,
                LONGEST_WORD,
                SHORTEST_WORD,
                DIFFICULT_WORDS,
                QUIZ,
                COMPARE,
                COMPARISON,
            )
        ):
            langs = [plan.language]
        steps.append(
            IntentStep(
                index=i,
                message=seg,
                plan=plan,
                topic=topic_from_message(seg, plan.intent),
                languages=langs,
            )
        )

    return MultiIntentPlan(
        original_message=text,
        steps=steps,
        multi=len(steps) > 1,
    )


# ---------------------------------------------------------------------------
# Off-topic
# ---------------------------------------------------------------------------

# Truly off-mission / unsafe only. General education (math, economics, CS
# concepts, study advice, product how-to) must NOT be refused here.
_OFF_TOPIC_PATTERNS = [
    r"\b(messi|ronaldo|celebrity|celebrities|nascar|taylor\s+swift|elon\s+musk)\b",
    r"\b(weather|forecast|temperature|rain|humidity)\b",
    r"\b(capital\s+of|president\s+of|prime\s+minister)\b",
    r"\b(stock|stocks|crypto|bitcoin|ethereum|nft)\b",
    r"\b(joke|jokes|meme|memes|riddle)\b",
    r"\b(recipe|recipes|cook|cooking|bake|baking)\b",
    r"\b(sports?|football|soccer|nba|fifa|match\s+score|world\s+cup)\b",
    r"\b(politics|election)\b",
    r"\b(write\s+(me\s+)?(a\s+|an\s+)?(essay|poem|song|story)\b)",
    r"\b(write\s+(me\s+)?(a\s+|an\s+|some\s+)?(code|python(\s+code|\s+script)?|javascript(\s+code|\s+app)?))\b",
    r"\b(latest\s+news|breaking\s+news|who\s+won)\b",
    r"\b(password|passwd|credentials?|login\s+details?|netflix|spotify|wifi\s+password)\b",
    r"\b(hack|phishing|credit\s+card|ssn|social\s+security)\b",
]

# Product / website help — never treat as vocabulary lookup.
_PRODUCT_HELP_RE = re.compile(
    r"\b("
    r"achievements?\s+page|passport\s+page|dictionary\s+page|settings\s+page|"
    r"world\s+explorer|explorer\s+page|dashboard|"
    r"ai\s+tutor|this\s+(app|site|website|product)|"
    r"how\s+does\s+(the\s+)?(app|site|website|tutor|mascot|stamp)|"
    r"what\s+does\s+the\s+(achievements?|passport|dictionary|quiz|explorer|settings)\b|"
    r"stamp\s+collection|mascot\s+settings?"
    r")\b",
    re.I,
)

# General education outside heritage-language lesson facts.
_GENERAL_EDUCATION_RE = re.compile(
    r"\b("
    r"math(?:ematics)?|algebra|calculus|geometry|trigonometry|"
    r"equation|quadratic|discriminant|integral|derivative|polynomial|"
    r"economics?|opportunity\s+cost|inflation|supply\s+and\s+demand|"
    r"computer\s+science|embedded\s+system|algorithm|data\s+structure|"
    r"operating\s+system|compiler|binary\s+tree|recursion|"
    r"physics|chemistry|biology|photosynthesis|"
    r"study\s+(tip|tips|advice|habit|habits|technique|techniques)|"
    r"how\s+can\s+i\s+study|memorize|flash\s*cards?|spaced\s+repetition"
    r")\b",
    re.I,
)

_DOMAIN_HINTS = [
    r"\b(vocabulary|vocab|word|words|phrase|translate|translation|grammar|"
    r"pronounce|pronunciation|ipa|phonetic|phonology|morphology|syntax|"
    r"semantics|pragmatics|discourse|orthography|etymology|culture|"
    r"cultural|tradition|festival|lesson|quiz|greeting|dialogue|"
    r"conversation|sentence|example|noun|verb|adjective|length|longest|"
    r"shortest|difficult|meaning|compare|average|top\s+\d+|rank|"
    r"linguistics|language\s+family|writing\s+system)\b",
]


def is_off_topic(message: str) -> bool:
    """Refuse only unsafe / entertainment / trivia — never general education."""
    text = (message or "").strip().lower()
    if not text:
        return False
    # Product help and general education are always in-scope for answering.
    if _PRODUCT_HELP_RE.search(text) or _GENERAL_EDUCATION_RE.search(text):
        return False
    if domain_language_pattern().search(text) or any(
        re.search(p, text, re.I) for p in _DOMAIN_HINTS
    ):
        if re.search(
            r"\b(messi|ronaldo|weather|forecast|capital\s+of|bitcoin)\b",
            text,
            re.I,
        ) and not (
            domain_language_pattern().search(text)
            or re.search(r"\b(translate|vocabulary|grammar|lesson|word)\b", text, re.I)
        ):
            return True
        return False
    if re.search(r"(?i)^\s*who\s+(is|are|was|were)\b", text):
        return True
    return any(re.search(p, text, re.I) for p in _OFF_TOPIC_PATTERNS)


def is_general_education_request(message: str) -> bool:
    """True for non-language educational / product-help questions."""
    text = (message or "").strip()
    if not text:
        return False
    if _PRODUCT_HELP_RE.search(text):
        return True
    if _GENERAL_EDUCATION_RE.search(text):
        # Still treat as language-fact if it asks for heritage-language DB claims.
        if domain_language_pattern().search(text) and re.search(
            r"\b(translate|longest|shortest|vocabulary\s+list|quiz|this\s+lesson|"
            r"meaning\s+of|what\s+does\s+\w+\s+mean)\b",
            text,
            re.I,
        ):
            return False
        return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STOP = {
    "a", "an", "the", "to", "of", "in", "on", "for", "and", "or", "is", "are",
    "am", "i", "you", "me", "my", "your", "how", "do", "does", "what", "who",
    "when", "where", "why", "this", "that", "with", "from", "about", "please",
    "can", "could", "would", "tell", "give", "show", "find", "look", "up",
}

_ORDINALS = {
    "first": 0, "1st": 0,
    "second": 1, "2nd": 1,
    "third": 2, "3rd": 2,
    "fourth": 3, "4th": 3,
    "fifth": 4, "5th": 4,
    "sixth": 5, "6th": 5,
    "seventh": 6, "7th": 6,
    "eighth": 7, "8th": 7,
    "ninth": 8, "9th": 8,
    "tenth": 9, "10th": 9,
}

_WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
}


def _requested_count(message: str, default: int = 12) -> int:
    match = re.search(r"\btop\s+(\d+)\b", message or "", re.I)
    if match:
        return max(1, min(50, int(match.group(1))))
    match = re.search(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"fifteen|twenty|\d+)\b",
        message or "",
        re.I,
    )
    if not match:
        return default
    token = match.group(1).lower()
    if token.isdigit():
        return max(1, min(50, int(token)))
    return _WORD_NUMS.get(token, default)


# ---------------------------------------------------------------------------
# Generalized count/ordinal extraction.
#
# The requested quantity in a vocabulary/ranking question can be phrased as:
#   digit ("5"), word-number ("five"), "top N", "top five", "first N",
#   "bottom N", or a bare cardinal anywhere in the sentence regardless of
#   singular/plural wording ("5 longest word" vs "5 longest words").
#
# This is a single, general-purpose extractor used by every ranking/random
# branch below — there is no per-phrase special case.
# ---------------------------------------------------------------------------

_NUM_TOKEN = (
    r"(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|fifteen|twenty)"
)


def _num_token_to_int(token: str) -> Optional[int]:
    token = (token or "").lower()
    if token.isdigit():
        return int(token)
    return _WORD_NUMS.get(token)


def _keyword_count(text: str, keyword: str) -> Optional[int]:
    """Match '<keyword> <number>' (digit or word-number). e.g. top five, bottom 5."""
    m = re.search(rf"\b{keyword}\s+({_NUM_TOKEN})\b", text, re.I)
    if not m:
        return None
    val = _num_token_to_int(m.group(1))
    return max(1, min(50, val)) if val else None


def _bare_count(text: str) -> Optional[int]:
    """
    A cardinal number appearing anywhere in the sentence that is not part of
    an ordinal ("2nd"), a level/lesson reference, or a language name digit.

    Used as the last-resort explicit-count signal so that phrasing like
    "5 longest word" (singular) is treated identically to
    "5 longest words" (plural) or "top 5 longest words".
    """
    low = (text or "").lower()
    m = re.search(r"\b(\d{1,2})\b", low)
    if m:
        span_start = m.start(1)
        # Skip digits that are actually ordinals ("5th") or level/lesson refs.
        tail = low[m.end(1):m.end(1) + 3]
        if re.match(r"\s*(st|nd|rd|th)\b", tail):
            m = None
        else:
            prefix = low[max(0, span_start - 10):span_start]
            if re.search(r"\b(level|lesson|unit)\s*$", prefix):
                m = None
    if m:
        val = int(m.group(1))
        if 1 <= val <= 50:
            return val
    m2 = re.search(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"fifteen|twenty)\b",
        low,
    )
    if m2:
        return _WORD_NUMS.get(m2.group(1))
    return None


def extract_translation_payload(message: str) -> tuple[str, str, str]:
    text = (message or "").strip()
    m = re.search(
        r"(?is)^\s*translate(?:\s+this)?(?:\s+to\s+([\w\-\s]+))?\s*[:\-]?\s*(.+)$",
        text,
    )
    if m:
        target_raw = (m.group(1) or "").strip()
        target = resolve_language(target_raw) or target_raw.lower()
        return m.group(2).strip().strip("\"'"), "en", target

    m = re.search(
        r"(?is)how\s+do\s+(?:i|you)\s+say\s+['\"]?(.+?)['\"]?(?:\s+in\s+([\w\-\s]+))?\s*\??\s*$",
        text,
    )
    if m:
        target_raw = (m.group(2) or "").strip()
        target = resolve_language(target_raw) or target_raw.lower()
        return m.group(1).strip(), "en", target

    return text, "en", ""


def tokenize_for_translation(source: str) -> list[str]:
    words = re.findall(r"[A-Za-z']+", source or "")
    tokens = []
    for w in words:
        low = w.lower()
        if low in _STOP or len(low) < 2:
            continue
        if low not in tokens:
            tokens.append(low)
    return tokens


def _mode_intent(mode: Optional[str]) -> Optional[str]:
    return {
        "quiz": QUIZ,
        "explain": GRAMMAR_EXPLANATION,
        "example": EXAMPLE_SENTENCE,
        "culture": CULTURE,
    }.get((mode or "").strip().lower())


def resolve_scope(
    message: str,
    entities: list[str],
    current_lang: Optional[str],
    current_lesson: Optional[int],
) -> tuple[str, Optional[str], Optional[int], bool]:
    """Returns (scope, language_scope, lesson_scope, search_all_lessons)."""
    low = (message or "").lower()

    if re.search(
        r"\b(all\s+languages?|every\s+language|across\s+(all\s+)?languages?|"
        r"whole\s+database|entire\s+database|across\s+the\s+database|"
        r"all\s+supported\s+languages|compare\s+all|rank\s+all|"
        r"which\s+language|hardest\s+language|easiest\s+language|"
        r"most\s+difficult\s+language)\b",
        low,
    ):
        return SCOPE_DATABASE, None, None, True

    if len(entities) > 1:
        return SCOPE_SELECTED, None, None, True

    if len(entities) == 1:
        if re.search(r"\b(this\s+lesson|current\s+lesson|level\s+\d+)\b", low):
            lesson = current_lesson
            m = re.search(r"\blevel\s+(\d+)\b", low)
            if m:
                lesson = int(m.group(1))
            return SCOPE_LESSON, entities[0], lesson, False
        return SCOPE_LANGUAGE, entities[0], None, True

    if re.search(r"\b(this\s+lesson|current\s+lesson)\b", low):
        return SCOPE_LESSON, current_lang, current_lesson, False

    if re.search(r"\b(this\s+language|whole\s+language|all\s+lessons?)\b", low):
        return SCOPE_LANGUAGE, current_lang, None, True

    return SCOPE_LESSON, current_lang, current_lesson, False


# ---------------------------------------------------------------------------
# Compositional query structure parser (data-driven analytics)
# ---------------------------------------------------------------------------

@dataclass
class QueryStructure:
    """Universal analytics / retrieval structure — not a special case."""
    operation: str = "retrieve"  # retrieve|aggregate|rank|count|filter|compare
    table: str = "vocabulary"
    metric: Optional[str] = None  # word_length | difficulty | count
    aggregation: Optional[str] = None  # max|min|avg|count|rank|none
    target_field: Optional[str] = None
    order: Optional[str] = None  # asc|desc
    limit: Optional[int] = None
    offset: int = 0
    filters: list[dict[str, Any]] = field(default_factory=list)
    part_of_speech: Optional[str] = None
    meanings: list[str] = field(default_factory=list)
    detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "table": self.table,
            "metric": self.metric,
            "aggregation": self.aggregation,
            "field": self.target_field,
            "order": self.order,
            "limit": self.limit,
            "offset": self.offset,
            "filters": list(self.filters),
            "part_of_speech": self.part_of_speech,
            "meanings": list(self.meanings),
        }


@dataclass
class QueryClause:
    """One structured analytics atom: languages + structure + source span."""
    languages: list[str]
    structure: QueryStructure
    message: str


def parse_query_clauses(message: str) -> list[QueryClause]:
    """
    Bind structured metrics to nearby languages as independent clauses.

    Heterogeneous metrics (longest + shortest) become separate clauses so each
    language keeps its own aggregation. Same-metric multi-language compares
    remain a single clause with multiple languages.
    """
    text = (message or "").strip()
    if not text:
        return []

    fragments = _split_heterogeneous_metric_clauses(text)
    clauses: list[QueryClause] = []
    for frag in fragments:
        structure = parse_query_structure(frag)
        langs = extract_languages(frag)
        if structure.detected or langs:
            clauses.append(
                QueryClause(languages=list(langs), structure=structure, message=frag)
            )

    if not clauses:
        structure = parse_query_structure(text)
        return [
            QueryClause(
                languages=extract_languages(text),
                structure=structure,
                message=text,
            )
        ]
    return clauses


def parse_query_structure(message: str) -> QueryStructure:
    """
    Compositionally extract metric / aggregation / order / limit / filters.

    Examples mapped structurally (not as named features):
      longest word          → metric=word_length, aggregation=max, limit=1
      second longest        → metric=word_length, order=desc, offset=1, limit=1
      top 20 shortest       → metric=word_length, order=asc, limit=20
      average length        → aggregation=avg, field=word_length
      words longer than 10  → filter word_length>10
      how many greetings    → aggregation=count, filter pos=greeting

    For messages that mix opposing metrics across languages, prefer
    parse_query_clauses() — this function returns one structure for one span.
    """
    text = message or ""
    low = text.lower()
    spec = QueryStructure()

    # --- ordinal offset ("second longest", "3rd shortest") ---
    ord_m = re.search(
        r"\b(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|"
        r"sixth|6th|seventh|7th|eighth|8th|ninth|9th|tenth|10th)\b",
        low,
    )
    if ord_m:
        spec.offset = _ORDINALS.get(ord_m.group(1), 0)
        spec.operation = "rank"
        spec.detected = True

    # --- explicit top N / bottom N / first N (digit or word-number) ---
    top_m = _keyword_count(low, "top")
    if top_m is not None:
        spec.limit = top_m
        spec.operation = "rank"
        spec.detected = True

    bottom_m = _keyword_count(low, "bottom")
    if bottom_m is not None:
        spec.limit = bottom_m
        spec.operation = "rank"
        spec.detected = True
        # "bottom N longest" means the shortest among long ranking → ascending length
        if re.search(r"\blongest\b", low):
            spec.metric = "word_length"
            spec.order = "asc"
            spec.aggregation = "rank"
        elif re.search(r"\bshortest\b", low):
            spec.metric = "word_length"
            spec.order = "desc"
            spec.aggregation = "rank"

    # "first N" (N > 1) means "top N" — distinct from the ordinal "first"
    # (position 1) handled above, which only fires without a following count.
    first_m = re.search(rf"\bfirst\s+({_NUM_TOKEN})\b", low)
    if first_m and top_m is None:
        val = _num_token_to_int(first_m.group(1))
        if val and val > 1:
            spec.limit = max(1, min(50, val))
            spec.operation = "rank"
            spec.offset = 0
            spec.detected = True
            top_m = spec.limit

    # --- length metric ---
    # "biggest"/"largest word" and "smallest/tiniest word" are common
    # paraphrases of longest/shortest word. Normalize only for this length
    # block's own keyword checks (never mutates the shared `low` used by
    # unrelated patterns like "largest vocabulary" below, which means size).
    len_low = re.sub(r"\b(?:biggest|largest)\s+word", "longest word", low)
    len_low = re.sub(r"\b(?:smallest|tiniest)\s+word", "shortest word", len_low)
    len_low = re.sub(r"\bbiggest\b", "longest", len_low)
    len_low = re.sub(r"\bsmallest\b", "shortest", len_low)

    if re.search(
        r"\b(longest|shortest|word\s+length|letter(?:s)?|characters?|"
        r"longer\s+than|shorter\s+than|average\s+(?:\w+\s+){0,3}length|"
        r"avg\s+(?:\w+\s+){0,2}length)\b",
        len_low,
    ):
        spec.metric = "word_length"
        spec.target_field = "word_length"
        spec.detected = True

        # A bare cardinal ("5 longest word") is treated exactly like an
        # explicit "top N" — singular/plural wording never changes the
        # requested quantity. Explicit counts (top/bottom/first N) always
        # take priority over a bare ordinal ("first" alone = position 1).
        bare_n = None if (top_m or bottom_m) else _bare_count(text)
        explicit_n = top_m or bare_n

        if re.search(r"\bshortest\b", len_low):
            spec.order = "asc"
            if explicit_n or re.search(r"\bshortest\s+words\b", len_low):
                spec.operation = "rank"
                spec.aggregation = "rank"
                spec.limit = spec.limit or explicit_n or _requested_count(text, 10)
            elif ord_m:
                spec.operation = "rank"
                spec.aggregation = "rank"
                spec.limit = 1
                spec.order = "asc"
            else:
                spec.aggregation = "min"
                spec.limit = spec.limit or 1
                spec.operation = "aggregate"
        elif re.search(r"\blongest\b", len_low):
            spec.order = "desc"
            if explicit_n or re.search(r"\blongest\s+words\b", len_low):
                spec.operation = "rank"
                spec.aggregation = "rank"
                spec.limit = spec.limit or explicit_n or _requested_count(text, 10)
            elif ord_m:
                spec.operation = "rank"
                spec.aggregation = "rank"
                spec.limit = 1
                spec.order = "desc"
            else:
                spec.aggregation = "max"
                spec.limit = 1
                spec.operation = "aggregate"

        if re.search(r"\b(average|avg|mean)\b", low):
            spec.aggregation = "avg"
            spec.operation = "aggregate"
            spec.limit = None
            spec.offset = 0

        if re.search(r"\bmedian\b", low):
            spec.aggregation = "median"
            spec.operation = "aggregate"
            spec.metric = "word_length"
            spec.target_field = "word_length"
            spec.detected = True

    # --- random sample / another / give me another ---
    if re.search(
        r"\brandom\b|"
        r"\b(?:give|show|get)\s+me\s+another\b|"
        r"\banother\s+word\b|"
        r"\bone\s+more\s+word\b",
        low,
    ):
        spec.operation = "retrieve"
        spec.aggregation = "random"
        spec.order = "random"
        # Honour "five random", "3 random greetings", etc.
        n = _requested_count(text, 1)
        spec.limit = n if n else (spec.limit or 1)
        spec.detected = True

    # --- alphabetical listing ---
    if re.search(r"\balphabet(?:ical(?:ly)?)?\b", low):
        spec.operation = "retrieve"
        spec.order = "alpha"
        spec.limit = spec.limit or _requested_count(text, 20)
        spec.detected = True

    # --- frequency / most common POS ---
    if re.search(
        r"\b(most\s+common|frequency|distribution|part\s+of\s+speech\s+count|"
        r"least\s+common|least\s+frequent|rarest)\b",
        low,
    ):
        if re.search(r"\b(least\s+common|least\s+frequent|rarest)\b", low):
            spec.metric = "difficulty"
            spec.order = "asc"
            spec.operation = "rank"
            spec.aggregation = "rank"
            spec.limit = spec.limit or _requested_count(text, 10)
        else:
            spec.operation = "aggregate"
            spec.aggregation = "frequency"
            spec.metric = "part_of_speech"
            spec.target_field = "part_of_speech"
            spec.limit = spec.limit or 10
        spec.detected = True

    # --- length filters ---
    gt = re.search(
        r"\b(?:longer|more)\s+than\s+(\d+)\s*(?:letters?|characters?|chars?)?\b",
        low,
    )
    if gt:
        spec.filters.append({"field": "word_length", "op": ">", "value": int(gt.group(1))})
        spec.metric = spec.metric or "word_length"
        spec.operation = "filter" if spec.operation == "retrieve" else spec.operation
        spec.order = spec.order or "desc"
        spec.limit = spec.limit or 20
        spec.detected = True

    lt = re.search(
        r"\b(?:shorter|fewer)\s+than\s+(\d+)\s*(?:letters?|characters?|chars?)?\b",
        low,
    )
    if lt:
        spec.filters.append({"field": "word_length", "op": "<", "value": int(lt.group(1))})
        spec.metric = spec.metric or "word_length"
        spec.operation = "filter" if spec.operation == "retrieve" else spec.operation
        spec.order = spec.order or "asc"
        spec.limit = spec.limit or 20
        spec.detected = True

    # --- difficulty ---
    if re.search(r"\b(difficult|hardest|most\s+difficult|hard\s+words?)\b", low):
        spec.metric = "difficulty"
        spec.target_field = "difficulty"
        spec.order = "asc"  # hard first via CASE in SQL
        spec.operation = "rank"
        spec.aggregation = "rank"
        spec.limit = spec.limit or _requested_count(text, 12)
        spec.detected = True

    if re.search(r"\baverage\s+difficulty\b", low):
        spec.metric = "difficulty"
        spec.aggregation = "avg"
        spec.operation = "aggregate"
        spec.detected = True

    # --- pattern filters ---
    sw = re.search(
        r"\b(?:words?\s+)?(?:start(?:s|ing)?\s+with|begin(?:s|ning)?\s+with|"
        r"beginning\s+with)\s+['\"]?([a-z]{1,4})['\"]?\b",
        low,
    )
    if sw:
        spec.filters.append({"field": "word", "op": "starts_with", "value": sw.group(1)})
        spec.operation = "filter"
        spec.limit = spec.limit or 20
        spec.detected = True

    ew = re.search(
        r"\b(?:words?\s+)?(?:end(?:s|ing)?\s+with)\s+['\"]?([a-z]{1,4})['\"]?\b",
        low,
    )
    if ew:
        spec.filters.append({"field": "word", "op": "ends_with", "value": ew.group(1)})
        spec.operation = "filter"
        spec.limit = spec.limit or 20
        spec.detected = True

    cw = re.search(
        r"\b(?:words?\s+)?contain(?:s|ing)?\s+['\"]?([a-z]{1,6})['\"]?\b",
        low,
    )
    if cw:
        spec.filters.append({"field": "word", "op": "contains", "value": cw.group(1)})
        spec.operation = "filter"
        spec.limit = spec.limit or 20
        spec.detected = True

    # --- numeric length comparisons (between / greater / less / equal) ---
    bt = re.search(
        r"\bbetween\s+(\d+)\s+and\s+(\d+)\s*(?:letters?|characters?|chars?)?\b",
        low,
    )
    if bt:
        lo, hi = int(bt.group(1)), int(bt.group(2))
        if lo > hi:
            lo, hi = hi, lo
        spec.filters.append({"field": "word_length", "op": "between", "value": [lo, hi]})
        spec.metric = spec.metric or "word_length"
        spec.operation = "filter"
        spec.limit = spec.limit or 20
        spec.detected = True

    gt2 = re.search(
        r"\b(?:greater\s+than|more\s+than|>\s*)\s*(\d+)\s*(?:letters?|characters?|chars?)?\b",
        low,
    )
    if gt2 and not gt:
        spec.filters.append({"field": "word_length", "op": ">", "value": int(gt2.group(1))})
        spec.metric = spec.metric or "word_length"
        spec.operation = "filter"
        spec.limit = spec.limit or 20
        spec.detected = True

    lt2 = re.search(
        r"\b(?:less\s+than|fewer\s+than|<\s*)\s*(\d+)\s*(?:letters?|characters?|chars?)?\b",
        low,
    )
    if lt2 and not lt:
        spec.filters.append({"field": "word_length", "op": "<", "value": int(lt2.group(1))})
        spec.metric = spec.metric or "word_length"
        spec.operation = "filter"
        spec.limit = spec.limit or 20
        spec.detected = True

    eq = re.search(
        r"\b(?:equal\s+to|exactly)\s+(\d+)\s*(?:letter(?:s)?|character(?:s)?|chars?)?\b|"
        r"\b(\d+)\s*[- ]?letter\s+words?\b",
        low,
    )
    if eq:
        val = int(eq.group(1) or eq.group(2))
        spec.filters.append({"field": "word_length", "op": "=", "value": val})
        spec.metric = spec.metric or "word_length"
        spec.operation = "filter"
        spec.limit = spec.limit or 20
        spec.detected = True

    # --- excluding / except POS ---
    ex = re.search(
        r"\b(?:exclud(?:e|ing)|except)\s+(greetings?|nouns?|verbs?|adjectives?|phrases?)\b",
        low,
    )
    if ex:
        raw = ex.group(1).lower().rstrip("s")
        pos_norm = {
            "greeting": "greeting",
            "noun": "noun",
            "verb": "verb",
            "adjective": "adjective",
            "phrase": "phrase",
        }.get(raw, raw)
        if raw.startswith("greeting"):
            pos_norm = "greeting"
        spec.filters.append({"field": "part_of_speech", "op": "!=", "value": pos_norm})
        spec.operation = "filter"
        spec.limit = spec.limit or 20
        spec.detected = True

    # --- common / rare / best (mapped to frequency or difficulty ranks) ---
    if re.search(r"\b(common\s+words?|most\s+common\s+words?)\b", low):
        spec.metric = "difficulty"
        spec.order = "desc"  # easy/common first via SQL CASE if needed
        spec.operation = "rank"
        spec.aggregation = "rank"
        spec.limit = spec.limit or 10
        spec.detected = True
    if re.search(r"\b(rare\s+words?|uncommon\s+words?)\b", low):
        spec.metric = "difficulty"
        spec.order = "asc"  # hard/rare first
        spec.operation = "rank"
        spec.aggregation = "rank"
        spec.limit = spec.limit or 10
        spec.detected = True
    if re.search(r"\bbest\s+greeting", low):
        spec.part_of_speech = "greeting"
        spec.filters.append({"field": "part_of_speech", "op": "=", "value": "greeting"})
        spec.operation = "rank"
        spec.limit = 1
        spec.detected = True

    # mode POS ≈ frequency top-1
    if re.search(r"\bmode\s+part\s+of\s+speech\b|\bmost\s+frequent\s+pos\b", low):
        spec.operation = "aggregate"
        spec.aggregation = "frequency"
        spec.metric = "part_of_speech"
        spec.limit = 1
        spec.detected = True

    # --- POS / category ---
    pos_map = {
        r"\bgreetings?\b": "greeting",
        r"\bnouns?\b": "noun",
        r"\bverbs?\b": "verb",
        r"\badjectives?\b": "adjective",
        r"\bphrases?\b": "phrase",
    }
    for pat, pos in pos_map.items():
        if re.search(pat, low):
            spec.part_of_speech = pos
            spec.filters.append({"field": "part_of_speech", "op": "=", "value": pos})
            spec.detected = True
            break

    # --- counts / size ---
    if re.search(
        r"\b(how\s+many|count|number\s+of|vocabulary\s+size|word\s+count|"
        r"largest\s+vocabulary|biggest\s+vocabulary|most\s+words)\b",
        low,
    ):
        spec.aggregation = "count"
        spec.operation = "count"
        spec.metric = "count"
        spec.detected = True
        if re.search(r"\bgrammar\b", low):
            spec.table = "grammar"
        elif re.search(r"\bculture\b", low):
            spec.table = "culture"
        else:
            spec.table = "vocabulary"

    # --- table hints ---
    if re.search(r"\bgrammar\b", low) and spec.operation in ("retrieve", "count"):
        if re.search(r"\b(how\s+many|count)\b", low):
            spec.table = "grammar"
    if re.search(r"\bculture\b", low) and re.search(r"\b(how\s+many|count)\b", low):
        spec.table = "culture"

    # ordinal without metric defaults to length ranking when "word" context
    if ord_m and not spec.metric and re.search(r"\bword", low):
        spec.metric = "word_length"
        spec.order = "desc"
        spec.limit = 1
        spec.operation = "rank"
        spec.aggregation = "rank"
        spec.detected = True

    if spec.detected and spec.limit is None and spec.operation in ("rank", "filter", "retrieve"):
        if spec.aggregation in ("max", "min"):
            spec.limit = 1
        elif spec.operation == "rank":
            spec.limit = spec.limit or 10

    return spec


def compute_plan_confidence(
    message: str,
    intent: str,
    entities: list[str],
    operations: list,
    notes: list[str],
) -> float:
    score = 0.55
    if intent not in (UNKNOWN, OFF_TOPIC):
        score += 0.15
    if entities:
        score += min(0.12, 0.04 * len(entities))
    if operations:
        score += 0.12
    if notes:
        score += 0.05
    if re.search(r"\band\b|\bcompare\b", message or "", re.I) and len(entities) < 2:
        score -= 0.08
    return round(min(0.99, max(0.2, score)), 2)


# ---------------------------------------------------------------------------
# Intent classification (domain categories — not analytics special cases)
# ---------------------------------------------------------------------------

def classify_intent(message: str, mode: Optional[str] = None) -> tuple[str, float, list[str]]:
    text = (message or "").strip()
    low = text.lower()
    mapped = _mode_intent(mode)
    notes: list[str] = []

    if mapped and not text:
        return mapped, 0.95, ["mode_button"]

    if is_off_topic(text):
        return OFF_TOPIC, 0.98, ["off_topic_detector"]

    # General education / website help — answer with GPT, not the language DB gate.
    if is_general_education_request(text):
        return GENERAL_KNOWLEDGE, 0.93, ["general_education"]

    if re.search(r"\b(easier|harder|easy|hard)\s+quiz\b|\bquiz\b.*\b(easier|harder|easy|hard)\b", low):
        return QUIZ, 0.96, ["quiz_difficulty_request"]

    if re.search(r"\b(quiz|test\s+me|question\s+me)\b", low) or mapped == QUIZ:
        return QUIZ, 0.95, []

    if re.search(r"(?i)\btranslate\b|how\s+do\s+(?:i|you)\s+say\b", text):
        return TRANSLATION, 0.93, ["translation_request"]

    if re.search(
        r"(?i)\b(pretend|role\s*play|talk\s+to\s+me|conversation|chat\s+with\s+me|"
        r"you\s+are\s+an?\s+\w+\s+villager)\b",
        text,
    ):
        return CONVERSATION, 0.9, ["conversation_mode"]

    # Comparison of entities
    if re.search(r"\bcompare\b|\bvs\.?\b|\bversus\b|\bdifference\s+between\b|\bwhat\s+is\s+the\s+difference\b", low):
        notes.append("comparison")
        # Fall through — structure decides statistics vs teaching compare

    # Linguistics domains (general knowledge allowed with disclaimer)
    if re.search(
        r"\b(phonetics?|phonology|morphology|syntax|semantics|pragmatics|"
        r"discourse|sociolinguistics|historical\s+linguistics|"
        r"language\s+acquisition|language\s+revitalization|language\s+endangerment|"
        r"endangered\s+languages?|language\s+famil(?:y|ies)|austronesian|"
        r"writing\s+system|orthography|etymology|word\s+order|svo|sov|vso|"
        r"typology|isolating\s+language|morpheme|phoneme|agglutination)\b",
        low,
    ):
        if re.search(r"\bmorphology\b", low):
            return MORPHOLOGY, 0.9, ["linguistics_domain"]
        if re.search(r"\bsyntax\b|word\s+order|svo|sov|vso", low):
            return SYNTAX, 0.9, ["linguistics_domain"]
        if re.search(r"\bsemantics\b", low):
            return SEMANTICS, 0.9, ["linguistics_domain"]
        if re.search(r"\b(ipa|phonetic|phonology|pronounc\w*|pronunc\w*)\b", low):
            return PRONUNCIATION, 0.9, ["linguistics_domain"]
        return LINGUISTICS, 0.88, ["linguistics_domain"]

    # Cross-language difficulty / size questions before local difficulty ranking
    if re.search(
        r"\b(hardest|easiest|most\s+difficult|least\s+difficult)\s+languages?\b|"
        r"\bwhich\s+language\s+is\s+(harder|hardest|easier|easiest)\b",
        low,
    ):
        return COMPARE, 0.93, notes + ["cross_language_difficulty"]

    # Compositional statistics / ranking / filters
    structure = parse_query_structure(text)
    if structure.detected:
        notes.append("compositional_query")
        if "comparison" in notes or re.search(r"\bcompare\b|\bvs\.?\b|\band\b", low):
            pass
        if structure.operation in ("count", "aggregate") and structure.aggregation in (
            "count", "avg", "max", "min", "median", "frequency"
        ):
            return STATISTICS, 0.94, notes + [f"agg:{structure.aggregation}"]
        if structure.aggregation == "random" or structure.order == "random":
            return ANALYTICS, 0.9, notes + ["random_sample"]
        if structure.order == "alpha":
            return SEARCH, 0.88, notes + ["alphabetical"]
        if structure.operation in ("rank", "filter") or structure.metric:
            if (
                structure.metric == "word_length"
                and structure.aggregation == "max"
                and (structure.limit or 1) == 1
                and structure.offset == 0
            ):
                return LONGEST_WORD, 0.95, notes
            if (
                structure.metric == "word_length"
                and structure.aggregation == "min"
                and (structure.limit or 1) == 1
                and structure.offset == 0
            ):
                return SHORTEST_WORD, 0.95, notes
            if structure.metric == "difficulty":
                return DIFFICULT_WORDS, 0.92, notes
            return RANKING if structure.operation == "rank" else ANALYTICS, 0.93, notes

    # Which language has more / larger vocabulary / rank all languages
    if re.search(
        r"\bwhich\s+lang(?:uage)?\s+has\b|\bmore\s+words\b|\blarger\s+vocabulary\b|"
        r"\bbigger\s+vocabulary\b|\bmost\s+words\b|\blargest\s+vocabulary\b|"
        r"\bmost\s+vocab\b|\bcompare\s+all\b|\beach\s+language\b|\ball\s+languages?\b|"
        r"\brank\s+all\s+languages\b|\bhardest\s+language\b|\beasiest\s+language\b|"
        r"\bmost\s+difficult\s+language\b|\bacross\s+all\s+languages\b|"
        r"\bbest\s+greeting\s+which\s+language\b",
        low,
    ):
        return COMPARE, 0.93, notes + ["vocab_size_compare"]

    if re.search(
        r"\bcompare\b|\bvs\.?\b|\bversus\b|\bdifference\s+between\b|"
        r"\bwhat\s+is\s+the\s+difference\b|\bdifferences?\s+between\b|"
        r"\bbedanya\b",
        low,
    ):
        return COMPARE, 0.94, notes or ["comparison"]

    if re.search(
        r"(?i)\b(introduce\s+myself|introduction|how\s+do\s+i\s+introduce|"
        r"teach\s+me|how\s+to\s+greet|meet\s+someone|say\s+hello|"
        r"explain\b|what\s+is\b|why\b|when\b|how\s+(?:do|does|to)\b|"
        r"common\s+mistakes?|practice\s+tip)\b",
        text,
    ):
        # Teaching + pronunciation/IPA is a pronunciation lesson, not intro teaching
        if re.search(r"(?i)\b(pronounc\w*|pronunc\w*|ipa|sound\s+like)\b", text):
            return PRONUNCIATION, 0.93, ["teaching_pronunciation"]
        if re.search(r"(?i)\b(teach|introduce|how\s+to\s+greet|say\s+hello)\b", text):
            return TEACHING, 0.94, ["teaching_request"]
        # "What is X?" with no heritage-language / linguistics signal → general education
        if (
            re.search(r"(?i)\b(what\s+is|what\s+are|why\s+(?:does|is|do|are)|explain)\b", text)
            and not domain_language_pattern().search(text)
            and not re.search(
                r"\b(morphology|syntax|phonology|linguistics|grammar|vocabulary|"
                r"iban|bidayuh|mah\s*meri|kadazan|dusun|lesson|quiz|translate)\b",
                low,
            )
        ):
            return GENERAL_KNOWLEDGE, 0.9, ["general_explanation"]
        return EXPLANATION, 0.9, ["explanation_request"]

    if mapped == GRAMMAR_EXPLANATION or re.search(
        r"(?i)\b(grammar|sentence\s+pattern|sentence\s+structure|common\s+mistake)\b",
        text,
    ):
        return GRAMMAR_EXPLANATION, 0.92, []

    if mapped == EXAMPLE_SENTENCE or re.search(
        r"(?i)\b(example|dialogue|sample\s+sentence|mini\s+dialogue|another example)\b",
        text,
    ):
        return EXAMPLE_SENTENCE, 0.9, []

    if mapped == CULTURE or re.search(
        r"(?i)\b(culture|cultural|tradition|festival|gawai|ngajat|longhouse|heritage)\b",
        text,
    ):
        return CULTURE, 0.9, []

    if re.search(r"(?i)\b(pronounce|pronunciation|ipa|sound\s+like)\b", text):
        return PRONUNCIATION, 0.9, []

    if re.search(r"(?i)\b(summary|summarise|summarize|today'?s\s+lesson|this\s+lesson)\b", text):
        return LESSON_SUMMARY, 0.88, []

    if re.search(
        r"(?i)\b(greeting|greetings|all\s+verbs|all\s+nouns|animals?|food|"
        r"numbers?|vocabulary|list\s+words|all\s+words)\b",
        text,
    ):
        return SEARCH, 0.88, ["category_or_list"]

    if re.search(r"(?i)\b(what\s+does|meaning\s+of|mean\??$|look\s+up)\b", text):
        return VOCABULARY_LOOKUP, 0.85, []

    if mapped:
        return mapped, 0.8, ["mode_fallback"]

    if len(text.split()) <= 4:
        return VOCABULARY_LOOKUP, 0.55, ["short_utterance_lookup"]

    return UNKNOWN, 0.4, ["unknown_default"]


# ---------------------------------------------------------------------------
# Operation builders
# ---------------------------------------------------------------------------

def _query_op(
    *,
    name: str,
    table: str,
    language: Optional[str],
    lesson_id: Optional[int],
    search_all: bool,
    structure: QueryStructure,
    required: bool = True,
) -> RetrievalOp:
    params = structure.to_dict()
    params.update(
        {
            "language": language,
            "lesson_id": lesson_id,
            "search_all": search_all if language else True,
            "limit": structure.limit or 12,
            "offset": structure.offset or 0,
        }
    )
    if structure.part_of_speech:
        params["part_of_speech"] = structure.part_of_speech
    if structure.meanings:
        params["meanings"] = structure.meanings
    return RetrievalOp(
        name=name,
        table=table or structure.table or "vocabulary",
        kind="query",
        params=params,
        required=required,
    )


def _ops_for_languages(
    structure: QueryStructure,
    languages: list[Optional[str]],
    lesson_id: Optional[int],
    search_all: bool,
) -> tuple[list[RetrievalOp], list[dict]]:
    ops: list[RetrievalOp] = []
    steps: list[dict] = []
    table = structure.table or "vocabulary"
    for idx, lang in enumerate(languages or [None]):
        label = display_name(lang) if lang else "all_languages"
        op_name = f"{structure.operation}_{structure.metric or structure.aggregation or 'query'}__{lang or 'all'}__{idx}"
        lang_search_all = search_all if lang else True
        ops.append(
            _query_op(
                name=op_name,
                table=table,
                language=lang,
                lesson_id=None if lang_search_all else lesson_id,
                search_all=lang_search_all,
                structure=structure,
            )
        )
        steps.append(
            {
                "step": idx + 1,
                "operation": structure.operation,
                "metric": structure.metric,
                "aggregation": structure.aggregation,
                "language": lang,
                "label": label,
                "table": table,
                "decompose": (
                    f"Retrieve {structure.operation}"
                    f"({structure.metric or structure.aggregation or 'rows'})"
                    f" for {label}"
                ),
            }
        )
    return ops, steps


def _topic_meanings(message: str) -> list[str]:
    stop = _STOP | {
        "word", "words", "meaning", "means", "mean", "does", "what",
        "vocabulary", "translate", "say", "in", "the", "a",
    }
    terms = []
    for w in re.findall(r"[a-zA-Z]{2,}", (message or "").lower()):
        if w not in stop and w not in terms:
            terms.append(w)
    return terms[:12]


def _quiz_difficulty(message: str) -> Optional[str]:
    low = (message or "").lower()
    if re.search(r"\b(easier|easy)\b", low):
        return "easy"
    if re.search(r"\b(harder|hard|difficult)\b", low):
        return "hard"
    return None


# ---------------------------------------------------------------------------
# build_plan — Universal Linguistics Query Engine entry point
# ---------------------------------------------------------------------------

def build_plan(
    message: str,
    lang_key: Optional[str] = None,
    level_num: Optional[int] = None,
    mode: Optional[str] = None,
) -> TutorPlan:
    text = (message or "").strip()
    normalized_mode = (mode or "").strip().lower() or None
    intent, confidence, notes = classify_intent(text, normalized_mode)
    entities = extract_languages(text)
    unsupported = extract_unsupported_language_mentions(text)
    unsupported = [
        u for u in unsupported
        if resolve_language(u) is None and not extract_languages(u)
    ]

    # Database-wide ranking language list
    if re.search(
        r"\b(all\s+supported\s+languages|which\s+language\s+has|largest\s+vocabulary|"
        r"biggest\s+vocabulary|across\s+all\s+languages|vocabulary\s+size\s+of\s+all|"
        r"compare\s+all|hardest\s+language|easiest\s+language)\b",
        text,
        re.I,
    ) and not entities:
        pass  # entities stay empty → scope database expands later

    scope, language_scope, lesson_scope, search_all = resolve_scope(
        text, entities, lang_key, level_num
    )

    # Force all-lessons for explicit database-wide analytics phrasing
    if re.search(
        r"\b(vocabulary\s+size\s+of\s+all|all\s+supported\s+languages|"
        r"which\s+language\s+has|largest\s+vocabulary|compare\s+all|"
        r"hardest\s+language|easiest\s+language)\b",
        text,
        re.I,
    ):
        scope = SCOPE_DATABASE
        search_all = True

    # COMPARE without named languages → compare across the whole registry
    if intent in (COMPARE, COMPARISON) and not entities:
        scope = SCOPE_DATABASE
        search_all = True

    structure = parse_query_structure(text)
    plan = TutorPlan(
        intent=intent,
        language=language_scope or lang_key,
        lesson_id=lesson_scope if not search_all else (
            lesson_scope if scope == SCOPE_LESSON else None
        ),
        search_all=search_all,
        message=text,
        mode=normalized_mode,
        confidence=confidence,
        notes=list(notes),
        entities=list(entities),
        scope=scope,
        language_scope=language_scope,
        lesson_scope=lesson_scope,
        unsupported=list(unsupported),
        query_spec=structure.to_dict() if structure.detected else {},
        need_reasoning=True,
        need_generation=True,
        allow_llm_rewrite=True,
    )

    # Only hard-refuse an unsupported-language mention when the question is
    # actually asking for LESSON-SPECIFIC facts about it (course vocabulary,
    # quiz, database counts). A general/comparative linguistics question that
    # merely *mentions* a non-course language (e.g. "compare Malay and
    # Indonesian grammar") must still reach GPT — the course database was
    # never going to have that answer anyway, and refusing would violate the
    # "GPT answers all in-domain language questions" policy.
    _wants_lesson_facts_for_unsupported = intent == QUIZ or bool(
        re.search(
            r"\b(vocabulary|vocab|word\s+list|words?\s+in|this\s+lesson|"
            r"course\s+database|longest|shortest|top\s+\d+|how\s+many|"
            r"quiz|greeting)\b",
            text,
            re.I,
        )
    )
    if (
        unsupported
        and not entities
        and intent not in (
            OFF_TOPIC,
            LINGUISTICS,
            MORPHOLOGY,
            SYNTAX,
            SEMANTICS,
            PRONUNCIATION,
            IPA,
            EXPLANATION,
        )
        and _wants_lesson_facts_for_unsupported
    ):
        plan.intent = UNSUPPORTED_LANGUAGE
        plan.require_evidence = False
        plan.allow_llm_rewrite = False
        plan.confidence = 0.99
        return plan

    if intent == OFF_TOPIC:
        plan.require_evidence = False
        plan.allow_llm_rewrite = False
        return plan

    # General education / product help: GPT path only — never invent language-DB ops
    # from incidental phrases like "number of real roots".
    if intent == GENERAL_KNOWLEDGE or is_general_education_request(text):
        plan.intent = GENERAL_KNOWLEDGE
        plan.require_evidence = False
        plan.operations = []
        plan.required_tables = []
        plan.query_spec = {}
        plan.response_type = "answer"
        plan.knowledge_policy = "general_education"
        plan.confidence = max(confidence, 0.9)
        plan.notes = list(dict.fromkeys(list(plan.notes) + ["general_education_no_db"]))
        return plan

    if unsupported and entities:
        plan.notes.append(f"unsupported_ignored:{','.join(unsupported)}")

    effective_lang = language_scope or lang_key
    effective_lesson = lesson_scope if scope == SCOPE_LESSON else None
    if scope == SCOPE_LANGUAGE:
        effective_lesson = None
        search_all = True
        plan.search_all = True

    # ---- QUIZ ----
    if intent == QUIZ:
        plan.quiz_difficulty = _quiz_difficulty(text)
        plan.required_tables = ["quiz"]
        plan.operations = [
            RetrievalOp(
                "quiz",
                "quiz",
                "query",
                {
                    "operation": "retrieve",
                    "table": "quiz",
                    "language": effective_lang,
                    "lesson_id": effective_lesson,
                    "search_all": False if effective_lesson is not None else True,
                    "limit": 40,
                    "filters": [],
                },
            )
        ]
        plan.operation = "quiz"
        plan.response_type = "quiz"
        plan.confidence = compute_plan_confidence(text, intent, entities, plan.operations, plan.notes)
        return plan

    # ---- Multi-language / statistics / ranking / compare ----
    stats_intents = {
        ANALYTICS, STATISTICS, RANKING, COMPARE, COMPARISON,
        LONGEST_WORD, SHORTEST_WORD, DIFFICULT_WORDS,
    }
    wants_compare = bool(
        re.search(r"\bcompare\b|\bvs\.?\b|\bversus\b|\bdifference\s+between\b", text, re.I)
    ) or len(entities) > 1

    # Clause-level binding: opposing metrics must not share one QueryStructure.
    clauses = parse_query_clauses(text)
    clause_signatures = {
        (
            c.structure.aggregation,
            c.structure.order,
            c.structure.operation,
            c.structure.limit,
        )
        for c in clauses
        if c.structure.detected
    }
    heterogeneous_clauses = len(clauses) > 1 and len(clause_signatures) > 1

    if heterogeneous_clauses:
        ops: list[RetrievalOp] = []
        steps: list[dict] = []
        bound_langs: list[str] = []
        search_for_ops = True if scope != SCOPE_LESSON else search_all
        for clause_idx, clause in enumerate(clauses):
            clause_langs = list(clause.languages) or (
                [effective_lang] if effective_lang else []
            )
            if not clause_langs:
                continue
            for lang in clause_langs:
                if lang and lang not in bound_langs:
                    bound_langs.append(lang)
            clause_ops, clause_steps = _ops_for_languages(
                clause.structure,
                clause_langs,
                effective_lesson,
                search_for_ops,
            )
            # Disambiguate op names across heterogeneous clauses
            for op in clause_ops:
                op.name = f"{op.name}__clause{clause_idx}"
            for step in clause_steps:
                step["clause"] = clause_idx
                step["clause_message"] = clause.message
                step["aggregation"] = clause.structure.aggregation
                step["order"] = clause.structure.order
            ops.extend(clause_ops)
            steps.extend(clause_steps)
        if ops:
            plan.operations = ops
            plan.execution_steps = steps
            plan.entities = bound_langs or list(entities)
            plan.required_tables = ["vocabulary"]
            plan.operation = "structured_multi_clause"
            plan.analytics_kind = "mixed:word_length"
            plan.compare_metric = "mixed:word_length"
            plan.query_spec = {
                "operation": "structured_multi_clause",
                "clauses": [
                    {
                        "languages": c.languages,
                        "structure": c.structure.to_dict(),
                        "message": c.message,
                    }
                    for c in clauses
                ],
            }
            plan.intent = COMPARE if len(bound_langs) > 1 else STATISTICS
            plan.response_type = "comparison" if len(bound_langs) > 1 else "analytics"
            plan.search_all = True
            plan.min_rows = 1
            plan.notes.append("heterogeneous_structured_clauses")
            plan.confidence = compute_plan_confidence(
                text, plan.intent, plan.entities, ops, plan.notes
            )
            return plan

    if intent in stats_intents or (structure.detected and (wants_compare or scope in (SCOPE_DATABASE, SCOPE_SELECTED))):
        if not structure.detected:
            # Default compare metric: vocabulary size
            structure = QueryStructure(
                operation="count",
                table="vocabulary",
                metric="count",
                aggregation="count",
                detected=True,
            )

        if scope == SCOPE_DATABASE and not entities:
            langs: list[Optional[str]] = list(get_language_keys())
            plan.entities = [L for L in langs if L]
            plan.scope = SCOPE_DATABASE
        elif entities:
            langs = list(entities)
        elif effective_lang:
            langs = [effective_lang]
        else:
            langs = list(get_language_keys())
            plan.entities = list(langs)
            plan.scope = SCOPE_DATABASE

        # Multi-lang always one op per language (never merge into one SQL)
        search_for_ops = True if scope != SCOPE_LESSON else search_all
        ops, steps = _ops_for_languages(
            structure, langs, effective_lesson, search_for_ops
        )
        plan.operations = ops
        plan.execution_steps = steps
        plan.required_tables = [structure.table or "vocabulary"]
        plan.operation = structure.operation
        plan.analytics_kind = (
            f"{structure.aggregation or structure.operation}:{structure.metric or structure.table}"
        )
        plan.compare_metric = plan.analytics_kind
        plan.query_spec = structure.to_dict()
        if len(langs) > 1 or wants_compare or scope == SCOPE_DATABASE:
            plan.intent = COMPARE if (wants_compare or len(langs) > 1) else STATISTICS
            plan.response_type = "comparison" if len(langs) > 1 else "analytics"
        else:
            if intent in (LONGEST_WORD, SHORTEST_WORD, DIFFICULT_WORDS):
                plan.response_type = "analytics"
            else:
                plan.intent = STATISTICS if structure.operation in ("count", "aggregate") else ANALYTICS
                plan.response_type = "analytics"
        plan.min_rows = 1
        plan.confidence = compute_plan_confidence(text, plan.intent, plan.entities, ops, plan.notes)
        return plan

    # Single-language compositional query
    if structure.detected:
        lang = effective_lang
        if not lang and entities:
            lang = entities[0]
        ops, steps = _ops_for_languages(
            structure,
            [lang],
            effective_lesson,
            search_all if scope != SCOPE_LESSON else search_all,
        )
        plan.operations = ops
        plan.execution_steps = steps
        plan.required_tables = [structure.table or "vocabulary"]
        plan.operation = structure.operation
        plan.analytics_kind = (
            f"{structure.aggregation or structure.operation}:{structure.metric or 'rows'}"
        )
        plan.query_spec = structure.to_dict()
        plan.response_type = "analytics"
        if intent not in (LONGEST_WORD, SHORTEST_WORD, DIFFICULT_WORDS):
            plan.intent = STATISTICS if structure.operation in ("count", "aggregate") else ANALYTICS
        plan.confidence = compute_plan_confidence(text, plan.intent, entities, ops, plan.notes)
        return plan

    # ---- TRANSLATION ----
    if intent == TRANSLATION:
        source, source_lang, target = extract_translation_payload(text)
        tokens = tokenize_for_translation(source)
        target_lang = resolve_language(target) if target else effective_lang
        plan.source_text = source
        plan.source_lang = source_lang
        plan.target_lang = target_lang or ""
        plan.tokens = tokens
        plan.language = target_lang or effective_lang
        plan.required_tables = ["vocabulary"]
        plan.operations = [
            RetrievalOp(
                "translation_vocab",
                "vocabulary",
                "query",
                {
                    "operation": "retrieve",
                    "table": "vocabulary",
                    "language": plan.language,
                    "lesson_id": effective_lesson,
                    "search_all": True,
                    "meanings": tokens,
                    "limit": 20,
                    "filters": [],
                },
            )
        ]
        plan.operation = "translate"
        plan.response_type = "translation"
        plan.min_rows = 1
        plan.confidence = compute_plan_confidence(text, intent, entities, plan.operations, plan.notes)
        return plan

    # ---- TEACHING / EXPLANATION / LESSON SUMMARY ----
    if intent in (TEACHING, EXPLANATION, LESSON_SUMMARY):
        plan.required_tables = ["vocabulary", "grammar", "culture"]
        plan.operations = [
            _query_op(
                name="vocab",
                table="vocabulary",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=search_all,
                structure=QueryStructure(
                    operation="retrieve", table="vocabulary", limit=20, detected=True
                ),
            ),
            _query_op(
                name="grammar",
                table="grammar",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=search_all,
                structure=QueryStructure(
                    operation="retrieve", table="grammar", limit=10, detected=True
                ),
                required=False,
            ),
            _query_op(
                name="culture",
                table="culture",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=search_all,
                structure=QueryStructure(
                    operation="retrieve", table="culture", limit=5, detected=True
                ),
                required=False,
            ),
        ]
        # Prefer greetings for introduction teaching
        if re.search(r"\b(introduce|greeting|hello)\b", text, re.I):
            plan.operations.insert(
                0,
                _query_op(
                    name="greetings",
                    table="vocabulary",
                    language=effective_lang,
                    lesson_id=effective_lesson,
                    search_all=True,
                    structure=QueryStructure(
                        operation="filter",
                        table="vocabulary",
                        part_of_speech="greeting",
                        filters=[{"field": "part_of_speech", "op": "=", "value": "greeting"}],
                        limit=10,
                        detected=True,
                    ),
                ),
            )
        plan.operation = "teach"
        plan.response_type = "teaching"
        plan.intent = TEACHING
        plan.confidence = compute_plan_confidence(text, TEACHING, entities, plan.operations, plan.notes)
        return plan

    # ---- GRAMMAR ----
    if intent in (GRAMMAR_EXPLANATION, GRAMMAR, SYNTAX, MORPHOLOGY):
        plan.required_tables = ["grammar", "vocabulary"]
        plan.operations = [
            _query_op(
                name="grammar",
                table="grammar",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=search_all,
                structure=QueryStructure(operation="retrieve", table="grammar", limit=10, detected=True),
            ),
            _query_op(
                name="vocab_support",
                table="vocabulary",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=search_all,
                structure=QueryStructure(operation="retrieve", table="vocabulary", limit=12, detected=True),
                required=False,
            ),
        ]
        plan.operation = "explain_grammar"
        plan.response_type = "grammar"
        plan.knowledge_policy = (
            "linguistics_with_disclaimer"
            if intent in (SYNTAX, MORPHOLOGY)
            else "database_first"
        )
        plan.confidence = compute_plan_confidence(text, intent, entities, plan.operations, plan.notes)
        return plan

    # ---- CULTURE ----
    if intent == CULTURE:
        plan.required_tables = ["culture"]
        plan.operations = [
            _query_op(
                name="culture",
                table="culture",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=search_all,
                structure=QueryStructure(
                    operation="retrieve",
                    table="culture",
                    meanings=_topic_meanings(text),
                    limit=8,
                    detected=True,
                ),
            )
        ]
        plan.operation = "explain_culture"
        plan.response_type = "culture"
        plan.confidence = compute_plan_confidence(text, intent, entities, plan.operations, plan.notes)
        return plan

    # ---- PRONUNCIATION / IPA / LINGUISTICS / SEMANTICS ----
    if intent in (PRONUNCIATION, IPA, LINGUISTICS, SEMANTICS):
        plan.required_tables = ["vocabulary", "grammar"]
        plan.operations = [
            _query_op(
                name="vocab",
                table="vocabulary",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=search_all,
                structure=QueryStructure(operation="retrieve", table="vocabulary", limit=15, detected=True),
            ),
            _query_op(
                name="grammar",
                table="grammar",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=True,
                structure=QueryStructure(operation="retrieve", table="grammar", limit=5, detected=True),
                required=False,
            ),
        ]
        plan.operation = "linguistics"
        plan.response_type = "linguistics"
        plan.knowledge_policy = "linguistics_with_disclaimer"
        plan.confidence = compute_plan_confidence(text, intent, entities, plan.operations, plan.notes)
        return plan

    # ---- EXAMPLES / CONVERSATION ----
    if intent in (EXAMPLE_SENTENCE, EXAMPLES, CONVERSATION):
        plan.required_tables = ["vocabulary"]
        meanings = _topic_meanings(text)
        struct = QueryStructure(
            operation="retrieve",
            table="vocabulary",
            meanings=meanings,
            limit=15,
            detected=True,
        )
        plan.operations = [
            _query_op(
                name="examples",
                table="vocabulary",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=True if intent == CONVERSATION else search_all,
                structure=struct,
            )
        ]
        plan.operation = "examples" if intent != CONVERSATION else "conversation"
        plan.response_type = "example" if intent != CONVERSATION else "conversation"
        plan.confidence = compute_plan_confidence(text, intent, entities, plan.operations, plan.notes)
        return plan

    # ---- SEARCH / VOCAB LOOKUP ----
    if intent in (SEARCH, VOCABULARY_LOOKUP, VOCABULARY):
        meanings = _topic_meanings(text)
        pos = None
        for pat, p in (
            (r"\bgreetings?\b", "greeting"),
            (r"\bverbs?\b", "verb"),
            (r"\bnouns?\b", "noun"),
        ):
            if re.search(pat, text, re.I):
                pos = p
                break
        struct = QueryStructure(
            operation="filter" if pos else "retrieve",
            table="vocabulary",
            part_of_speech=pos,
            filters=[{"field": "part_of_speech", "op": "=", "value": pos}] if pos else [],
            meanings=meanings if not pos else [],
            limit=_requested_count(text, 20),
            detected=True,
        )
        plan.required_tables = ["vocabulary"]
        plan.operations = [
            _query_op(
                name="vocab",
                table="vocabulary",
                language=effective_lang,
                lesson_id=effective_lesson,
                search_all=search_all if not meanings else True,
                structure=struct,
            )
        ]
        plan.operation = "search"
        plan.response_type = "vocabulary"
        plan.confidence = compute_plan_confidence(text, intent, entities, plan.operations, plan.notes)
        return plan

    # ---- UNKNOWN with no ops ----
    plan.require_evidence = False
    plan.allow_llm_rewrite = False
    plan.confidence = compute_plan_confidence(text, intent, entities, [], plan.notes)
    return plan
