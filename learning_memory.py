"""Learning memory: user_progress tracking for the AI Tutor."""

from __future__ import annotations

from typing import Any, Optional

from database import get_db


def init_user_progress_table(conn=None) -> None:
    own = conn is None
    if own:
        conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            language TEXT NOT NULL,
            lesson_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            item_key TEXT NOT NULL,
            correct INTEGER NOT NULL DEFAULT 0,
            wrong INTEGER NOT NULL DEFAULT 0,
            mastery REAL NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0,
            last_result TEXT,
            updated_at REAL NOT NULL DEFAULT (strftime('%s','now')),
            UNIQUE(user_id, language, lesson_id, item_type, item_key)
        );

        CREATE INDEX IF NOT EXISTS idx_user_progress_user
            ON user_progress (user_id, language, lesson_id);
        """
    )
    conn.commit()
    if own:
        conn.close()


def record_quiz_result(
    user_id: int,
    language: str,
    lesson_id: int,
    item_key: str,
    is_correct: bool,
    item_type: str = "quiz",
) -> dict[str, Any]:
    init_user_progress_table()
    conn = get_db()
    row = conn.execute(
        """
        SELECT * FROM user_progress
        WHERE user_id = ? AND language = ? AND lesson_id = ?
          AND item_type = ? AND item_key = ?
        """,
        (user_id, language, lesson_id, item_type, item_key),
    ).fetchone()

    if row:
        correct = int(row["correct"]) + (1 if is_correct else 0)
        wrong = int(row["wrong"]) + (0 if is_correct else 1)
        streak = int(row["streak"]) + 1 if is_correct else 0
    else:
        correct = 1 if is_correct else 0
        wrong = 0 if is_correct else 1
        streak = 1 if is_correct else 0

    total = max(1, correct + wrong)
    mastery = round(correct / total, 3)
    conn.execute(
        """
        INSERT INTO user_progress (
            user_id, language, lesson_id, item_type, item_key,
            correct, wrong, mastery, streak, last_result, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s','now'))
        ON CONFLICT(user_id, language, lesson_id, item_type, item_key)
        DO UPDATE SET
            correct = excluded.correct,
            wrong = excluded.wrong,
            mastery = excluded.mastery,
            streak = excluded.streak,
            last_result = excluded.last_result,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            language,
            lesson_id,
            item_type,
            item_key,
            correct,
            wrong,
            mastery,
            streak,
            "correct" if is_correct else "wrong",
        ),
    )
    conn.commit()
    conn.close()
    return {
        "correct": correct,
        "wrong": wrong,
        "mastery": mastery,
        "streak": streak,
    }


def get_lesson_stats(
    user_id: int,
    language: str,
    lesson_id: int,
) -> dict[str, Any]:
    init_user_progress_table()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT * FROM user_progress
        WHERE user_id = ? AND language = ? AND lesson_id = ?
        """,
        (user_id, language, lesson_id),
    ).fetchall()
    conn.close()
    items = [dict(r) for r in rows]
    total_correct = sum(int(r["correct"]) for r in items)
    total_wrong = sum(int(r["wrong"]) for r in items)
    weak = sorted(
        [r for r in items if int(r["wrong"]) >= 2 or float(r["mastery"]) < 0.5],
        key=lambda r: (-int(r["wrong"]), float(r["mastery"])),
    )
    streak = 0
    if items:
        streak = max(int(r["streak"]) for r in items)
    return {
        "correct": total_correct,
        "wrong": total_wrong,
        "mastery": round(total_correct / max(1, total_correct + total_wrong), 3),
        "streak": streak,
        "weak_items": weak[:5],
        "item_count": len(items),
    }


def weak_area_message(
    user_id: Optional[int],
    language: Optional[str],
    lesson_id: Optional[int],
) -> str:
    if not user_id or not language or lesson_id is None:
        return ""
    stats = get_lesson_stats(int(user_id), language, int(lesson_id))
    weak = stats.get("weak_items") or []
    if not weak:
        return ""
    top = weak[0]
    key = top.get("item_key") or "this topic"
    wrong = top.get("wrong") or 0
    return (
        f"I noticed you've answered **{key}** incorrectly several times "
        f"({wrong} mistakes). Let's review that."
    )


def preferred_quiz_difficulty(
    user_id: Optional[int],
    language: Optional[str],
    lesson_id: Optional[int],
) -> Optional[str]:
    """
    Adaptive difficulty:
      strong recent performance → hard
      struggling → easy
    """
    if not user_id or not language or lesson_id is None:
        return None
    stats = get_lesson_stats(int(user_id), language, int(lesson_id))
    total = int(stats["correct"]) + int(stats["wrong"])
    if total < 2:
        return None
    mastery = float(stats["mastery"])
    if mastery >= 0.75:
        return "hard"
    if mastery <= 0.4:
        return "easy"
    return "medium"


def get_user_mastery_summary(user_id: int) -> dict[str, Any]:
    """Aggregate quiz mastery across all languages for the profile page.

    Intentionally separate from course/level completion (`progress` table).
    """
    init_user_progress_table()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT language, correct, wrong, mastery, streak, item_key
        FROM user_progress
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    items = [dict(r) for r in rows]
    total_correct = sum(int(r["correct"]) for r in items)
    total_wrong = sum(int(r["wrong"]) for r in items)
    answered = total_correct + total_wrong
    overall_mastery = round(total_correct / max(1, answered), 3)
    best_streak = max((int(r["streak"]) for r in items), default=0)

    by_lang: dict[str, dict[str, Any]] = {}
    for r in items:
        lang = r["language"]
        bucket = by_lang.setdefault(
            lang, {"correct": 0, "wrong": 0, "streak": 0, "item_count": 0}
        )
        bucket["correct"] += int(r["correct"])
        bucket["wrong"] += int(r["wrong"])
        bucket["streak"] = max(bucket["streak"], int(r["streak"]))
        bucket["item_count"] += 1

    for lang, bucket in by_lang.items():
        total = bucket["correct"] + bucket["wrong"]
        bucket["mastery"] = round(bucket["correct"] / max(1, total), 3)
        bucket["mastery_pct"] = int(round(bucket["mastery"] * 100))

    weak = sorted(
        [r for r in items if int(r["wrong"]) >= 2 or float(r["mastery"]) < 0.5],
        key=lambda r: (-int(r["wrong"]), float(r["mastery"])),
    )[:5]

    return {
        "answered": answered,
        "correct": total_correct,
        "wrong": total_wrong,
        "mastery": overall_mastery,
        "mastery_pct": int(round(overall_mastery * 100)),
        "best_streak": best_streak,
        "item_count": len(items),
        "by_language": by_lang,
        "weak_items": [
            {
                "language": w.get("language"),
                "item_key": (w.get("item_key") or "")[:80],
                "wrong": int(w.get("wrong") or 0),
                "mastery_pct": int(round(float(w.get("mastery") or 0) * 100)),
            }
            for w in weak
        ],
    }


def init_quiz_history_table(conn=None) -> None:
    own = conn is None
    if own:
        conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS quiz_session_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lang_key TEXT NOT NULL,
            level_num INTEGER NOT NULL,
            difficulty TEXT,
            correct INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            percentage INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_quiz_history_user
            ON quiz_session_history (user_id, created_at DESC);
        """
    )
    conn.commit()
    if own:
        conn.close()


def record_quiz_session(
    user_id: int,
    lang_key: str,
    level_num: int,
    correct: int,
    total: int,
    difficulty: Optional[str] = None,
) -> dict[str, Any]:
    """Persist one finished standalone-quiz session for history display."""
    init_quiz_history_table()
    total = max(0, int(total))
    correct = max(0, min(int(correct), total))
    percentage = round(100 * correct / total) if total else 0
    conn = get_db()
    cur = conn.execute(
        """
        INSERT INTO quiz_session_history (
            user_id, lang_key, level_num, difficulty, correct, total, percentage, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%s','now'))
        """,
        (user_id, lang_key, int(level_num), difficulty, correct, total, percentage),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return {
        "id": row_id,
        "correct": correct,
        "total": total,
        "percentage": percentage,
    }


def get_quiz_history(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    init_quiz_history_table()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, lang_key, level_num, difficulty, correct, total, percentage, created_at
        FROM quiz_session_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, max(1, min(50, int(limit)))),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
