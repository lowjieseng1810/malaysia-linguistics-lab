"""Mah Meri quizzes derived from taught COURSE_DATA items.

Each Mah Meri level has a closed teaching set (vocabulary steps). Practice,
Quick Check, Daily (unlocked levels), and Tutor questions for Mah Meri are
built from that set — never from an unrelated global dictionary row.

Pedagogical Malay-bridge forms in COURSE_DATA are the verified lesson
content for this course; they are tested because they are taught, not
because they appear in the dictionary pack.
"""

from __future__ import annotations

import random
import re
from typing import Any, Iterable, Optional

from review_quality import (
    _BRIDGE_MALAY,
    detect_entry_issues,
    is_course_pedagogical_bridge,
    normalize_bridge_word,
)

_SKIP_HEADWORDS = frozenset({"src", "o-h", "raachin"})
_BAD_CHAR = re.compile(r"[|<>]|\\u")
_OCR_MIXED = re.compile(r"[a-z][A-Z]|[A-Z]{2,}[a-z]+[A-Z]")

# Close pairs that exist inside a single Mah Meri level. Used only for
# hints/explanations that contrast taught items — never for new glosses.
_TAUGHT_CONTRASTS = (
    (("Ya", "Tak"), "this level teaches both a short yes-form and a short no-form"),
    (("Nama?", "Nama saya ..."), "one form prompts for a name and the other begins a self-introduction"),
    (("Selamat", "Terima kasih"), "greeting and thank-you are different First Meeting formulas"),
    (("ibu", "bapa"), "mother and father are neighbouring kinship terms in this level"),
    (("anak", "orang"), "child and person/people are neighbouring people-terms in this level"),
    (("kawan", "keluarga"), "friend and family are neighbouring relationship terms in this level"),
    (("Apa?", "Siapa?"), "what? and who? are neighbouring question words in this level"),
    (("Siapa?", "Di mana?"), "who? and where? are neighbouring question words in this level"),
    (("Apa?", "Di mana?"), "what? and where? are neighbouring question words in this level"),
    (
        ("Ya, terima kasih.", "Tak, terima kasih."),
        "yes-thank-you and no-thank-you are neighbouring polite replies",
    ),
)


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
    """Dictionary-pack rows (non-bridge). Not used for lesson/practice/tutor."""
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


def _course_data():
    from app import COURSE_DATA

    return COURSE_DATA.get("mah-meri") or {}


def taught_items_from_steps(steps: Iterable[dict[str, Any]], *, level_num: int = 0) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for step in steps or []:
        if (step or {}).get("type") not in {"vocabulary", "vocab"}:
            word = (step or {}).get("word") or (step or {}).get("expression")
            meaning = (step or {}).get("meaning")
            if not (word and meaning) or (step or {}).get("type") == "quiz":
                continue
        else:
            word = (step or {}).get("word") or (step or {}).get("expression")
            meaning = (step or {}).get("meaning")
        word = (word or "").strip()
        meaning = (meaning or "").strip()
        if not word or not meaning:
            continue
        key = normalize_bridge_word(word)
        if not key or key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "word": word,
                "meaning": meaning,
                "note": ((step or {}).get("note") or (step or {}).get("context") or "").strip(),
                "title": ((step or {}).get("title") or "").strip(),
                "level_num": int(level_num or 0),
            }
        )
    return items


def taught_items_for_levels(level_nums: Iterable[int]) -> list[dict[str, Any]]:
    course = _course_data()
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in level_nums:
        try:
            level_num = int(raw)
        except (TypeError, ValueError):
            continue
        steps = (course.get(level_num) or {}).get("steps") or []
        for item in taught_items_from_steps(steps, level_num=level_num):
            key = normalize_bridge_word(item["word"])
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    return items


def taught_items_for_level(level_num: int) -> list[dict[str, Any]]:
    return taught_items_for_levels([int(level_num)])


def taught_word_set(items: Iterable[dict[str, Any]]) -> set[str]:
    return {normalize_bridge_word(item.get("word") or "") for item in items}


def _norm(text: str) -> str:
    return normalize_bridge_word(text or "")


def _same_bucket(a: dict[str, Any], b: dict[str, Any]) -> bool:
    for left, right in (pair for pair, _ in _TAUGHT_CONTRASTS):
        pair = {_norm(left), _norm(right)}
        if _norm(a.get("word") or "") in pair and _norm(b.get("word") or "") in pair:
            return True
    return False


def _contrast_note(item: dict[str, Any], siblings: list[dict[str, Any]]) -> Optional[str]:
    word = _norm(item.get("word") or "")
    sibling_words = {_norm(s.get("word") or "") for s in siblings}
    for (left, right), text in _TAUGHT_CONTRASTS:
        pair = {_norm(left), _norm(right)}
        if word in pair and pair <= (sibling_words | {word}):
            other = _norm(right) if word == _norm(left) else _norm(left)
            if other in sibling_words:
                return text
    return None


def _hint(item: dict[str, Any], siblings: list[dict[str, Any]], reverse: bool) -> str:
    title = (item.get("title") or "").strip() or f"Mah Meri Level {item.get('level_num') or ''}".strip()
    contrast = _contrast_note(item, siblings)
    if reverse:
        base = (
            f"This gloss was taught in {title}. "
            "Choose the Mah Meri form paired with it in that lesson, not a neighbouring item from the same set."
        )
    else:
        base = (
            f"“{(item.get('word') or '').strip()}” was introduced in {title}. "
            "Match the gloss taught with it there — not a nearby item from the same lesson."
        )
    if contrast:
        return f"{base} Remember: {contrast}."
    return base


def _explanation(item: dict[str, Any], siblings: list[dict[str, Any]]) -> str:
    word = (item.get("word") or "").strip()
    meaning = (item.get("meaning") or "").strip()
    title = (item.get("title") or "").strip()
    note = (item.get("note") or "").strip()
    parts = []
    if title:
        parts.append(f'In {title}, “{word}” is taught as “{meaning}”.')
    else:
        parts.append(f'“{word}” is taught as “{meaning}”.')
    if note:
        parts.append(note.rstrip(".") + ".")
    contrast = _contrast_note(item, siblings)
    if contrast:
        other = None
        word_n = _norm(word)
        for left, right in (pair for pair, _ in _TAUGHT_CONTRASTS):
            pair = {_norm(left), _norm(right)}
            if word_n in pair:
                other_form = right if word_n == _norm(left) else left
                match = next((s for s in siblings if _norm(s.get("word") or "") == _norm(other_form)), None)
                if match:
                    other = match
                    break
        if other:
            parts.append(
                f'Do not confuse it with “{other["word"]}” (“{other["meaning"]}”): {contrast}.'
            )
    return " ".join(parts)


def _distractors(target: dict[str, Any], pool: list[dict[str, Any]], rng, *, closer: bool) -> list[dict[str, Any]]:
    others = [item for item in pool if _norm(item.get("word") or "") != _norm(target.get("word") or "")]
    if closer:
        same = [item for item in others if _same_bucket(target, item)]
        rest = [item for item in others if item not in same]
        rng.shuffle(same)
        rng.shuffle(rest)
        ordered = same + rest
    else:
        ordered = list(others)
        rng.shuffle(ordered)
    picked: list[dict[str, Any]] = []
    seen_gloss: set[str] = set()
    target_gloss = (target.get("meaning") or "").strip().lower()
    for item in ordered:
        gloss = (item.get("meaning") or "").strip().lower()
        word = (item.get("word") or "").strip()
        if not gloss or not word or gloss == target_gloss or gloss in seen_gloss:
            continue
        seen_gloss.add(gloss)
        picked.append(item)
        if len(picked) >= 3:
            break
    return picked


def _mcq_from_taught(target: dict[str, Any], distractors: list[dict[str, Any]], reverse: bool) -> dict[str, Any]:
    word = (target.get("word") or "").strip()
    gloss = (target.get("meaning") or "").strip()
    siblings = distractors
    if reverse:
        options = [word] + [(d.get("word") or "").strip() for d in distractors]
        question = f'Which Mah Meri expression means "{gloss}"?'
        answer = word
    else:
        options = [gloss] + [(d.get("meaning") or "").strip() for d in distractors]
        question = f'What does the Mah Meri expression "{word}" mean?'
        answer = gloss
    return {
        "question": question,
        "options": options,
        "correct_answer": answer,
        "explanation": _explanation(target, siblings),
        "hint": _hint(target, siblings, reverse),
        "source_word": word,
        "source_meaning": gloss,
        "source_lang": "mah-meri",
        "level_num": target.get("level_num"),
        "difficulty": "hard" if reverse else "medium",
    }


def _reverse_bias_for_level(level_num: Optional[int], override: Optional[float]) -> float:
    if override is not None:
        return override
    if level_num == 1:
        return 0.25
    if level_num == 2:
        return 0.5
    if level_num == 3:
        return 0.7
    return 0.45


def build_mah_meri_mcqs(
    count: int,
    *,
    rng,
    reverse_bias: Optional[float] = None,
    level_num: Optional[int] = None,
    levels: Optional[Iterable[int]] = None,
    items: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Build MCQs from taught Mah Meri items only (same-set distractors)."""
    if items is not None:
        items = list(items)
        bias_level = int(level_num) if level_num is not None else None
        if bias_level is None:
            nums = [int(i.get("level_num") or 0) for i in items if i.get("level_num")]
            bias_level = max(nums) if nums else 2
    elif levels is not None:
        level_list = [int(n) for n in levels]
        items = taught_items_for_levels(level_list)
        bias_level = max(level_list) if level_list else None
    elif level_num is not None:
        items = taught_items_for_level(int(level_num))
        bias_level = int(level_num)
    else:
        items = taught_items_for_levels([1, 2, 3])
        bias_level = 2
    if len(items) < 4 or count <= 0:
        return []
    bias = _reverse_bias_for_level(bias_level, reverse_bias)
    closer = (bias_level or 1) >= 2
    shuffled = list(items)
    rng.shuffle(shuffled)
    built: list[dict[str, Any]] = []
    used: set[str] = set()
    cycle = list(shuffled)
    while len(built) < count and cycle:
        progressed = False
        for target in cycle:
            if len(built) >= count:
                break
            key = _norm(target.get("word") or "")
            if key in used:
                continue
            distractors = _distractors(target, items, rng, closer=closer)
            if len(distractors) < 3:
                continue
            reverse = rng.random() < bias
            item = _mcq_from_taught(target, distractors, reverse)
            if len({o.strip().lower() for o in item["options"] if o.strip()}) < 4:
                continue
            used.add(key)
            built.append(item)
            progressed = True
        if not progressed:
            break
        if len(built) < count and len(used) >= len(items):
            used.clear()
            rng.shuffle(cycle)
    return built


def filter_quiz_table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Legacy helper: drop Malay-bridge table rows. Unused for Mah Meri course quizzes."""
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
                "hint": item.get("hint") or "",
                "difficulty": difficulty or item.get("difficulty") or "medium",
                "source_lang": "mah-meri",
                "source_word": item.get("source_word") or "",
                "source_meaning": item.get("source_meaning") or "",
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
        explanation = item.get("explanation") or ""
        out.append(
            {
                "question": item["question"],
                "options": options,
                "correctIndex": idx,
                "correctFeedback": explanation,
                "wrongFeedback": explanation,
                "hint": item.get("hint") or "",
            }
        )
    return out


def quiz_steps_from_taught(items: list[dict[str, Any]], needed: int, *, level_num: int) -> list[dict[str, Any]]:
    if needed <= 0 or len(items) < 4:
        return []
    rng = random.Random(f"mah-meri-lesson|{int(level_num)}")
    mcqs = build_mah_meri_mcqs(
        needed,
        rng=rng,
        reverse_bias=_reverse_bias_for_level(int(level_num), None),
        level_num=int(level_num),
        items=items,
    )
    if len(mcqs) < needed:
        return []
    steps = []
    for item in mcqs[:needed]:
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
                "instruction": "Choose the form or meaning taught in this Mah Meri level.",
                "options": options,
                "correctIndex": idx,
                "hint": item.get("hint") or "",
                "correctFeedback": item.get("explanation") or "",
                "wrongFeedback": item.get("explanation") or "",
            }
        )
    return steps


def align_mah_meri_lesson_quizzes(steps: list[dict[str, Any]], level_num: int) -> list[dict[str, Any]]:
    """Rebuild Quick Check steps from vocabulary taught in the same step list."""
    taught = taught_items_from_steps(steps, level_num=level_num)
    if len(taught) < 4:
        taught = taught_items_for_level(level_num)
    quiz_indexes = [i for i, step in enumerate(steps) if (step or {}).get("type") == "quiz"]
    if not quiz_indexes:
        return list(steps)
    replacements = quiz_steps_from_taught(taught, len(quiz_indexes), level_num=level_num)
    if len(replacements) < len(quiz_indexes):
        return list(steps)
    out = list(steps)
    for idx, new_step in zip(quiz_indexes, replacements):
        out[idx] = new_step
    return out


def replace_mah_meri_lesson_quizzes(steps: list[dict[str, Any]], level_num: int) -> list[dict[str, Any]]:
    """Compatibility alias: lesson quizzes must test that lesson's taught items."""
    return align_mah_meri_lesson_quizzes(steps, level_num)


def taught_context_rows(level_num: Optional[int] = None, levels: Optional[Iterable[int]] = None) -> list[dict[str, Any]]:
    if levels is not None:
        items = taught_items_for_levels(levels)
    elif level_num is not None:
        items = taught_items_for_level(int(level_num))
    else:
        items = taught_items_for_levels([1, 2, 3])
    return [
        {
            "word": item["word"],
            "meaning_en": item["meaning"],
            "note": item.get("note") or "",
            "lesson_title": item.get("title") or "",
            "language": "mah-meri",
            "level_num": item.get("level_num"),
        }
        for item in items
    ]
