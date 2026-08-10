"""Database helpers for user data and tutor content tables.

Uses the unified ``db`` layer (PostgreSQL via DATABASE_URL, else local SQLite).
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from db import get_db, table_columns

VOCAB_PACK_DIR = Path(__file__).resolve().parent / "data" / "vocabulary"
TARGET_VOCAB_PER_LANGUAGE = 250
COURSE_LANGUAGES = ("iban", "kadazan-dusun", "bidayuh", "mah-meri")


def init_content_tables(conn=None) -> None:
    own = conn is None
    if own:
        conn = get_db()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            language TEXT NOT NULL,
            lesson_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            meaning_en TEXT,
            meaning_ms TEXT,
            meaning_zh TEXT,
            part_of_speech TEXT,
            difficulty TEXT,
            ipa TEXT,
            audio_path TEXT,
            example_sentence TEXT,
            culture_note TEXT
        );

        CREATE TABLE IF NOT EXISTS grammar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            language TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            explanation TEXT,
            examples TEXT,
            common_mistakes TEXT
        );

        CREATE TABLE IF NOT EXISTS culture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            language TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            content TEXT,
            image_path TEXT,
            references_text TEXT
        );

        CREATE TABLE IF NOT EXISTS quiz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            language TEXT NOT NULL DEFAULT '',
            question TEXT NOT NULL,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_answer TEXT,
            explanation TEXT,
            difficulty TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_vocab_lang_lesson
            ON vocabulary (language, lesson_id);
        CREATE INDEX IF NOT EXISTS idx_vocab_word
            ON vocabulary (word);
        CREATE INDEX IF NOT EXISTS idx_vocab_language
            ON vocabulary (language);
        CREATE INDEX IF NOT EXISTS idx_vocab_lang_word
            ON vocabulary (language, word);
        CREATE INDEX IF NOT EXISTS idx_vocab_lang_pos
            ON vocabulary (language, part_of_speech);
        CREATE INDEX IF NOT EXISTS idx_grammar_lang_lesson
            ON grammar (language, lesson_id);
        CREATE INDEX IF NOT EXISTS idx_culture_lang_lesson
            ON culture (language, lesson_id);
        CREATE INDEX IF NOT EXISTS idx_quiz_lang_lesson
            ON quiz (language, lesson_id);
        """
    )
    _ensure_vocabulary_provenance_columns(conn)
    # Learning memory for adaptive tutoring + standalone quiz history
    from learning_memory import init_user_progress_table, init_quiz_history_table

    init_user_progress_table(conn)
    init_quiz_history_table(conn)
    conn.commit()
    if own:
        conn.close()


def _vocab_columns(conn) -> set[str]:
    return table_columns(conn, "vocabulary")


def _ensure_vocabulary_provenance_columns(conn) -> None:
    """Minimal compatible extension: source + dialect metadata."""
    cols = _vocab_columns(conn)
    if "source_ref" not in cols:
        conn.execute("ALTER TABLE vocabulary ADD COLUMN source_ref TEXT")
    if "dialect_variant" not in cols:
        conn.execute("ALTER TABLE vocabulary ADD COLUMN dialect_variant TEXT")
    # Tag legacy course/quiz rows once so provenance is never silent.
    conn.execute(
        """
        UPDATE vocabulary
        SET source_ref = COALESCE(NULLIF(TRIM(source_ref), ''), ?)
        WHERE source_ref IS NULL OR TRIM(source_ref) = ''
        """,
        ("course_database",),
    )
    # Hot Dictionary browse/search paths (safe IF NOT EXISTS on existing DBs).
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_vocab_language ON vocabulary (language)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_vocab_lang_word ON vocabulary (language, word)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_vocab_lang_pos ON vocabulary (language, part_of_speech)"
    )


def _classify_pos(word: str, meaning: str) -> str:
    text = f"{word} {meaning}".lower()
    greeting_bits = (
        "welcome", "hello", "how are you", "good morning", "good night",
        "thank", "goodbye", "name is", "my name", "what is your name",
    )
    if any(bit in text for bit in greeting_bits):
        return "greeting"
    if any(bit in text for bit in (
        "father", "mother", "child", "friend", "family", "brother", "sister",
    )):
        return "noun"
    if any(bit in text for bit in (
        "eat", "drink", "go", "come", "sleep", "walk", "run", "speak", "say",
    )):
        return "verb"
    if any(bit in text for bit in (
        "dog", "cat", "bird", "fish", "animal", "chicken", "pig", "cow",
    )):
        return "animal"
    if any(bit in text for bit in (
        "rice", "food", "water", "fruit", "meat", "tea", "coffee",
    )):
        return "food"
    if any(bit in text for bit in (
        "one", "two", "three", "four", "five", "number", "ten",
    )):
        return "number"
    if "?" in word or meaning.strip().endswith("?"):
        return "phrase"
    return "expression"


def _difficulty_for(word: str) -> str:
    length = len((word or "").replace(" ", ""))
    if length <= 5:
        return "easy"
    if length <= 10:
        return "medium"
    return "hard"


def _normalize_vocab_word(word: str) -> str:
    text = unicodedata.normalize("NFC", (word or "").strip())
    text = re.sub(r"\s+", " ", text)
    return text


def _upsert_vocab(conn, row: dict[str, Any]) -> bool:
    """Insert a vocabulary row if missing. Returns True when inserted."""
    _ensure_vocabulary_provenance_columns(conn)
    word = _normalize_vocab_word(row.get("word") or "")
    if not word:
        return False
    language = (row.get("language") or "").strip()
    lesson_id = int(row.get("lesson_id") or 1)
    exists = conn.execute(
        """
        SELECT id FROM vocabulary
        WHERE language = ?
          AND LOWER(TRIM(word)) = LOWER(TRIM(?))
        LIMIT 1
        """,
        (language, word),
    ).fetchone()
    if exists:
        return False
    conn.execute(
        """
        INSERT INTO vocabulary (
            language, lesson_id, word, meaning_en, meaning_ms, meaning_zh,
            part_of_speech, difficulty, ipa, audio_path, example_sentence,
            culture_note, source_ref, dialect_variant
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            language,
            lesson_id,
            word,
            row.get("meaning_en"),
            row.get("meaning_ms"),
            row.get("meaning_zh"),
            row.get("part_of_speech"),
            row.get("difficulty"),
            row.get("ipa"),
            row.get("audio_path"),
            row.get("example_sentence"),
            row.get("culture_note"),
            row.get("source_ref") or "course_database",
            row.get("dialect_variant"),
        ),
    )
    return True


def _insert_vocab(conn, row: dict[str, Any]) -> bool:
    """Compatibility alias used by sync/enrich helpers."""
    return _upsert_vocab(conn, row)


def _collect_vocab_from_steps(
    lang_key: str,
    level_num: int,
    steps: Iterable[dict],
) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()

    def add(word: str, meaning: str, note: str = "") -> None:
        clean = (word or "").strip()
        if not clean:
            return
        key = clean.lower()
        if key in seen:
            return
        seen.add(key)
        items.append(
            {
                "language": lang_key,
                "lesson_id": level_num,
                "word": clean,
                "meaning_en": (meaning or "").strip() or None,
                "meaning_ms": None,
                "meaning_zh": None,
                "part_of_speech": _classify_pos(clean, meaning or ""),
                "difficulty": _difficulty_for(clean),
                "ipa": None,
                "audio_path": None,
                "example_sentence": None,
                "culture_note": (note or "").strip() or None,
                "source_ref": "course_database",
                "dialect_variant": None,
            }
        )

    for step in steps:
        step_type = step.get("type")
        if step_type == "discover":
            add(step.get("expression", ""), step.get("meaning", ""), step.get("context", ""))
        elif step_type == "respond":
            options = step.get("options") or []
            idx = step.get("correctIndex", 0)
            if isinstance(idx, int) and 0 <= idx < len(options):
                add(options[idx], step.get("responseMeaning", ""), step.get("hint", ""))
        elif step_type == "vocabulary":
            add(step.get("word", ""), step.get("meaning", ""), step.get("note", ""))
        elif step_type == "conversation":
            for turn in step.get("turns") or []:
                options = turn.get("options") or []
                idx = turn.get("correctIndex", 0)
                prompt = turn.get("prompt", "")
                if prompt:
                    add(prompt, "", "")
                if isinstance(idx, int) and 0 <= idx < len(options):
                    add(options[idx], "", turn.get("correctFeedback", ""))
    return items


def _collect_quiz_from_steps(
    lang_key: str,
    level_num: int,
    steps: Iterable[dict],
) -> list[dict]:
    items: list[dict] = []
    for step in steps:
        if step.get("type") != "quiz":
            continue
        options = list(step.get("options") or [])
        while len(options) < 4:
            options.append("")
        idx = step.get("correctIndex", 0)
        correct = ""
        if isinstance(idx, int) and 0 <= idx < len(options):
            correct = options[idx]
        question = (
            step.get("question")
            or step.get("prompt")
            or step.get("title")
            or "Choose the correct answer."
        )
        items.append(
            {
                "language": lang_key,
                "lesson_id": level_num,
                "question": question,
                "option_a": options[0],
                "option_b": options[1],
                "option_c": options[2],
                "option_d": options[3],
                "correct_answer": correct,
                "explanation": (
                    step.get("correctFeedback")
                    or step.get("explanation")
                    or step.get("note")
                    or ""
                ),
                "difficulty": step.get("difficulty") or "medium",
            }
        )
    return items


def _generate_vocab_quizzes(vocab_rows: list[dict]) -> list[dict]:
    by_lesson: dict[tuple[str, int], list[dict]] = {}
    for row in vocab_rows:
        by_lesson.setdefault((row["language"], row["lesson_id"]), []).append(row)

    generated: list[dict] = []
    for (lang, lesson_id), rows in by_lesson.items():
        if len(rows) < 4:
            continue
        meanings = [r["meaning_en"] for r in rows if r.get("meaning_en")]
        words = [r["word"] for r in rows]
        for row in rows[:8]:
            meaning = row.get("meaning_en") or ""
            word = row["word"]
            if not meaning:
                continue
            distractors = [m for m in meanings if m != meaning][:3]
            while len(distractors) < 3 and meanings:
                distractors.append(meanings[len(distractors) % len(meanings)])
            options = [meaning] + distractors[:3]
            generated.append(
                {
                    "language": lang,
                    "lesson_id": lesson_id,
                    "question": f'What does "{word}" mean?',
                    "option_a": options[0],
                    "option_b": options[1],
                    "option_c": options[2],
                    "option_d": options[3],
                    "correct_answer": meaning,
                    "explanation": f'"{word}" means "{meaning}".',
                    "difficulty": row.get("difficulty") or "medium",
                }
            )
            word_distractors = [w for w in words if w != word][:3]
            while len(word_distractors) < 3:
                word_distractors.append(words[len(word_distractors) % len(words)])
            w_options = [word] + word_distractors[:3]
            generated.append(
                {
                    "language": lang,
                    "lesson_id": lesson_id,
                    "question": f'Which word means "{meaning}"?',
                    "option_a": w_options[0],
                    "option_b": w_options[1],
                    "option_c": w_options[2],
                    "option_d": w_options[3],
                    "correct_answer": word,
                    "explanation": f'The word for "{meaning}" is "{word}".',
                    "difficulty": row.get("difficulty") or "medium",
                }
            )
    return generated


def sync_missing_vocabulary_from_course(course_data: dict) -> dict[str, int]:
    """
    Insert any COURSE_DATA vocabulary rows that are missing from SQLite.
    Never invents words — only harvests existing course steps.
    Safe to run repeatedly (skips duplicates by language+lesson+word).
    """
    conn = get_db()
    init_content_tables(conn)
    inserted = 0
    scanned = 0

    for lang_key, levels in (course_data or {}).items():
        if not isinstance(levels, dict):
            continue
        for level_num, payload in levels.items():
            if not isinstance(level_num, int):
                try:
                    level_num = int(level_num)
                except (TypeError, ValueError):
                    continue
            steps = (payload or {}).get("steps") or []
            for row in _collect_vocab_from_steps(lang_key, level_num, steps):
                scanned += 1
                exists = conn.execute(
                    """
                    SELECT 1 FROM vocabulary
                    WHERE language = ?
                      AND lesson_id = ?
                      AND LOWER(TRIM(word)) = LOWER(TRIM(?))
                    LIMIT 1
                    """,
                    (row["language"], row["lesson_id"], row["word"]),
                ).fetchone()
                if exists:
                    continue
                _insert_vocab(conn, row)
                inserted += 1

    enrich = enrich_vocabulary_from_quiz_stems(conn)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) AS c FROM vocabulary").fetchone()["c"]
    conn.close()
    return {
        "scanned": scanned,
        "inserted": inserted,
        "enrich_inserted": enrich.get("inserted", 0),
        "vocabulary": total,
    }


def seed_tutor_content(
    course_data: dict,
    languages: dict,
    explore_unlocks: dict | None = None,
) -> dict[str, int]:
    """Populate content tables from course dictionaries if vocabulary is empty."""
    conn = get_db()
    init_content_tables(conn)

    existing = conn.execute("SELECT COUNT(*) AS c FROM vocabulary").fetchone()["c"]
    if existing > 0:
        # Keep dictionary coverage current when COURSE_DATA gains entries.
        conn.close()
        synced = sync_missing_vocabulary_from_course(course_data or {})
        return {
            "skipped": 1,
            "vocabulary": synced.get("vocabulary", existing),
            "synced_inserted": synced.get("inserted", 0),
            "enrich_inserted": synced.get("enrich_inserted", 0),
        }

    vocab_rows: list[dict] = []
    quiz_rows: list[dict] = []
    grammar_rows: list[dict] = []
    culture_rows: list[dict] = []

    for lang_key, levels in (course_data or {}).items():
        if not isinstance(levels, dict):
            continue
        for level_num, payload in levels.items():
            if not isinstance(level_num, int):
                try:
                    level_num = int(level_num)
                except (TypeError, ValueError):
                    continue
            steps = (payload or {}).get("steps") or []
            lesson_vocab = _collect_vocab_from_steps(lang_key, level_num, steps)
            vocab_rows.extend(lesson_vocab)
            quiz_rows.extend(_collect_quiz_from_steps(lang_key, level_num, steps))

            examples = []
            for item in lesson_vocab[:6]:
                if item.get("meaning_en"):
                    examples.append(f'{item["word"]} = {item["meaning_en"]}')
            grammar_rows.append(
                {
                    "language": lang_key,
                    "lesson_id": level_num,
                    "title": f"Lesson {level_num} language patterns",
                    "explanation": (
                        f"This lesson introduces useful "
                        f"{lang_key.replace('-', ' ').title()} expressions and vocabulary. "
                        "Focus on recognising the form, matching it to meaning, and using "
                        "it in a short exchange."
                    ),
                    "examples": " | ".join(examples) if examples else "",
                    "common_mistakes": (
                        "Do not mix greeting forms with name introductions. "
                        "Match the response to the question being asked."
                    ),
                }
            )

    quiz_rows.extend(_generate_vocab_quizzes(vocab_rows))

    # Auto-generated vocab quizzes can coincidentally repeat the exact
    # phrasing of a hand-authored lesson quiz step (e.g. both producing
    # `What does "Indo" mean?` for the same word). De-duplicate by
    # (language, lesson_id, question) and keep the first occurrence, so
    # hand-authored questions (added earlier in the list) win over the
    # auto-generated fallback.
    _seen_quiz_keys: set[tuple[str, int, str]] = set()
    _deduped_quiz_rows: list[dict] = []
    for row in quiz_rows:
        key = (
            row["language"],
            row["lesson_id"],
            " ".join((row["question"] or "").strip().lower().split()),
        )
        if key in _seen_quiz_keys:
            continue
        _seen_quiz_keys.add(key)
        _deduped_quiz_rows.append(row)
    quiz_rows = _deduped_quiz_rows

    for lang_key, meta in (languages or {}).items():
        if not isinstance(meta, dict):
            continue
        display = meta.get("display_name") or lang_key
        for field, title in (
            ("about", meta.get("about_title") or f"About {display}"),
            ("speakers", meta.get("speakers_title") or f"{display} speakers"),
            ("location", meta.get("location_title") or f"Where {display} is spoken"),
            ("preservation", meta.get("preservation_title") or f"Preserving {display}"),
        ):
            content = (meta.get(field) or "").strip()
            if not content:
                continue
            culture_rows.append(
                {
                    "language": lang_key,
                    "lesson_id": 1,
                    "title": title,
                    "content": content,
                    "image_path": None,
                    "references_text": meta.get("verification_note") or "",
                }
            )
        for slide in meta.get("gallery") or []:
            if not isinstance(slide, dict):
                continue
            culture_rows.append(
                {
                    "language": lang_key,
                    "lesson_id": 1,
                    "title": slide.get("title") or "Cultural image",
                    "content": slide.get("caption") or "",
                    "image_path": slide.get("image_url"),
                    "references_text": slide.get("source_name") or "",
                }
            )

    if explore_unlocks:
        for lang_key, levels in explore_unlocks.items():
            if not isinstance(levels, dict):
                continue
            for level_num, unlock in levels.items():
                if not isinstance(unlock, dict):
                    continue
                try:
                    lesson_id = int(level_num)
                except (TypeError, ValueError):
                    continue
                description = unlock.get("description") or unlock.get("world_message") or ""
                if description:
                    culture_rows.append(
                        {
                            "language": lang_key,
                            "lesson_id": lesson_id,
                            "title": unlock.get("title")
                            or unlock.get("journey_title")
                            or "Lesson culture",
                            "content": description,
                            "image_path": None,
                            "references_text": "",
                        }
                    )

    for row in vocab_rows:
        _upsert_vocab(conn, row)

    for row in grammar_rows:
        conn.execute(
            """
            INSERT INTO grammar (lesson_id, language, title, explanation, examples, common_mistakes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["lesson_id"],
                row["language"],
                row["title"],
                row["explanation"],
                row["examples"],
                row["common_mistakes"],
            ),
        )

    for row in culture_rows:
        conn.execute(
            """
            INSERT INTO culture (lesson_id, language, title, content, image_path, references_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["lesson_id"],
                row["language"],
                row["title"],
                row["content"],
                row.get("image_path"),
                row.get("references_text"),
            ),
        )

    for row in quiz_rows:
        conn.execute(
            """
            INSERT INTO quiz (
                lesson_id, language, question, option_a, option_b, option_c, option_d,
                correct_answer, explanation, difficulty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["lesson_id"],
                row["language"],
                row["question"],
                row["option_a"],
                row["option_b"],
                row["option_c"],
                row["option_d"],
                row["correct_answer"],
                row["explanation"],
                row["difficulty"],
            ),
        )

    conn.commit()
    # Harvest additional verified word/meaning pairs already present as
    # quiz stems (e.g. What does "Kaban" mean? → Friend). Never invents.
    enrich_vocabulary_from_quiz_stems(conn)
    counts = {
        "vocabulary": conn.execute("SELECT COUNT(*) AS c FROM vocabulary").fetchone()["c"],
        "grammar": conn.execute("SELECT COUNT(*) AS c FROM grammar").fetchone()["c"],
        "culture": conn.execute("SELECT COUNT(*) AS c FROM culture").fetchone()["c"],
        "quiz": conn.execute("SELECT COUNT(*) AS c FROM quiz").fetchone()["c"],
    }
    conn.close()
    return counts


_QUIZ_MEANING_RE = re.compile(
    r'what\s+does\s+[\'"“]?(.+?)[\'"”]?\s+mean\??',
    re.IGNORECASE,
)
_QUIZ_REVERSE_RE = re.compile(
    r'(?:which|what)\s+(?:word|expression|phrase)?\s*(?:means|is)\s+[\'"“]?(.+?)[\'"”]?\s*\??$',
    re.IGNORECASE,
)


def enrich_vocabulary_from_quiz_stems(conn=None) -> dict[str, int]:
    """
    Insert vocabulary rows inferred from verified quiz stems already in SQLite.

    Harvests:
    - What does "Word" mean? → correct_answer as meaning
    - Which word means "Friend"? → correct_answer as word, captured gloss as meaning
    Skips duplicates. Does not invent IPA or examples.
    """
    own = conn is None
    if own:
        conn = get_db()
    init_content_tables(conn)

    rows = conn.execute(
        """
        SELECT language, lesson_id, question, correct_answer, difficulty
        FROM quiz
        WHERE question IS NOT NULL
          AND correct_answer IS NOT NULL
          AND TRIM(correct_answer) != ''
        """
    ).fetchall()

    inserted = 0
    skipped = 0

    def _exists(language: str, lesson_id: int, word: str) -> bool:
        return bool(
            conn.execute(
                """
                SELECT 1 FROM vocabulary
                WHERE language = ?
                  AND LOWER(TRIM(word)) = LOWER(TRIM(?))
                LIMIT 1
                """,
                (language, word),
            ).fetchone()
        )

    for row in rows:
        question = (row["question"] or "").strip()
        answer = (row["correct_answer"] or "").strip()
        if not answer:
            skipped += 1
            continue

        word = None
        meaning = None

        match = _QUIZ_MEANING_RE.search(question)
        if match:
            word = match.group(1).strip().strip("\"'“”")
            meaning = answer
        else:
            rev = _QUIZ_REVERSE_RE.search(question)
            if rev:
                meaning = rev.group(1).strip().strip("\"'“”")
                word = answer

        if not word or not meaning:
            skipped += 1
            continue
        if len(word) > 80 or len(meaning) > 120:
            skipped += 1
            continue
        if " " in word and word.lower() == word and len(word.split()) > 4:
            skipped += 1
            continue
        if _exists(row["language"], row["lesson_id"], word):
            skipped += 1
            continue

        if _insert_vocab(
            conn,
            {
                "language": row["language"],
                "lesson_id": row["lesson_id"],
                "word": word,
                "meaning_en": meaning,
                "meaning_ms": None,
                "meaning_zh": None,
                "part_of_speech": _classify_pos(word, meaning),
                "difficulty": row["difficulty"] or "medium",
                "ipa": None,
                "audio_path": None,
                "example_sentence": None,
                "culture_note": "Harvested from verified course quiz stem.",
                "source_ref": "course_quiz_stem",
                "dialect_variant": None,
            },
        ):
            inserted += 1
        else:
            skipped += 1

    if own:
        conn.commit()
        total = conn.execute("SELECT COUNT(*) AS c FROM vocabulary").fetchone()["c"]
        conn.close()
        return {"inserted": inserted, "skipped": skipped, "vocabulary": total}

    total = conn.execute("SELECT COUNT(*) AS c FROM vocabulary").fetchone()["c"]
    return {"inserted": inserted, "skipped": skipped, "vocabulary": total}


def vocabulary_counts_by_language(conn=None) -> dict[str, int]:
    own = conn is None
    if own:
        conn = get_db()
    init_content_tables(conn)
    rows = conn.execute(
        """
        SELECT language, COUNT(*) AS c
        FROM vocabulary
        WHERE word IS NOT NULL AND TRIM(word) != ''
        GROUP BY language
        """
    ).fetchall()
    counts = {lang: 0 for lang in COURSE_LANGUAGES}
    for row in rows:
        counts[row["language"]] = int(row["c"])
    if own:
        conn.close()
    return counts


def vocabulary_coverage_report(conn=None) -> dict[str, Any]:
    """Honest coverage vs the 250/language learning target."""
    counts = vocabulary_counts_by_language(conn)
    per_language = {}
    for lang in COURSE_LANGUAGES:
        verified = counts.get(lang, 0)
        per_language[lang] = {
            "verified": verified,
            "target": TARGET_VOCAB_PER_LANGUAGE,
            "unavailable": max(0, TARGET_VOCAB_PER_LANGUAGE - verified),
        }
    return {
        "target_per_language": TARGET_VOCAB_PER_LANGUAGE,
        "total_verified": sum(counts.values()),
        "total_target": TARGET_VOCAB_PER_LANGUAGE * len(COURSE_LANGUAGES),
        "languages": per_language,
    }


def import_verified_vocabulary_packs(
    pack_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    Import verified vocabulary JSON packs from data/vocabulary/.

    Pack schema (one language per file, or a multi-language file):
    {
      "language": "iban",
      "source_ref": "Publisher / dictionary title (year)",
      "dialect_variant": "optional variety label",
      "entries": [
        {
          "word": "...",
          "meaning_en": "...",
          "meaning_ms": "...",
          "part_of_speech": "noun",
          "lesson_id": 1,
          "ipa": null,
          "example_sentence": null,
          "dialect_variant": null,
          "source_ref": "optional per-entry override"
        }
      ]
    }

    Never invents entries. Missing/invalid rows are rejected with reasons.
    """
    root = Path(pack_dir) if pack_dir else VOCAB_PACK_DIR
    conn = get_db()
    init_content_tables(conn)

    inserted = 0
    duplicates = 0
    rejected: list[dict[str, str]] = []
    files_seen: list[str] = []

    if not root.is_dir():
        conn.close()
        return {
            "inserted": 0,
            "duplicates": 0,
            "rejected": [{"reason": "pack_dir_missing", "path": str(root)}],
            "files": [],
            "coverage": vocabulary_coverage_report(conn=None),
        }

    for path in sorted(root.glob("*.json")):
        if path.name.lower() in {"sources.json", "manifest.json"}:
            continue
        files_seen.append(path.name)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            rejected.append({"file": path.name, "reason": f"invalid_json:{exc}"})
            continue

        packs = payload if isinstance(payload, list) else [payload]
        for pack in packs:
            if not isinstance(pack, dict):
                rejected.append({"file": path.name, "reason": "pack_not_object"})
                continue
            language = (pack.get("language") or "").strip()
            if language not in COURSE_LANGUAGES:
                rejected.append(
                    {
                        "file": path.name,
                        "reason": f"unsupported_language:{language or 'missing'}",
                    }
                )
                continue
            pack_source = (pack.get("source_ref") or "").strip()
            if not pack_source:
                rejected.append({"file": path.name, "reason": "missing_source_ref"})
                continue
            pack_dialect = (pack.get("dialect_variant") or None) or None
            entries = pack.get("entries") or []
            if not isinstance(entries, list):
                rejected.append({"file": path.name, "reason": "entries_not_list"})
                continue
            for idx, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    rejected.append(
                        {"file": path.name, "reason": f"entry_{idx}_not_object"}
                    )
                    continue
                word = _normalize_vocab_word(entry.get("word") or "")
                meaning = (entry.get("meaning_en") or entry.get("meaning") or "").strip()
                if not word or not meaning:
                    rejected.append(
                        {
                            "file": path.name,
                            "reason": f"entry_{idx}_missing_word_or_meaning",
                            "word": word,
                        }
                    )
                    continue
                source_ref = (entry.get("source_ref") or pack_source).strip()
                dialect = entry.get("dialect_variant")
                if dialect is None:
                    dialect = pack_dialect
                row = {
                    "language": language,
                    "lesson_id": int(entry.get("lesson_id") or 1),
                    "word": word,
                    "meaning_en": meaning,
                    "meaning_ms": entry.get("meaning_ms"),
                    "meaning_zh": entry.get("meaning_zh"),
                    "part_of_speech": entry.get("part_of_speech")
                    or _classify_pos(word, meaning),
                    "difficulty": entry.get("difficulty") or _difficulty_for(word),
                    "ipa": entry.get("ipa"),
                    "audio_path": entry.get("audio_path"),
                    "example_sentence": entry.get("example_sentence"),
                    "culture_note": entry.get("culture_note"),
                    "source_ref": source_ref,
                    "dialect_variant": dialect,
                }
                if _insert_vocab(conn, row):
                    inserted += 1
                else:
                    duplicates += 1

    conn.commit()
    coverage = vocabulary_coverage_report(conn)
    conn.close()
    return {
        "inserted": inserted,
        "duplicates": duplicates,
        "rejected": rejected,
        "files": files_seen,
        "coverage": coverage,
    }
