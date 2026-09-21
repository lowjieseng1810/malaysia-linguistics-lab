"""Mah Meri quiz selection from verified dictionary rows.

Does not invent vocabulary. Pedagogical Malay/multilingual bridges are
deprioritized so practice, daily, tutor, and lesson quizzes can prefer
Mah Meri-specific attested items already stored in the project.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from review_quality import (
    _BRIDGE_MALAY,
    detect_entry_issues,
    is_course_pedagogical_bridge,
    normalize_bridge_word,
)

_SKIP_HEADWORDS = frozenset({"src", "o-h", "raachin"})
_BAD_CHAR = re.compile(r"[|<>]|\\u")
_OCR_MIXED = re.compile(r"[a-z][A-Z]|[A-Z]{2,}[a-z]+[A-Z]")


def _gloss(row: dict[str, Any]) -> str:
    return ((row.get("meaning_en") or row.get("meaning_ms") or "")).strip()


def looks_like_malay_overlap(row: dict[str, Any]) -> bool:
    if is_course_pedagogical_bridge(row):
        return True
    word = normalize_bridge_word(row.get("word") or "")
    ms = normalize_bridge_word(row.get("meaning_ms") or "")
    if word in _BRIDGE_MALAY:
        return True
    if word and ms and word == ms:
        return True
    return False


def quiz_text_is_malay_bridge(question: str, options: list[str], answer: str) -> bool:
    blob = " ".join(
        [question or "", answer or ""] + [str(o or "") for o in options]
    ).lower()
    for item in _BRIDGE_MALAY:
        if item and item in blob:
            return True
    return False


def is_usable_learner_row(row: dict[str, Any]) -> bool:
    word = (row.get("word") or "").strip()
    gloss = _gloss(row)
    if not word or not gloss:
        return False
    if normalize_bridge_word(word) in _SKIP_HEADWORDS:
        return False
    if _BAD_CHAR.search(word) or _BAD_CHAR.search(gloss):
        return False
    if _OCR_MIXED.search(word):
        return False
    if len(word) > 40 or len(gloss) > 80:
        return False
    issues = detect_entry_issues(row)
    if any((issue or {}).get("severity") == "technical" for issue in issues):
        return False
    return True


def verified_specific_vocab(limit: int = 80) -> list[dict[str, Any]]:
    from database import list_vocabulary_for_language

    specific: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in list_vocabulary_for_language("mah-meri"):
        if not is_usable_learner_row(row):
            continue
        if looks_like_malay_overlap(row):
            continue
        key = normalize_bridge_word(row.get("word") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        specific.append(row)
        if len(specific) >= limit:
            break
    return specific


def _distinct_gloss_pool(rows: list[dict[str, Any]], target: dict[str, Any]) -> list[dict[str, Any]]:
    target_gloss = _gloss(target).lower()
    target_word = normalize_bridge_word(target.get("word") or "")
    out = []
    seen_gloss: set[str] = set()
    target_pos = (target.get("part_of_speech") or "").strip().lower()
    same_pos = []
    other = []
    for row in rows:
        if normalize_bridge_word(row.get("word") or "") == target_word:
            continue
        gloss = _gloss(row).lower()
        if not gloss or gloss == target_gloss or gloss in seen_gloss:
            continue
        seen_gloss.add(gloss)
        if target_pos and (row.get("part_of_speech") or "").strip().lower() == target_pos:
            same_pos.append(row)
        else:
            other.append(row)
    out.extend(same_pos)
    out.extend(other)
    return out


def _mcq_pair(target: dict[str, Any], distractors: list[dict[str, Any]], reverse: bool) -> dict[str, Any]:
    word = (target.get("word") or "").strip()
    gloss = _gloss(target)
    if reverse:
        options = [word] + [(d.get("word") or "").strip() for d in distractors]
        question = f'Which Mah Meri word means "{gloss}"?'
        answer = word
        explanation = f'In the project dictionary, "{word}" is glossed as "{gloss}".'
    else:
        options = [gloss] + [_gloss(d) for d in distractors]
        question = f'What does the Mah Meri word "{word}" mean?'
        answer = gloss
        explanation = f'"{word}" is a documented Mah Meri form glossed as "{gloss}".'
    return {
        "question": question,
        "options": options,
        "correct_answer": answer,
        "explanation": explanation,
        "source_word": word,
        "source_lang": "mah-meri",
        "difficulty": "hard" if reverse else "medium",
    }


def build_mah_meri_mcqs(
    count: int,
    *,
    rng,
    reverse_bias: float = 0.55,
) -> list[dict[str, Any]]:
    rows = verified_specific_vocab(limit=120)
    if len(rows) < 4:
        return []
    shuffled = list(rows)
    rng.shuffle(shuffled)
    built: list[dict[str, Any]] = []
    used_words: set[str] = set()
    for target in shuffled:
        if len(built) >= count:
            break
        word_key = normalize_bridge_word(target.get("word") or "")
        if word_key in used_words:
            continue
        pool = _distinct_gloss_pool(rows, target)
        if len(pool) < 3:
            continue
        distractors = pool[:3]
        reverse = rng.random() < reverse_bias
        item = _mcq_pair(target, distractors, reverse)
        if len({o.strip().lower() for o in item["options"] if o.strip()}) < 4:
            continue
        used_words.add(word_key)
        built.append(item)
    return built


def filter_quiz_table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept = []
    for row in rows:
        options = [
            row.get("option_a") or "",
            row.get("option_b") or "",
            row.get("option_c") or "",
            row.get("option_d") or "",
        ]
        if quiz_text_is_malay_bridge(
            row.get("question") or "",
            options,
            row.get("correct_answer") or "",
        ):
            continue
        kept.append(row)
    return kept


def as_session_questions(mcqs: list[dict[str, Any]], *, rng, difficulty: Optional[str] = None) -> list[dict[str, Any]]:
    built = []
    for item in mcqs:
        options = [o for o in (item.get("options") or []) if str(o).strip()]
        if len(options) < 2:
            continue
        correct = (item.get("correct_answer") or "").strip()
        shuffled = options[:]
        rng.shuffle(shuffled)
        if correct and correct.lower() not in [o.strip().lower() for o in shuffled]:
            shuffled[0] = correct
        correct_index = 0
        for i, opt in enumerate(shuffled):
            if opt.strip().lower() == correct.lower():
                correct_index = i
                break
        built.append(
            {
                "quiz_id": None,
                "question": item["question"],
                "options": shuffled,
                "correct_index": correct_index,
                "explanation": item.get("explanation") or "",
                "difficulty": difficulty or item.get("difficulty") or "medium",
                "source_lang": "mah-meri",
            }
        )
    return built


def as_tutor_candidates(mcqs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in mcqs:
        options = [o for o in (item.get("options") or []) if str(o).strip()]
        if len(options) < 2:
            continue
        try:
            idx = options.index(item["correct_answer"])
        except ValueError:
            continue
        out.append(
            {
                "question": item["question"],
                "options": options,
                "correctIndex": idx,
                "correctFeedback": item.get("explanation") or "",
                "wrongFeedback": item.get("explanation") or "",
            }
        )
    return out


def lesson_quiz_replacements(level_num: int, needed: int) -> list[dict[str, Any]]:
    """Stable extra/replacement quiz steps for in-lesson Mah Meri quizzes."""
    import random

    rows = verified_specific_vocab(limit=80)
    if len(rows) < 4 or needed <= 0:
        return []
    rng = random.Random(f"mah-meri-lesson|{int(level_num)}")
    offset = max(0, (int(level_num) - 1) * 6)
    rotated = rows[offset:] + rows[:offset]
    mcqs = []
    used = set()
    for target in rotated:
        if len(mcqs) >= needed:
            break
        key = normalize_bridge_word(target.get("word") or "")
        if key in used:
            continue
        pool = _distinct_gloss_pool(rows, target)
        if len(pool) < 3:
            continue
        reverse = (len(mcqs) % 2) == 1
        item = _mcq_pair(target, pool[:3], reverse)
        if len({o.strip().lower() for o in item["options"] if o.strip()}) < 4:
            continue
        used.add(key)
        mcqs.append(item)
    steps = []
    for item in mcqs:
        options = list(item["options"])
        rng.shuffle(options)
        answer = item["correct_answer"]
        try:
            idx = next(i for i, o in enumerate(options) if o.strip().lower() == answer.lower())
        except StopIteration:
            continue
        steps.append(
            {
                "type": "quiz",
                "question": item["question"],
                "instruction": "Choose the documented Mah Meri form or gloss.",
                "options": options,
                "correctIndex": idx,
                "hint": "Use the Mah Meri dictionary form, not a Malay look-alike.",
                "correctFeedback": item.get("explanation") or "",
                "wrongFeedback": item.get("explanation") or "",
            }
        )
    return steps


def replace_mah_meri_lesson_quizzes(steps: list[dict[str, Any]], level_num: int) -> list[dict[str, Any]]:
    quiz_indexes = [i for i, step in enumerate(steps) if (step or {}).get("type") == "quiz"]
    if not quiz_indexes:
        return list(steps)
    replacements = lesson_quiz_replacements(level_num, len(quiz_indexes))
    if len(replacements) < len(quiz_indexes):
        return list(steps)
    out = list(steps)
    for idx, new_step in zip(quiz_indexes, replacements):
        out[idx] = new_step
    return out
