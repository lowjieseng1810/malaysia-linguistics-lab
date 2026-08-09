"""Recent-question diversity for AI Tutor GPT quizzes.

Pure helpers — no hard-coded question blacklists. Detects exact, near-duplicate,
and same-concept / same-answer repeats so each Next question adds learning value.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Optional

HISTORY_SESSION_KEY = "tutor_gpt_quiz_history"
HISTORY_LIMIT = 12
MAX_GENERATION_ATTEMPTS = 4

# Soft reject threshold for overall similarity (0–1).
SIMILARITY_REJECT = 0.72
# High wording similarity alone is enough to reject.
WORDING_REJECT = 0.82
# Same answer + moderate concept overlap rejects.
SAME_ANSWER_CONCEPT_REJECT = 0.55

_STOPWORDS = frozenset(
    """
    a an the and or of to in on for with from by as is are was were be been being
    what which who whom whose where when why how does do did can could would should
    will may might must about into over under between among this that these those
    it its their his her our your my me we they them you i not no yes than then
    also just only more most less least other another same different language
    languages word words mean means meaning called call name named
    """.split()
)

_TYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("comparison", re.compile(r"\b(compare|contrast|difference|differ|versus|vs\.?)\b", re.I)),
    ("example", re.compile(r"\b(example|for instance|illustrat)\b", re.I)),
    ("application", re.compile(r"\b(how (would|do|can|might)|apply|use|using|in practice)\b", re.I)),
    ("reasoning", re.compile(r"\b(why|because|reason|cause|result|effect)\b", re.I)),
    ("identification", re.compile(r"\b(which|identify|select|choose|pick)\b", re.I)),
    ("definition", re.compile(r"\b(what is|what are|define|definition|means?|refer to)\b", re.I)),
]


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.lower().strip()
    value = re.sub(r"[“”\"'`´]", "", value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _stem_token(tok: str) -> str:
    """Lightweight stemmer for quiz similarity (not linguistic perfection)."""
    if len(tok) <= 3:
        return tok
    for suffix in ("ing", "ers", "ies", "ied", "ed", "es", "s"):
        if tok.endswith(suffix) and len(tok) - len(suffix) >= 3:
            return tok[: -len(suffix)]
    return tok


def content_tokens(text: str) -> set[str]:
    return {
        _stem_token(tok)
        for tok in normalize_text(text).split()
        if tok and tok not in _STOPWORDS and len(tok) > 1
    }


def answers_equivalent(a: str, b: str) -> bool:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na in nb or nb in na:
        return True
    ta, tb = content_tokens(a), content_tokens(b)
    if ta and tb and (ta <= tb or tb <= ta):
        return True
    return bool(ta and tb and _jaccard(ta, tb) >= 0.5)


def infer_question_type(question: str) -> str:
    q = question or ""
    for label, pattern in _TYPE_PATTERNS:
        if pattern.search(q):
            return label
    return "identification"


def concept_fingerprint(question: str, answer: str = "") -> str:
    tokens = sorted(content_tokens(f"{question} {answer}"))
    return " ".join(tokens)


def build_history_record(
    *,
    question: str,
    correct_answer: str,
    options: Optional[list[str]] = None,
    language: Optional[str] = None,
    question_type: Optional[str] = None,
    topic: Optional[str] = None,
) -> dict[str, Any]:
    q = (question or "").strip()
    ans = (correct_answer or "").strip()
    qtype = question_type or infer_question_type(q)
    return {
        "question": q,
        "normalized_question": normalize_text(q),
        "correct_answer": ans,
        "normalized_answer": normalize_text(ans),
        "concept": concept_fingerprint(q, ans),
        "question_type": qtype,
        "language": language,
        "topic": topic,
        "options": list(options or []),
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _ratio(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def similarity_breakdown(
    candidate: dict[str, Any],
    recent: dict[str, Any],
) -> dict[str, float]:
    cq = candidate.get("normalized_question") or normalize_text(candidate.get("question") or "")
    rq = recent.get("normalized_question") or normalize_text(recent.get("question") or "")
    ca = candidate.get("correct_answer") or ""
    ra = recent.get("correct_answer") or ""
    c_tokens = content_tokens(candidate.get("question") or "")
    r_tokens = content_tokens(recent.get("question") or "")
    c_concept = set((candidate.get("concept") or concept_fingerprint(
        candidate.get("question") or "", candidate.get("correct_answer") or ""
    )).split())
    r_concept = set((recent.get("concept") or concept_fingerprint(
        recent.get("question") or "", recent.get("correct_answer") or ""
    )).split())

    # Token-sort ratio catches reordered paraphrases ("pitch change" vs "changing pitch").
    sorted_c = " ".join(sorted(cq.split()))
    sorted_r = " ".join(sorted(rq.split()))
    wording = max(
        _ratio(cq, rq),
        _ratio(sorted_c, sorted_r),
        _jaccard(c_tokens, r_tokens),
    )
    concept = _jaccard(c_concept, r_concept)
    answer_same = 1.0 if answers_equivalent(ca, ra) else 0.0
    overall = max(
        wording,
        concept,
        (0.65 * wording + 0.35 * concept) if answer_same else (0.55 * wording + 0.45 * concept),
    )
    if answer_same and concept >= SAME_ANSWER_CONCEPT_REJECT:
        overall = max(overall, 0.9)
    # Same answer + strong shared content tokens (even if wording differs).
    if answer_same and _jaccard(c_tokens, r_tokens) >= 0.45:
        overall = max(overall, 0.88)
    if cq and cq == rq:
        overall = 1.0
    return {
        "wording": wording,
        "concept": concept,
        "answer_same": answer_same,
        "overall": overall,
    }


def is_too_similar(
    candidate: dict[str, Any],
    recent_records: list[dict[str, Any]],
    *,
    threshold: float = SIMILARITY_REJECT,
) -> tuple[bool, str, float]:
    """Return (too_similar, reason, best_score)."""
    if not recent_records:
        return False, "", 0.0
    cand = candidate if "normalized_question" in candidate else build_history_record(
        question=candidate.get("question") or "",
        correct_answer=candidate.get("correct_answer")
        or (
            (candidate.get("options") or [""])[int(candidate.get("correct_index") or 0)]
            if candidate.get("options")
            else ""
        ),
        options=candidate.get("options"),
        language=candidate.get("language"),
        question_type=candidate.get("question_type"),
        topic=candidate.get("topic"),
    )
    best_score = 0.0
    best_reason = ""
    for recent in recent_records:
        parts = similarity_breakdown(cand, recent)
        score = parts["overall"]
        if score > best_score:
            best_score = score
        cq = cand.get("normalized_question") or ""
        rq = recent.get("normalized_question") or ""
        if cq and cq == rq:
            return True, "exact_normalized_match", 1.0
        if parts["wording"] >= WORDING_REJECT:
            return True, "near_duplicate_wording", parts["wording"]
        if parts["answer_same"] and (
            parts["concept"] >= SAME_ANSWER_CONCEPT_REJECT
            or parts["wording"] >= 0.55
            or score >= 0.8
        ):
            return True, "same_answer_same_concept", max(parts["concept"], score)
        if score >= threshold:
            best_reason = "semantic_similarity"
    if best_score >= threshold:
        return True, best_reason or "semantic_similarity", best_score
    return False, "", best_score


def diversity_score(
    candidate: dict[str, Any],
    recent_records: list[dict[str, Any]],
) -> float:
    """Higher is better (more different from recent history)."""
    if not recent_records:
        return 1.0
    _, _, best = is_too_similar(candidate, recent_records, threshold=1.1)
    type_bonus = 0.0
    qtype = candidate.get("question_type") or infer_question_type(candidate.get("question") or "")
    recent_types = [r.get("question_type") for r in recent_records[-4:]]
    if qtype and qtype not in recent_types:
        type_bonus = 0.08
    return max(0.0, 1.0 - best) + type_bonus


def preferred_question_types(recent_records: list[dict[str, Any]]) -> list[str]:
    recent_types = [r.get("question_type") for r in (recent_records or [])[-5:] if r.get("question_type")]
    counts: dict[str, int] = {}
    for t in recent_types:
        counts[t] = counts.get(t, 0) + 1
    all_types = ["definition", "identification", "application", "comparison", "example", "reasoning"]
    # Prefer underused types.
    return sorted(all_types, key=lambda t: (counts.get(t, 0), all_types.index(t)))


def select_best_candidate(
    candidates: list[dict[str, Any]],
    recent_records: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda c: diversity_score(c, recent_records),
        reverse=True,
    )
    for cand in ranked:
        too_sim, _, _ = is_too_similar(cand, recent_records)
        if not too_sim:
            return cand
    # Bounded fallback: least-similar candidate rather than hanging.
    return ranked[0]


def append_history(
    recent_records: list[dict[str, Any]],
    record: dict[str, Any],
    *,
    limit: int = HISTORY_LIMIT,
) -> list[dict[str, Any]]:
    out = list(recent_records or [])
    out.append(record)
    return out[-limit:]
