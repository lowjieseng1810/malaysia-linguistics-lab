"""Database-driven adaptive quiz flow, with a GPT-generated fallback.

DB-backed quiz questions remain the default when the course database has
verified rows for the requested lesson. When it does not (no active lesson,
or a free-form topic like "quiz me on Mah Meri morphology" with no matching
DB rows), GPT generates a multiple-choice question instead of refusing.
Grading stays fully deterministic in both cases — only the question source
differs, and that source is always tracked (`source: database|gpt_generated`)
so generated content is never confused with verified course facts.
"""

from __future__ import annotations

import random
from typing import Optional

from flask import session

from composer import COMPOSER_ENABLED, generate_quiz_question
from language_registry import display_name
from learning_memory import (
    preferred_quiz_difficulty,
    record_quiz_result,
    record_quiz_session,
    weak_area_message,
)
from retrieval import get_quiz_questions
from tutor_quiz_diversity import (
    HISTORY_SESSION_KEY,
    MAX_GENERATION_ATTEMPTS,
    append_history,
    build_history_record,
    is_too_similar,
    preferred_question_types,
    select_best_candidate,
)


def _score_key(lang_key: str, level_num) -> str:
    return f"{lang_key}|{level_num}"


def _difficulty_rank(value: Optional[str]) -> int:
    return {"easy": 0, "medium": 1, "hard": 2}.get((value or "").lower(), 1)


def _course_context_rows(lang_key: Optional[str]) -> list[dict]:
    """A few vocabulary rows to ground a GPT-generated question, if any exist."""
    if not lang_key:
        return []
    if lang_key == "mah-meri":
        try:
            from mah_meri_quiz import verified_specific_vocab

            return verified_specific_vocab(limit=18)
        except Exception:
            pass
    try:
        from retrieval import dictionary_search

        result = dictionary_search(language=lang_key, limit=8)
        return result.get("rows") or []
    except Exception:
        return []


def _gpt_quiz_history() -> list:
    raw = session.get(HISTORY_SESSION_KEY) or []
    return list(raw) if isinstance(raw, list) else []


def reset_gpt_quiz_history() -> None:
    session.pop(HISTORY_SESSION_KEY, None)


def _start_gpt_quiz(
    *,
    lang_key: Optional[str],
    level_num: Optional[int],
    user_id: Optional[int],
    target_diff: Optional[str],
    topic_text: Optional[str],
    history: Optional[list] = None,
    quiz_continue: bool = False,
) -> str:
    """GPT-generated practice question when the course DB has nothing usable."""
    if not COMPOSER_ENABLED:
        if lang_key and level_num is not None:
            return (
                "This lesson does not yet have verified quiz questions in the "
                "database, and the GPT composer is disabled on this server, so "
                "I can't generate a practice question right now."
            )
        return (
            "Open a lesson first, then press Quiz — or tell me a language/topic "
            "(e.g. \"quiz me on Mah Meri greetings\") once the GPT composer is "
            "enabled so I can generate a practice question."
        )

    # Fresh Quiz action starts a new series; Next continues with diversity memory.
    if not quiz_continue:
        reset_gpt_quiz_history()

    topic = (topic_text or "").strip() or (
        f"{display_name(lang_key)} vocabulary" if lang_key else "general language learning"
    )
    lang_display = display_name(lang_key) if lang_key else None
    context_rows = _course_context_rows(lang_key)
    recent = _gpt_quiz_history()
    preferred_types = preferred_question_types(recent)

    candidates: list[dict] = []
    generated = None
    for attempt in range(MAX_GENERATION_ATTEMPTS):
        candidate = generate_quiz_question(
            topic=topic,
            language_display=lang_display,
            difficulty=target_diff,
            course_context=context_rows,
            history=history,
            avoid_recent=recent,
            preferred_question_types=preferred_types,
            attempt=attempt,
        )
        if not candidate.get("ok"):
            continue
        options = candidate["options"]
        correct_index = candidate["correct_index"]
        record = build_history_record(
            question=candidate["question"],
            correct_answer=options[correct_index],
            options=options,
            language=lang_key,
            topic=topic,
        )
        candidate["_history_record"] = record
        candidates.append(candidate)
        too_similar, _, _ = is_too_similar(record, recent)
        if not too_similar:
            generated = candidate
            break

    if generated is None:
        generated = select_best_candidate(candidates, recent)

    if not generated or not generated.get("ok"):
        if lang_key and level_num is not None:
            return "This lesson does not yet have verified quiz questions in the database."
        fail_reason = "unknown"
        if candidates:
            fail_reason = candidates[-1].get("reason") or fail_reason
        return (
            "I couldn't generate a practice question right now "
            f"(reason: {fail_reason}). "
            "Open a lesson and press Quiz for verified lesson questions instead."
        )

    options = generated["options"]
    correct_index = generated["correct_index"]
    # Freeze the selected answer for deterministic grading — never rewrite later.
    correct_answer = options[correct_index]
    key = _score_key(lang_key, level_num)
    history_record = generated.get("_history_record") or build_history_record(
        question=generated["question"],
        correct_answer=correct_answer,
        options=options,
        language=lang_key,
        topic=topic,
    )
    session[HISTORY_SESSION_KEY] = append_history(recent, history_record)

    session["tutor_quiz_state"] = {
        "lang_key": lang_key,
        "level_num": level_num,
        "question": generated["question"],
        "options": options,
        "correct_index": correct_index,
        "correct_answer": correct_answer,
        "explanation": generated.get("explanation") or "",
        "quiz_id": None,
        "difficulty": target_diff or "medium",
        "item_key": generated["question"][:120],
        "source": "gpt_generated",
        "question_type": history_record.get("question_type"),
        "concept": history_record.get("concept"),
    }

    scores = session.get("tutor_quiz_scores") or {}
    score = scores.get(key) or {"correct": 0, "total": 0}
    score_line = f"\n\n🏆 Score so far: {score['correct']}/{score['total']}" if score.get("total") else ""

    coaching = weak_area_message(user_id, lang_key, level_num) if lang_key and level_num is not None else ""
    diff_label = (target_diff or "medium").title()

    lines = [
        f"🧩 Quiz time — GPT-generated practice question (topic: {topic}, {diff_label})",
        "_This question is generated by GPT, not pulled from the verified course database._",
        "",
    ]
    if coaching:
        lines.extend([coaching, ""])
    lines.append(generated["question"])
    lines.append("")
    for i, opt in enumerate(options, start=1):
        lines.append(f"{i}. {opt}")
    if score_line:
        lines.append(score_line)
    lines.append('Reply with the option number (e.g. "1") or the full answer text.')
    return "\n".join(line for line in lines if line is not None)


def _start_mah_meri_verified_tutor(
    *,
    level_num: Optional[int],
    user_id: Optional[int],
    target_diff: Optional[str],
) -> Optional[str]:
    from mah_meri_quiz import as_session_questions, build_mah_meri_mcqs

    rng = random.Random()
    reverse_bias = 0.7 if (target_diff or "").lower() == "hard" else 0.55
    mcqs = build_mah_meri_mcqs(6, rng=rng, reverse_bias=reverse_bias)
    built = as_session_questions(mcqs, rng=rng, difficulty=target_diff or "hard")
    if not built:
        return None
    recent = session.get("tutor_quiz_recent") or {}
    key = _score_key("mah-meri", level_num)
    recent_questions = list(recent.get(key) or [])
    pool = [q for q in built if q.get("question") not in recent_questions] or built
    chosen = random.choice(pool)
    session["tutor_quiz_state"] = {
        "lang_key": "mah-meri",
        "level_num": level_num,
        "question": chosen["question"],
        "options": chosen["options"],
        "correct_index": chosen["correct_index"],
        "correct_answer": chosen["options"][chosen["correct_index"]],
        "explanation": chosen.get("explanation") or "",
        "quiz_id": None,
        "difficulty": chosen.get("difficulty") or target_diff or "hard",
        "item_key": (chosen.get("question") or "")[:120],
        "source": "database",
    }
    recent_questions.append(chosen.get("question"))
    recent[key] = recent_questions[-12:]
    session["tutor_quiz_recent"] = recent
    scores = session.get("tutor_quiz_scores") or {}
    score = scores.get(key) or {"correct": 0, "total": 0}
    score_line = f"\n\n🏆 Score so far: {score['correct']}/{score['total']}" if score.get("total") else ""
    coaching = (
        weak_area_message(user_id, "mah-meri", int(level_num))
        if level_num is not None
        else ""
    )
    lines = [
        "🧩 Quiz time — verified Mah Meri dictionary item",
        "_This question uses documented Mah Meri vocabulary from the project database._",
        "",
    ]
    if coaching:
        lines.extend([coaching, ""])
    lines.append(chosen["question"])
    lines.append("")
    for i, opt in enumerate(chosen["options"], start=1):
        lines.append(f"{i}. {opt}")
    if score_line:
        lines.append(score_line)
    lines.append('Reply with the option number (e.g. "1") or the full answer text.')
    return "\n".join(line for line in lines if line is not None)


def start_quiz(
    lang_key: Optional[str],
    level_num: Optional[int],
    user_id: Optional[int] = None,
    forced_difficulty: Optional[str] = None,
    topic_text: Optional[str] = None,
    history: Optional[list] = None,
    prefer_gpt: bool = False,
    quiz_continue: bool = False,
) -> str:
    # AI Tutor Quiz action prefers GPT-generated MCQ; standalone Practice Quiz
    # page never calls this path. Mah Meri uses verified dictionary items first
    # so the tutor cannot drift into Malay look-alikes.
    if lang_key == "mah-meri":
        mah_reply = _start_mah_meri_verified_tutor(
            level_num=level_num,
            user_id=user_id,
            target_diff=forced_difficulty,
        )
        if mah_reply:
            return mah_reply
    if prefer_gpt or not lang_key or level_num is None:
        return _start_gpt_quiz(
            lang_key=lang_key,
            level_num=level_num,
            user_id=user_id,
            target_diff=forced_difficulty,
            topic_text=topic_text,
            history=history,
            quiz_continue=quiz_continue,
        )

    target_diff = forced_difficulty or preferred_quiz_difficulty(
        user_id, lang_key, int(level_num)
    )
    questions = get_quiz_questions(lang_key, int(level_num), difficulty=target_diff)
    if not questions:
        questions = get_quiz_questions(lang_key, int(level_num))
    if lang_key == "mah-meri":
        from mah_meri_quiz import filter_quiz_table_rows

        filtered = filter_quiz_table_rows(questions)
        if filtered:
            questions = filtered
    if not questions:
        return _start_gpt_quiz(
            lang_key=lang_key,
            level_num=level_num,
            user_id=user_id,
            target_diff=target_diff,
            topic_text=topic_text,
            history=history,
            quiz_continue=quiz_continue,
        )

    # Prefer questions near adaptive difficulty even if column is sparse
    if target_diff:
        ranked = sorted(
            questions,
            key=lambda q: abs(_difficulty_rank(q.get("difficulty")) - _difficulty_rank(target_diff)),
        )
        pool_pref = ranked[: max(3, len(ranked) // 2)]
    else:
        pool_pref = questions

    recent = session.get("tutor_quiz_recent") or {}
    key = _score_key(lang_key, int(level_num))
    recent_questions = list(recent.get(key) or [])

    pool = [q for q in pool_pref if q.get("question") not in recent_questions]
    if not pool:
        pool = [q for q in questions if q.get("question") not in recent_questions] or list(questions)
        if pool == questions:
            recent_questions = []

    chosen = random.choice(pool)
    options = [
        chosen.get("option_a") or "",
        chosen.get("option_b") or "",
        chosen.get("option_c") or "",
        chosen.get("option_d") or "",
    ]
    options = [opt for opt in options if str(opt).strip()]
    if not options:
        return "A quiz question was found, but it has no answer options yet."

    correct = (chosen.get("correct_answer") or "").strip()
    shuffled = options[:]
    random.shuffle(shuffled)
    if correct and correct not in shuffled:
        shuffled[0] = correct

    correct_index = 0
    for i, opt in enumerate(shuffled):
        if opt.strip().lower() == correct.lower():
            correct_index = i
            break

    session["tutor_quiz_state"] = {
        "lang_key": lang_key,
        "level_num": int(level_num),
        "question": chosen.get("question"),
        "options": shuffled,
        "correct_index": correct_index,
        "correct_answer": correct,
        "explanation": chosen.get("explanation") or "",
        "quiz_id": chosen.get("id"),
        "difficulty": chosen.get("difficulty") or target_diff or "medium",
        "item_key": (chosen.get("question") or "")[:120],
        "source": "database",
    }

    recent_questions.append(chosen.get("question"))
    recent[key] = recent_questions[-12:]
    session["tutor_quiz_recent"] = recent

    scores = session.get("tutor_quiz_scores") or {}
    score = scores.get(key) or {"correct": 0, "total": 0}
    score_line = ""
    if score.get("total"):
        score_line = f"\n\n🏆 Score so far: {score['correct']}/{score['total']}"

    coaching = weak_area_message(user_id, lang_key, int(level_num))
    diff_label = (chosen.get("difficulty") or target_diff or "mixed").title()

    lines = [
        f"🧩 Quiz time — from the lesson database ({diff_label})",
        "",
    ]
    if coaching:
        lines.extend([coaching, ""])
    lines.append(chosen.get("question") or "Choose the correct answer.")
    lines.append("")
    for i, opt in enumerate(shuffled, start=1):
        lines.append(f"{i}. {opt}")
    if score_line:
        lines.append(score_line)
    lines.append('Reply with the option number (e.g. "1") or the full answer text.')
    return "\n".join(line for line in lines if line is not None)


def grade_quiz_answer(
    user_message: str,
    user_id: Optional[int] = None,
) -> str:
    state = session.get("tutor_quiz_state")
    if not state:
        return "There is no active quiz question. Press Quiz to start one."

    raw = (user_message or "").strip()
    options = state.get("options") or []
    correct_index = int(state.get("correct_index") or 0)
    correct_answer = (state.get("correct_answer") or "").strip()
    if not correct_answer and 0 <= correct_index < len(options):
        correct_answer = options[correct_index]

    selected = None
    letter_map = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5}
    low = raw.lower()
    if low in letter_map and letter_map[low] < len(options):
        selected = options[letter_map[low]]
    elif raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            selected = options[idx]
    if selected is None:
        for opt in options:
            if opt.strip().lower() == low:
                selected = opt
                break

    is_correct = bool(
        selected and selected.strip().lower() == correct_answer.strip().lower()
    )

    lang_key = state.get("lang_key")
    level_num = state.get("level_num")
    key = _score_key(lang_key, level_num)
    scores = session.get("tutor_quiz_scores") or {}
    score = scores.get(key) or {"correct": 0, "total": 0}
    score["total"] = int(score.get("total") or 0) + 1
    if is_correct:
        score["correct"] = int(score.get("correct") or 0) + 1
    scores[key] = score
    session["tutor_quiz_scores"] = scores

    progress = None
    if user_id and lang_key and level_num is not None:
        progress = record_quiz_result(
            int(user_id),
            lang_key,
            int(level_num),
            state.get("item_key") or state.get("question") or "quiz",
            is_correct,
            item_type="quiz",
        )

    session.pop("tutor_quiz_state", None)

    explanation = (state.get("explanation") or "").strip()
    if is_correct:
        reply = "✅ Correct! " + random.choice(
            ["Nice work!", "Exactly right.", "Well done!", "You got it."]
        )
        if progress and progress.get("streak", 0) >= 3:
            reply += f" Streak: {progress['streak']}!"
        reply += "\n\nNext quiz will lean a little harder."
    else:
        reply = f"❌ Not quite.\n\nThe correct answer was: {correct_answer}."
        reply += "\n\nNext quiz will ease up a bit so you can rebuild confidence."

    if explanation:
        reply += f"\n\n{explanation}"

    if progress:
        reply += (
            f"\n\n📊 Mastery on this item: {int(float(progress['mastery']) * 100)}% "
            f"(✓{progress['correct']} / ✗{progress['wrong']})"
        )

    reply += f"\n\n🏆 Score: {score['correct']}/{score['total']}"
    reply += "\n\nWant another question? Press Quiz again."
    return reply


def has_active_quiz() -> bool:
    return bool(session.get("tutor_quiz_state"))


def active_quiz_card() -> Optional[dict[str, Any]]:
    """Public quiz card for the Tutor UI (never includes the correct index)."""
    state = session.get("tutor_quiz_state") or {}
    options = list(state.get("options") or [])
    if not state.get("question") or len(options) < 2:
        return None
    labels = ["A", "B", "C", "D", "E", "F"]
    return {
        "question": state.get("question"),
        "options": [
            {"key": labels[i] if i < len(labels) else str(i + 1), "text": opt}
            for i, opt in enumerate(options)
        ],
        "source": state.get("source") or "tutor",
        "difficulty": state.get("difficulty") or "medium",
    }


def grade_quiz_answer_structured(
    user_message: str,
    user_id: Optional[int] = None,
) -> dict[str, Any]:
    """Grade an active tutor quiz and return structured feedback for the UI."""
    state = session.get("tutor_quiz_state")
    if not state:
        return {
            "ok": False,
            "reply": "There is no active quiz question. Press Quiz to start one.",
            "quiz_result": None,
        }

    raw = (user_message or "").strip()
    options = list(state.get("options") or [])
    correct_index = int(state.get("correct_index") or 0)
    correct_answer = (state.get("correct_answer") or "").strip()
    if not correct_answer and 0 <= correct_index < len(options):
        correct_answer = options[correct_index]

    selected = None
    selected_index = None
    # Accept "A"/"B", "1"/"2", or full option text
    letter_map = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5}
    low = raw.lower()
    if low in letter_map and letter_map[low] < len(options):
        selected_index = letter_map[low]
        selected = options[selected_index]
    elif raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            selected_index = idx
            selected = options[idx]
    if selected is None:
        for i, opt in enumerate(options):
            if opt.strip().lower() == low:
                selected_index = i
                selected = opt
                break

    # Reuse textual grader for progress/scoring side effects
    reply = grade_quiz_answer(user_message, user_id=user_id)
    is_correct = bool(
        selected and selected.strip().lower() == correct_answer.strip().lower()
    )
    labels = ["A", "B", "C", "D", "E", "F"]
    result = {
        "correct": is_correct,
        "selected_key": labels[selected_index]
        if selected_index is not None and selected_index < len(labels)
        else None,
        "selected_text": selected,
        "correct_key": labels[correct_index]
        if 0 <= correct_index < len(labels)
        else None,
        "correct_answer": correct_answer,
        "explanation": (state.get("explanation") or "").strip(),
        "question": state.get("question"),
    }
    return {"ok": True, "reply": reply, "quiz_result": result}


# =====================================================================
# Standalone, non-chat, non-AI "Quiz" page session.
#
# This is entirely separate from the tutor-chat quiz loop above (different
# session key, different reply shape: JSON, not chat markdown). It never
# calls composer.py / GPT — if the course database has no verified
# questions for the requested language/level/difficulty it reports an
# empty pool instead of generating anything, so it works identically with
# or without an OpenAI API key configured.
# =====================================================================

_QUIZ_SESSION_KEY = "quiz_page_state"


def _build_session_questions(
    lang_key: str,
    level_num: int,
    count: int,
    difficulty: Optional[str],
    *,
    rng=None,
) -> list[dict]:
    rng = rng or random
    if lang_key == "mah-meri":
        from mah_meri_quiz import (
            as_session_questions,
            build_mah_meri_mcqs,
            filter_quiz_table_rows,
        )

        reverse_bias = 0.7 if (difficulty or "").lower() == "hard" else 0.5
        mcqs = build_mah_meri_mcqs(count, rng=rng, reverse_bias=reverse_bias)
        built = as_session_questions(mcqs, rng=rng, difficulty=difficulty)
        if len(built) >= count:
            return built[:count]
        table_rows = filter_quiz_table_rows(
            get_quiz_questions(lang_key, int(level_num), limit=200)
        )
        extra = _session_questions_from_table(table_rows, count - len(built), difficulty, rng)
        return (built + extra)[:count]

    pool = get_quiz_questions(lang_key, int(level_num), limit=200, difficulty=difficulty) if difficulty else []
    if not pool:
        pool = get_quiz_questions(lang_key, int(level_num), limit=200)
    if len(pool) < count:
        extra = get_quiz_questions(lang_key, int(level_num), limit=200, search_all=True)
        seen = {q.get("id") for q in pool}
        for row in extra:
            if row.get("id") in seen:
                continue
            pool.append(row)
            seen.add(row.get("id"))
    if not pool:
        return []
    return _session_questions_from_table(pool, count, difficulty, rng)


def _session_questions_from_table(
    pool: list[dict],
    count: int,
    difficulty: Optional[str],
    rng,
) -> list[dict]:
    if not pool or count <= 0:
        return []
    shuffled_pool = list(pool)
    rng.shuffle(shuffled_pool)
    chosen = shuffled_pool[:count]

    built: list[dict] = []
    for q in chosen:
        options = [
            (q.get("option_a") or ""),
            (q.get("option_b") or ""),
            (q.get("option_c") or ""),
            (q.get("option_d") or ""),
        ]
        options = [opt for opt in options if str(opt).strip()]
        if not options:
            continue

        correct = (q.get("correct_answer") or "").strip()
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
                "quiz_id": q.get("id"),
                "question": q.get("question") or "Choose the correct answer.",
                "options": shuffled,
                "correct_index": correct_index,
                "explanation": q.get("explanation") or "",
                "hint": (q.get("hint") or "").strip(),
                "difficulty": q.get("difficulty") or difficulty or "medium",
                "source_lang": q.get("language") or q.get("source_lang"),
            }
        )
    return built


def _public_session_view(state: dict) -> dict:
    idx = int(state.get("index") or 0)
    questions = state.get("questions") or []
    total = len(questions)
    finished = idx >= total
    current = None
    if not finished:
        q = questions[idx]
        current = {
            "question": q["question"],
            "options": q["options"],
            "difficulty": q.get("difficulty"),
            "quiz_id": q.get("quiz_id"),
            "source_lang": q.get("source_lang") or state.get("lang_key"),
            "hint": q.get("hint") or "",
        }
    return {
        "lang_key": state.get("lang_key"),
        "mode": state.get("mode") or "practice",
        "level_num": state.get("level_num"),
        "difficulty": state.get("difficulty"),
        "index": idx,
        "total": total,
        "finished": finished,
        "current_question": current,
        "score": state.get("score") or {"correct": 0, "total": 0},
    }


def start_quiz_session(
    *,
    lang_key: str,
    level_num: int,
    user_id: Optional[int] = None,
    count: int = 5,
    difficulty: Optional[str] = None,
) -> dict:
    """Start a fresh N-question quiz session for the standalone Quiz page."""
    count = max(1, min(20, int(count or 5)))
    target_diff = difficulty or preferred_quiz_difficulty(user_id, lang_key, int(level_num))

    questions = _build_session_questions(lang_key, int(level_num), count, target_diff)
    if not questions:
        return {"ok": False, "reason": "no_questions"}

    weak = weak_area_message(user_id, lang_key, int(level_num))

    state = {
        "lang_key": lang_key,
        "level_num": int(level_num),
        "difficulty": target_diff,
        "mode": "practice",
        "questions": questions,
        "index": 0,
        "answers": [],
        "score": {"correct": 0, "total": 0},
    }
    session[_QUIZ_SESSION_KEY] = state
    result = {"ok": True, "coaching_note": weak}
    result.update(_public_session_view(state))
    return result


def quiz_session_state() -> dict:
    state = session.get(_QUIZ_SESSION_KEY)
    if not state:
        return {"ok": False, "reason": "no_session"}
    result = {"ok": True}
    result.update(_public_session_view(state))
    return result


def submit_quiz_session_answer(answer_index: Optional[int], user_id: Optional[int] = None) -> dict:
    state = session.get(_QUIZ_SESSION_KEY)
    if not state:
        return {"ok": False, "reason": "no_session"}

    idx = int(state.get("index") or 0)
    questions = state.get("questions") or []
    if idx >= len(questions):
        return {"ok": False, "reason": "already_finished"}

    q = questions[idx]
    is_correct = isinstance(answer_index, int) and answer_index == q["correct_index"]

    score = state.get("score") or {"correct": 0, "total": 0}
    score["total"] = int(score.get("total") or 0) + 1
    if is_correct:
        score["correct"] = int(score.get("correct") or 0) + 1
    state["score"] = score

    progress = None
    if user_id and state.get("lang_key") and state.get("level_num") is not None:
        progress = record_quiz_result(
            int(user_id),
            state["lang_key"],
            int(state["level_num"]),
            (q.get("question") or "quiz")[:120],
            is_correct,
            item_type="quiz",
        )

    state.setdefault("answers", []).append({"quiz_id": q.get("quiz_id"), "correct": is_correct})
    state["index"] = idx + 1
    session[_QUIZ_SESSION_KEY] = state

    # Persist a finished session once, so profile history stays accurate.
    if state["index"] >= len(questions) and user_id and not state.get("history_recorded"):
        record_quiz_session(
            int(user_id),
            state["lang_key"],
            int(state["level_num"]),
            int(score.get("correct") or 0),
            int(score.get("total") or 0),
            difficulty=state.get("difficulty"),
        )
        state["history_recorded"] = True
        session[_QUIZ_SESSION_KEY] = state

    result = {
        "ok": True,
        "correct": is_correct,
        "correct_index": q["correct_index"],
        "correct_answer": q["options"][q["correct_index"]],
        "explanation": q.get("explanation") or "",
        "progress": progress,
    }
    result.update(_public_session_view(state))
    return result


def quiz_session_results() -> dict:
    state = session.get(_QUIZ_SESSION_KEY)
    if not state:
        return {"ok": False, "reason": "no_session"}

    score = state.get("score") or {"correct": 0, "total": 0}
    total = int(score.get("total") or 0)
    correct = int(score.get("correct") or 0)
    percentage = round(100 * correct / total) if total else 0

    return {
        "ok": True,
        "lang_key": state.get("lang_key"),
        "level_num": state.get("level_num"),
        "difficulty": state.get("difficulty"),
        "score": score,
        "percentage": percentage,
        "questions_total": len(state.get("questions") or []),
        "answered": total,
        "history_recorded": bool(state.get("history_recorded")),
    }


def restart_quiz_session(user_id: Optional[int] = None) -> dict:
    state = session.get(_QUIZ_SESSION_KEY)
    if not state:
        return {"ok": False, "reason": "no_session"}
    return start_quiz_session(
        lang_key=state["lang_key"],
        level_num=state["level_num"],
        user_id=user_id,
        count=len(state.get("questions") or []) or 5,
        difficulty=state.get("difficulty"),
    )


def clear_quiz_session() -> None:
    session.pop(_QUIZ_SESSION_KEY, None)


def _daily_seed(user_id: Optional[int], day_key: str, lang_key: str = "") -> str:
    return f"daily|{day_key}|{user_id or 0}|{lang_key or '*'}"


def daily_quiz_status(user_id: int) -> dict:
    """Return today's completion state from existing quiz_session_history."""
    from datetime import datetime, timezone
    from learning_memory import get_quiz_history

    day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history = get_quiz_history(int(user_id), limit=40)
    today_rows = []
    for row in history:
        created = int(row.get("created_at") or 0)
        if not created:
            continue
        day = datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%d")
        if day == day_key and (row.get("difficulty") or "") == "daily":
            today_rows.append(row)

    completed = bool(today_rows)
    latest = today_rows[0] if today_rows else None
    return {
        "ok": True,
        "day_key": day_key,
        "completed": completed,
        "score": (
            {
                "correct": latest.get("correct"),
                "total": latest.get("total"),
                "percentage": latest.get("percentage"),
            }
            if latest
            else None
        ),
        "lang_key": latest.get("lang_key") if latest else None,
        "question_count": 5,
        "estimated_minutes": 2,
    }


def start_daily_quiz_session(
    *,
    user_id: int,
    unlocked_levels: dict[str, list[int]],
    count: int = 5,
    lang_key: Optional[str] = None,
) -> dict:
    """
    Date-seeded daily quiz using verified rows for one selected language.
    Reuses the standalone quiz session machinery (no new tables).
    """
    from datetime import datetime, timezone
    import hashlib

    day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    status = daily_quiz_status(user_id)

    requested = (lang_key or "").strip()
    lang_keys = [k for k, levels in (unlocked_levels or {}).items() if levels]
    if requested:
        if requested not in lang_keys:
            return {"ok": False, "reason": "language_locked"}
        lang_keys = [requested]
    if not lang_keys:
        return {"ok": False, "reason": "no_unlocked_levels"}
    if len(lang_keys) != 1:
        return {"ok": False, "reason": "language_required"}

    chosen_lang = lang_keys[0]
    seed = _daily_seed(user_id, day_key, chosen_lang)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:16], 16))

    count = max(1, min(10, int(count or 5)))
    levels = unlocked_levels.get(chosen_lang) or []
    if not levels:
        return {"ok": False, "reason": "no_unlocked_levels"}

    if chosen_lang == "mah-meri":
        built = _build_session_questions(chosen_lang, int(levels[0]), count, "hard", rng=rng)
        primary_level = int(levels[0])
    else:
        pool: list[tuple[str, int, dict]] = []
        for level_num in levels:
            rows = get_quiz_questions(chosen_lang, int(level_num), limit=200)
            for q in rows:
                pool.append((chosen_lang, int(level_num), q))
        if not pool:
            return {"ok": False, "reason": "no_questions"}
        rng.shuffle(pool)
        seen_ids: set = set()
        chosen: list[tuple[str, int, dict]] = []
        for item in pool:
            qid = item[2].get("id")
            if qid in seen_ids:
                continue
            seen_ids.add(qid)
            chosen.append(item)
            if len(chosen) >= count:
                break
        if not chosen:
            return {"ok": False, "reason": "no_questions"}
        built = []
        primary_level = chosen[0][1]
        table_rows = [item[2] for item in chosen]
        for q in table_rows:
            q = dict(q)
            q["source_lang"] = chosen_lang
        built = _session_questions_from_table(table_rows, count, "daily", rng)
        for item in built:
            item["difficulty"] = "daily"
            item["source_lang"] = chosen_lang

    if not built:
        return {"ok": False, "reason": "no_questions"}
    for item in built:
        item["difficulty"] = "daily"
        item["source_lang"] = chosen_lang

    weak = weak_area_message(user_id, chosen_lang, int(primary_level))
    state = {
        "lang_key": chosen_lang,
        "level_num": int(primary_level),
        "difficulty": "daily",
        "mode": "daily",
        "day_key": day_key,
        "questions": built,
        "index": 0,
        "answers": [],
        "score": {"correct": 0, "total": 0},
    }
    session[_QUIZ_SESSION_KEY] = state
    result = {
        "ok": True,
        "mode": "daily",
        "day_key": day_key,
        "already_completed_today": bool(status.get("completed")),
        "coaching_note": weak,
    }
    result.update(_public_session_view(state))
    return result

