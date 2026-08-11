"""Persistent, idempotent achievement definitions and unlock engine.

Uses only verifiable activity data — never fabricates progress.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from db import get_db

# Category keys used by the gallery UI.
CATEGORIES = (
    ("getting_started", "Getting Started"),
    ("exploration", "Exploration"),
    ("learning", "Language Learning"),
    ("dictionary", "Dictionary"),
    ("quiz", "Quiz"),
    ("consistency", "Consistency"),
    ("points", "Points / Milestones"),
)

def _build_face_values(defs: list[dict[str, Any]]) -> dict[str, int]:
    """Stable presentation face values by category order (not gameplay data)."""
    face_by_category: dict[str, int] = {}
    out: dict[str, int] = {}
    for definition in defs:
        cat = definition["category"]
        face_by_category[cat] = face_by_category.get(cat, 0) + 10
        out[definition["key"]] = face_by_category[cat]
    return out


# Curated collectible set — quality over quantity.
ACHIEVEMENT_DEFS: list[dict[str, Any]] = [
    # Getting started
    {
        "key": "first_steps",
        "title": "First Steps",
        "description": "Begin your heritage journey with a successful login.",
        "category": "getting_started",
        "icon": "steps",
        "check": "first_login",
    "rarity": "common",
    },
    {
        "key": "welcome_explorer",
        "title": "Welcome Explorer",
        "description": "Open the World Explorer for the first time.",
        "category": "getting_started",
        "icon": "globe",
        "check": "world_explorer_visit",
    "rarity": "common",
    },
    {
        "key": "first_discovery",
        "title": "First Discovery",
        "description": "Discover your first living language beacon.",
        "category": "getting_started",
        "icon": "beacon",
        "check": "passport_count_ge_1",
    "rarity": "common",
    },
    # Exploration
    {
        "key": "across_the_map",
        "title": "Across the Map",
        "description": "Discover two living language communities.",
        "category": "exploration",
        "icon": "map",
        "check": "passport_count_ge_2",
    "rarity": "uncommon",
    },
    {
        "key": "heritage_collector",
        "title": "Heritage Collector",
        "description": "Discover all four living languages of the explorer.",
        "category": "exploration",
        "icon": "passport",
        "check": "passport_count_ge_4",
    "rarity": "epic",
    },
    {
        "key": "world_traveller",
        "title": "World Traveller",
        "description": "Complete the journey from World to Malaysia.",
        "category": "exploration",
        "icon": "journey",
        "check": "malaysia_arrived",
    "rarity": "uncommon",
    },
    {
        "key": "beacon_finder",
        "title": "Beacon Finder",
        "description": "Discover a language through its living beacon.",
        "category": "exploration",
        "icon": "signal",
        "check": "beacon_discovery",
    "rarity": "common",
    },
    # Learning
    {
        "key": "first_lesson",
        "title": "First Lesson",
        "description": "Complete your first language lesson.",
        "category": "learning",
        "icon": "lesson",
        "check": "lessons_ge_1",
    "rarity": "common",
    },
    {
        "key": "keep_learning",
        "title": "Keep Learning",
        "description": "Complete five lessons across your journey.",
        "category": "learning",
        "icon": "books",
        "check": "lessons_ge_5",
    "rarity": "uncommon",
    },
    {
        "key": "language_learner",
        "title": "Language Learner",
        "description": "Complete lessons in two different languages.",
        "category": "learning",
        "icon": "dual",
        "check": "lesson_langs_ge_2",
    "rarity": "uncommon",
    },
    {
        "key": "polyglot_path",
        "title": "Polyglot Path",
        "description": "Complete lessons in all four languages.",
        "category": "learning",
        "icon": "four",
        "check": "lesson_langs_ge_4",
    "rarity": "epic",
    },
    {
        "key": "course_finisher",
        "title": "Course Finisher",
        "description": "Complete every level in one language course.",
        "category": "learning",
        "icon": "seal",
        "check": "full_course_one_lang",
    "rarity": "rare",
    },
    # Dictionary
    {
        "key": "first_word",
        "title": "First Word",
        "description": "Explore your first dictionary entry.",
        "category": "dictionary",
        "icon": "word",
        "check": "dict_views_ge_1",
    "rarity": "common",
    },
    {
        "key": "word_collector",
        "title": "Word Collector",
        "description": "Save ten words to your collection.",
        "category": "dictionary",
        "icon": "bookmark",
        "check": "saved_words_ge_10",
    "rarity": "uncommon",
    },
    {
        "key": "vocabulary_explorer",
        "title": "Vocabulary Explorer",
        "description": "Explore twenty-five dictionary entries.",
        "category": "dictionary",
        "icon": "archive",
        "check": "dict_views_ge_25",
    "rarity": "rare",
    },
    {
        "key": "four_worlds_many_words",
        "title": "Four Worlds, Many Words",
        "description": "Explore dictionary entries from all four languages.",
        "category": "dictionary",
        "icon": "lexicon",
        "check": "dict_langs_ge_4",
    "rarity": "rare",
    },
    # Quiz
    {
        "key": "first_challenge",
        "title": "First Challenge",
        "description": "Complete your first quiz session.",
        "category": "quiz",
        "icon": "challenge",
        "check": "quiz_sessions_ge_1",
    "rarity": "common",
    },
    {
        "key": "quiz_runner",
        "title": "Quiz Runner",
        "description": "Answer ten quiz questions correctly.",
        "category": "quiz",
        "icon": "runner",
        "check": "quiz_correct_ge_10",
    "rarity": "uncommon",
    },
    {
        "key": "quiz_explorer",
        "title": "Quiz Explorer",
        "description": "Complete quizzes in two languages.",
        "category": "quiz",
        "icon": "quiz",
        "check": "quiz_langs_ge_2",
    "rarity": "uncommon",
    },
    {
        "key": "daily_learner",
        "title": "Daily Learner",
        "description": "Complete a Daily Quiz.",
        "category": "quiz",
        "icon": "daily",
        "check": "daily_quiz_done",
    "rarity": "uncommon",
    },
    # Consistency (calendar activity days)
    {
        "key": "first_streak",
        "title": "First Streak",
        "description": "Return for three consecutive active days.",
        "category": "consistency",
        "icon": "flame3",
        "check": "streak_ge_3",
    "rarity": "uncommon",
    },
    {
        "key": "on_a_roll",
        "title": "On a Roll",
        "description": "Maintain a seven-day exploration streak.",
        "category": "consistency",
        "icon": "flame7",
        "check": "streak_ge_7",
    "rarity": "rare",
    },
    {
        "key": "heritage_habit",
        "title": "Heritage Habit",
        "description": "Stay active for fourteen consecutive days.",
        "category": "consistency",
        "icon": "flame14",
        "check": "streak_ge_14",
    "rarity": "epic",
    },
    {
        "key": "dedicated_explorer",
        "title": "Dedicated Explorer",
        "description": "Stay active for thirty consecutive days.",
        "category": "consistency",
        "icon": "flame30",
        "check": "streak_ge_30",
    "rarity": "epic",
    },
    # Points (dashboard XP formula)
    {
        "key": "first_100",
        "title": "First 100",
        "description": "Earn 100 explorer points.",
        "category": "points",
        "icon": "points100",
        "check": "points_ge_100",
    "rarity": "uncommon",
    },
    {
        "key": "explorer_500",
        "title": "Explorer 500",
        "description": "Earn 500 explorer points.",
        "category": "points",
        "icon": "points500",
        "check": "points_ge_500",
    "rarity": "rare",
    },
    {
        "key": "heritage_1000",
        "title": "Heritage 1000",
        "description": "Earn 1000 explorer points.",
        "category": "points",
        "icon": "points1000",
        "check": "points_ge_1000",
    "rarity": "legendary",
    },
]

ACHIEVEMENT_BY_KEY = {item["key"]: item for item in ACHIEVEMENT_DEFS}
ACHIEVEMENT_FACE_VALUES = _build_face_values(ACHIEVEMENT_DEFS)
ACHIEVEMENT_RARITIES = {item["key"]: item.get("rarity", "common") for item in ACHIEVEMENT_DEFS}
RARITY_ORDER = ("common", "uncommon", "rare", "epic", "legendary")


def achievement_rarity(key: str) -> str:
    rarity = ACHIEVEMENT_RARITIES.get(key, "common")
    return rarity if rarity in RARITY_ORDER else "common"




def init_achievement_tables(conn=None) -> None:
    own = conn is None
    if own:
        conn = get_db()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            achievement_key TEXT NOT NULL,
            unlocked_at INTEGER NOT NULL,
            notified INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, achievement_key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_user_achievements_user
            ON user_achievements (user_id);

        CREATE TABLE IF NOT EXISTS user_activity_days (
            user_id INTEGER NOT NULL,
            day_key TEXT NOT NULL,
            PRIMARY KEY (user_id, day_key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS explorer_milestones (
            user_id INTEGER NOT NULL,
            milestone_key TEXT NOT NULL,
            achieved_at INTEGER NOT NULL,
            PRIMARY KEY (user_id, milestone_key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS dictionary_views (
            user_id INTEGER NOT NULL,
            vocabulary_id INTEGER NOT NULL,
            lang_key TEXT NOT NULL,
            viewed_at INTEGER NOT NULL,
            PRIMARY KEY (user_id, vocabulary_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS mascot_preferences (
            user_id INTEGER PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 1,
            reactions_enabled INTEGER NOT NULL DEFAULT 1,
            achievement_reactions_enabled INTEGER NOT NULL DEFAULT 1,
            facts_enabled INTEGER NOT NULL DEFAULT 1,
            thoughts_enabled INTEGER NOT NULL DEFAULT 1,
            voice_enabled INTEGER NOT NULL DEFAULT 0,
            frequency TEXT NOT NULL DEFAULT 'normal',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    if own:
        conn.commit()
        conn.close()


def _day_key(ts: int | None = None) -> str:
    value = int(ts if ts is not None else time.time())
    return time.strftime("%Y-%m-%d", time.gmtime(value))


def record_activity_day(user_id: int) -> None:
    """Mark today as an active exploration day (UTC)."""
    init_achievement_tables()
    conn = get_db()
    conn.execute(
        """
        INSERT OR IGNORE INTO user_activity_days (user_id, day_key)
        VALUES (?, ?)
        """,
        (user_id, _day_key()),
    )
    conn.commit()
    conn.close()


def set_explorer_milestone(user_id: int, milestone_key: str) -> bool:
    """Record a one-time explorer milestone. Returns True if newly set."""
    init_achievement_tables()
    now = int(time.time())
    conn = get_db()
    existing = conn.execute(
        """
        SELECT 1 FROM explorer_milestones
        WHERE user_id = ? AND milestone_key = ?
        """,
        (user_id, milestone_key),
    ).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute(
        """
        INSERT INTO explorer_milestones (user_id, milestone_key, achieved_at)
        VALUES (?, ?, ?)
        """,
        (user_id, milestone_key, now),
    )
    conn.commit()
    conn.close()
    return True


def record_dictionary_view(user_id: int, vocabulary_id: int, lang_key: str) -> bool:
    init_achievement_tables()
    now = int(time.time())
    conn = get_db()
    before = conn.execute(
        """
        SELECT 1 FROM dictionary_views
        WHERE user_id = ? AND vocabulary_id = ?
        """,
        (user_id, vocabulary_id),
    ).fetchone()
    if before:
        conn.close()
        return False
    conn.execute(
        """
        INSERT INTO dictionary_views (user_id, vocabulary_id, lang_key, viewed_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, vocabulary_id, lang_key, now),
    )
    conn.commit()
    conn.close()
    return True


def get_activity_streak(user_id: int) -> int:
    """Canonical user-facing streak: consecutive UTC days with verified activity.

    This is the single streak used by the header flame, achievement consistency
    milestones, achievement summary, and mascot streak reactions.

    Distinct from quiz-mastery item streaks in learning_memory (correct-answer
    chains), which remain available on the profile as quiz stats.
    """
    conn = get_db()
    rows = conn.execute(
        """
        SELECT day_key FROM user_activity_days
        WHERE user_id = ?
        ORDER BY day_key DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    if not rows:
        return 0
    days = {row["day_key"] for row in rows}
    # Count consecutive days ending today or yesterday (UTC).
    cursor = time.gmtime()
    streak = 0
    from datetime import date, timedelta

    today = date(
        cursor.tm_year,
        cursor.tm_mon,
        cursor.tm_mday,
    )
    probe = today
    if _day_key() not in days:
        probe = today - timedelta(days=1)
        if probe.isoformat() not in days:
            return 0
    while probe.isoformat() in days:
        streak += 1
        probe -= timedelta(days=1)
    return streak


# Back-compat alias for older call sites / tests.
_calendar_streak = get_activity_streak


def collect_user_stats(user_id: int) -> dict[str, Any]:
    """Gather verifiable counters used by achievement checks."""
    from learning_memory import get_user_mastery_summary
    from language_registry import get_language_keys

    init_achievement_tables()
    conn = get_db()

    passport_count = conn.execute(
        "SELECT COUNT(*) AS c FROM heritage_passport WHERE user_id = ?",
        (user_id,),
    ).fetchone()["c"]

    lesson_rows = conn.execute(
        """
        SELECT lang_key, COUNT(*) AS c
        FROM progress
        WHERE user_id = ? AND completed = 1
        GROUP BY lang_key
        """,
        (user_id,),
    ).fetchall()
    lessons_total = sum(int(r["c"]) for r in lesson_rows)
    lesson_langs = len(lesson_rows)

    # Full course = all levels in LEVEL_TITLES for a language.
    # Count max completed levels among languages; exact full-course checked later.
    max_levels_one_lang = max((int(r["c"]) for r in lesson_rows), default=0)

    saved_words = conn.execute(
        "SELECT COUNT(*) AS c FROM saved_words WHERE user_id = ?",
        (user_id,),
    ).fetchone()["c"]

    dict_views = conn.execute(
        "SELECT COUNT(*) AS c FROM dictionary_views WHERE user_id = ?",
        (user_id,),
    ).fetchone()["c"]

    dict_langs = conn.execute(
        """
        SELECT COUNT(DISTINCT lang_key) AS c
        FROM dictionary_views WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()["c"]

    milestones = {
        row["milestone_key"]
        for row in conn.execute(
            "SELECT milestone_key FROM explorer_milestones WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    }

    quiz_sessions = 0
    quiz_langs = 0
    daily_done = 0
    try:
        quiz_sessions = conn.execute(
            """
            SELECT COUNT(*) AS c FROM quiz_session_history
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()["c"]
        quiz_langs = conn.execute(
            """
            SELECT COUNT(DISTINCT lang_key) AS c
            FROM quiz_session_history WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()["c"]
        daily_done = conn.execute(
            """
            SELECT COUNT(*) AS c FROM quiz_session_history
            WHERE user_id = ? AND difficulty = 'daily'
            """,
            (user_id,),
        ).fetchone()["c"]
    except Exception:
        pass

    conn.close()

    mastery = get_user_mastery_summary(user_id)
    quiz_correct = int(mastery.get("correct") or 0)
    quiz_answered = int(mastery.get("answered") or (quiz_correct + int(mastery.get("wrong") or 0)))
    points = lessons_total * 100 + quiz_correct * 25

    lang_keys = list(get_language_keys() or [])
    levels_per_lang = 3  # LEVEL_TITLES currently has 3 levels
    full_course = any(int(r["c"]) >= levels_per_lang for r in lesson_rows)

    streak = get_activity_streak(user_id)
    return {
        "passport_count": int(passport_count),
        "lessons_total": int(lessons_total),
        "lesson_langs": int(lesson_langs),
        "full_course_one_lang": bool(full_course),
        "max_levels_one_lang": int(max_levels_one_lang),
        "saved_words": int(saved_words),
        "dict_views": int(dict_views),
        "dict_langs": int(dict_langs),
        "quiz_sessions": int(quiz_sessions),
        "quiz_langs": int(quiz_langs),
        "quiz_correct": quiz_correct,
        "quiz_answered": quiz_answered,
        "daily_quiz_done": int(daily_done) > 0,
        "points": points,
        # Canonical user-facing streak: consecutive active days.
        "streak": streak,
        # Alias used by existing consistency achievement check keys.
        "calendar_streak": streak,
        "milestones": milestones,
        "lang_total": len(lang_keys) or 4,
    }


def _passes_check(check: str, stats: dict[str, Any]) -> bool:
    milestones = stats.get("milestones") or set()
    streak = int(stats.get("streak") or stats.get("calendar_streak") or 0)
    mapping = {
        "first_login": "first_login" in milestones,
        "world_explorer_visit": "world_explorer_visit" in milestones,
        "malaysia_arrived": "malaysia_arrived" in milestones,
        "beacon_discovery": "beacon_discovery" in milestones
        or stats["passport_count"] >= 1,
        "passport_count_ge_1": stats["passport_count"] >= 1,
        "passport_count_ge_2": stats["passport_count"] >= 2,
        "passport_count_ge_4": stats["passport_count"] >= 4,
        "lessons_ge_1": stats["lessons_total"] >= 1,
        "lessons_ge_5": stats["lessons_total"] >= 5,
        "lesson_langs_ge_2": stats["lesson_langs"] >= 2,
        "lesson_langs_ge_4": stats["lesson_langs"] >= 4,
        "full_course_one_lang": stats["full_course_one_lang"],
        "dict_views_ge_1": stats["dict_views"] >= 1,
        "dict_views_ge_25": stats["dict_views"] >= 25,
        "dict_langs_ge_4": stats["dict_langs"] >= 4,
        "saved_words_ge_10": stats["saved_words"] >= 10,
        "quiz_sessions_ge_1": stats["quiz_sessions"] >= 1,
        "quiz_correct_ge_10": stats.get("quiz_answered", stats["quiz_correct"]) >= 10,
        "quiz_langs_ge_2": stats["quiz_langs"] >= 2,
        "daily_quiz_done": stats["daily_quiz_done"],
        "streak_ge_3": streak >= 3,
        "streak_ge_7": streak >= 7,
        "streak_ge_14": streak >= 14,
        "streak_ge_30": streak >= 30,
        # Legacy check keys (same canonical streak).
        "calendar_streak_ge_3": streak >= 3,
        "calendar_streak_ge_7": streak >= 7,
        "calendar_streak_ge_14": streak >= 14,
        "calendar_streak_ge_30": streak >= 30,
        "points_ge_100": stats["points"] >= 100,
        "points_ge_500": stats["points"] >= 500,
        "points_ge_1000": stats["points"] >= 1000,
    }
    return bool(mapping.get(check, False))


def get_unlocked_keys(user_id: int) -> set[str]:
    init_achievement_tables()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT achievement_key FROM user_achievements
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return {row["achievement_key"] for row in rows}


def unlock_achievement(user_id: int, key: str) -> dict[str, Any] | None:
    """Idempotent unlock. Returns achievement payload if newly unlocked."""
    if key not in ACHIEVEMENT_BY_KEY:
        return None
    init_achievement_tables()
    now = int(time.time())
    conn = get_db()
    existing = conn.execute(
        """
        SELECT unlocked_at FROM user_achievements
        WHERE user_id = ? AND achievement_key = ?
        """,
        (user_id, key),
    ).fetchone()
    if existing:
        conn.close()
        return None
    conn.execute(
        """
        INSERT INTO user_achievements
            (user_id, achievement_key, unlocked_at, notified)
        VALUES (?, ?, ?, 0)
        """,
        (user_id, key, now),
    )
    conn.commit()
    conn.close()
    definition = ACHIEVEMENT_BY_KEY[key]
    return {
        "key": key,
        "title": definition["title"],
        "description": definition["description"],
        "category": definition["category"],
        "icon": definition["icon"],
        "face_value": ACHIEVEMENT_FACE_VALUES.get(key, 10),
        "issue_year": "2026",
        "rarity": achievement_rarity(key),
        "unlocked_at": now,
        "earned_date_label": format_earned_date(now),
        "newly_unlocked": True,
    }


def evaluate_achievements(user_id: int) -> list[dict[str, Any]]:
    """Evaluate all checks and unlock newly earned achievements."""
    record_activity_day(user_id)
    stats = collect_user_stats(user_id)
    already = get_unlocked_keys(user_id)
    newly: list[dict[str, Any]] = []
    earned_cursor = len(already)
    total = len(ACHIEVEMENT_DEFS)
    for definition in ACHIEVEMENT_DEFS:
        key = definition["key"]
        if key in already:
            continue
        if _passes_check(definition["check"], stats):
            payload = unlock_achievement(user_id, key)
            if payload:
                earned_cursor += 1
                payload["earned"] = earned_cursor
                payload["total"] = total
                newly.append(payload)
    return newly


def format_earned_date(unlocked_at: int | None) -> str | None:
    """Compact stamp-face date from real unlock timestamp (never fabricated)."""
    if unlocked_at is None:
        return None
    try:
        ts = int(unlocked_at)
    except (TypeError, ValueError):
        return None
    if ts <= 0:
        return None
    return datetime.fromtimestamp(ts).strftime("%d %b %Y").upper()


def get_achievements_gallery(user_id: int) -> dict[str, Any]:
    init_achievement_tables()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT achievement_key, unlocked_at, notified
        FROM user_achievements WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    unlocked_map = {
        row["achievement_key"]: {
            "unlocked_at": int(row["unlocked_at"]),
            "notified": bool(row["notified"]),
        }
        for row in rows
    }
    items = []
    for definition in ACHIEVEMENT_DEFS:
        key = definition["key"]
        unlock = unlocked_map.get(key)
        unlocked_at = unlock["unlocked_at"] if unlock else None
        items.append(
            {
                "key": key,
                "title": definition["title"],
                "description": definition["description"],
                "category": definition["category"],
                "icon": definition["icon"],
                "face_value": ACHIEVEMENT_FACE_VALUES.get(key, 10),
                "issue_year": "2026",
                "rarity": achievement_rarity(key),
                "unlocked": unlock is not None,
                "unlocked_at": unlocked_at,
                "earned_date_label": format_earned_date(unlocked_at),
            }
        )
    earned = sum(1 for item in items if item["unlocked"])
    return {
        # Use "entries" (not "items") so Jinja templates don't collide with dict.items.
        "entries": items,
        "items": items,
        "earned": earned,
        "total": len(items),
        "categories": [{"key": k, "label": label} for k, label in CATEGORIES],
    }


def mark_achievements_notified(user_id: int, keys: list[str] | None = None) -> None:
    """Mark achievements as shown. If keys is None, mark all pending for user."""
    init_achievement_tables()
    conn = get_db()
    if keys:
        clean = [k for k in keys if k in ACHIEVEMENT_BY_KEY]
        if not clean:
            conn.close()
            return
        placeholders = ",".join("?" for _ in clean)
        conn.execute(
            f"""
            UPDATE user_achievements
            SET notified = 1
            WHERE user_id = ? AND achievement_key IN ({placeholders})
            """,
            (user_id, *clean),
        )
    else:
        conn.execute(
            """
            UPDATE user_achievements
            SET notified = 1
            WHERE user_id = ? AND notified = 0
            """,
            (user_id,),
        )
    conn.commit()
    conn.close()


def pop_pending_achievement_notifications(user_id: int) -> list[dict[str, Any]]:
    """Return newly unlocked achievements not yet shown.

    Does **not** mark ``notified`` — the client must POST ``/api/achievements/ack``
    after the plaque is actually displayed so a failed/off-screen render cannot
    permanently swallow the unlock toast.
    """
    init_achievement_tables()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT achievement_key, unlocked_at
        FROM user_achievements
        WHERE user_id = ? AND notified = 0
        ORDER BY unlocked_at ASC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    if not rows:
        return []
    keys = [row["achievement_key"] for row in rows]
    unlocked_total = len(get_unlocked_keys(user_id))
    total = len(ACHIEVEMENT_DEFS)
    pending = []
    # Show progressive collection counts across the queued plaques.
    start_earned = max(0, unlocked_total - len(keys))
    for index, row in enumerate(rows):
        definition = ACHIEVEMENT_BY_KEY.get(row["achievement_key"])
        if not definition:
            continue
        pending.append(
            {
                "key": row["achievement_key"],
                "title": definition["title"],
                "description": definition["description"],
                "category": definition["category"],
                "icon": definition["icon"],
                "face_value": ACHIEVEMENT_FACE_VALUES.get(row["achievement_key"], 10),
                "issue_year": "2026",
                "rarity": achievement_rarity(row["achievement_key"]),
                "unlocked_at": int(row["unlocked_at"]),
                "earned_date_label": format_earned_date(int(row["unlocked_at"])),
                "earned": start_earned + index + 1,
                "total": total,
                "newly_unlocked": True,
            }
        )
    return pending


def get_mascot_preferences(user_id: int) -> dict[str, Any]:
    init_achievement_tables()
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM mascot_preferences WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        conn.execute(
            """
            INSERT INTO mascot_preferences (user_id)
            VALUES (?)
            """,
            (user_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM mascot_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    conn.close()
    return {
        "enabled": bool(row["enabled"]),
        "reactions_enabled": bool(row["reactions_enabled"]),
        "achievement_reactions_enabled": bool(row["achievement_reactions_enabled"]),
        "facts_enabled": bool(row["facts_enabled"]),
        "thoughts_enabled": bool(row["thoughts_enabled"]),
        "voice_enabled": bool(row["voice_enabled"]),
        "frequency": row["frequency"] or "normal",
    }


def update_mascot_preferences(user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    current = get_mascot_preferences(user_id)
    frequency = str(data.get("frequency") or current["frequency"]).lower()
    if frequency not in ("occasional", "normal", "frequent"):
        frequency = "normal"

    def flag(name: str) -> int:
        if name not in data:
            return 1 if current[name] else 0
        return 1 if bool(data[name]) else 0

    conn = get_db()
    conn.execute(
        """
        INSERT INTO mascot_preferences (
            user_id, enabled, reactions_enabled,
            achievement_reactions_enabled, facts_enabled,
            thoughts_enabled, voice_enabled, frequency
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            enabled = excluded.enabled,
            reactions_enabled = excluded.reactions_enabled,
            achievement_reactions_enabled = excluded.achievement_reactions_enabled,
            facts_enabled = excluded.facts_enabled,
            thoughts_enabled = excluded.thoughts_enabled,
            voice_enabled = excluded.voice_enabled,
            frequency = excluded.frequency
        """,
        (
            user_id,
            flag("enabled"),
            flag("reactions_enabled"),
            flag("achievement_reactions_enabled"),
            flag("facts_enabled"),
            flag("thoughts_enabled"),
            flag("voice_enabled"),
            frequency,
        ),
    )
    conn.commit()
    conn.close()
    return get_mascot_preferences(user_id)
