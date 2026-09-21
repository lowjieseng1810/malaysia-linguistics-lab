"""Mah Meri lesson items must be the only source for that level's quizzes.

Run: python -m unittest tests.test_mah_meri_level_align -v
"""

from __future__ import annotations

import os
import random
import re
import sys
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DB_FD, _DB_PATH = tempfile.mkstemp(prefix="mmle_mm_align_", suffix=".db")
os.close(_DB_FD)
os.environ["DATABASE_PATH"] = _DB_PATH
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-mah-meri-align")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)
os.environ.pop("DATABASE_URL", None)


TAUGHT = {
    1: {
        "Selamat": "Greeting / well-being",
        "Terima kasih": "Thank you",
        "Ya": "Yes",
        "Tak": "No / not",
        "Nama?": "Name?",
        "Nama saya ...": "My name is ...",
    },
    2: {
        "orang": "person / people",
        "anak": "child",
        "ibu": "mother",
        "bapa": "father",
        "kawan": "friend",
        "keluarga": "family",
    },
    3: {
        "Apa?": "What?",
        "Siapa?": "Who?",
        "Di mana?": "Where?",
        "Ya, terima kasih.": "Yes, thank you.",
        "Tak, terima kasih.": "No, thank you.",
        "Selamat datang.": "Welcome.",
    },
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _csrf_meta(html: str) -> str:
    match = re.search(r'name="csrf-token"\s+content="([^"]+)"', html)
    if not match:
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        raise AssertionError("csrf token missing")
    return match.group(1)


class MahMeriLevelAlignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module
        from database import import_verified_vocabulary_packs, init_content_tables, seed_tutor_content

        cls.app_module = app_module
        cls.app = app_module.app
        cls.app.config["TESTING"] = True
        with cls.app.app_context():
            app_module.init_db()
            init_content_tables()
            seed_tutor_content(
                app_module.COURSE_DATA,
                app_module.LANGUAGES,
                app_module.EXPLORE_UNLOCKS,
            )
            import_verified_vocabulary_packs()

    def setUp(self):
        self.client = self.app.test_client()
        self._ensure_user()
        self._unlock_mah_meri_levels()
        self._login()

    def _ensure_user(self):
        from db import get_db

        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("mm_align_user",)
        ).fetchone()
        if not existing:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "email" in cols:
                conn.execute(
                    """
                    INSERT INTO users (username, password, email, provider, role)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "mm_align_user",
                        generate_password_hash("QuizPass1"),
                        "mm_align_user@example.com",
                        "local",
                        "student",
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    ("mm_align_user", generate_password_hash("QuizPass1")),
                )
            conn.commit()
        conn.close()

    def _unlock_mah_meri_levels(self):
        from db import get_db

        conn = get_db()
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("mm_align_user",)
        ).fetchone()
        uid = int(row["id"])
        for level_num in (1, 2, 3):
            conn.execute(
                """
                INSERT OR IGNORE INTO progress (user_id, lang_key, level_num, completed)
                VALUES (?, 'mah-meri', ?, 1)
                """,
                (uid, level_num),
            )
            conn.execute(
                """
                UPDATE progress
                SET completed = 1
                WHERE user_id = ? AND lang_key = 'mah-meri' AND level_num = ?
                """,
                (uid, level_num),
            )
        conn.commit()
        conn.close()

    def _login(self):
        from db import get_db

        conn = get_db()
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("mm_align_user",)
        ).fetchone()
        conn.close()
        with self.client.session_transaction() as sess:
            sess["user_id"] = int(row["id"])
            sess["username"] = "mm_align_user"

    def _csrf(self):
        return _csrf_meta(self.client.get("/quiz").get_data(as_text=True))

    def test_taught_sets_match_course_data(self):
        from mah_meri_quiz import taught_items_for_level

        for level_num, expected in TAUGHT.items():
            items = taught_items_for_level(level_num)
            words = {item["word"] for item in items}
            self.assertEqual(words, set(expected), level_num)
            by_word = {item["word"]: item["meaning"] for item in items}
            self.assertEqual(by_word, expected)

    def test_quick_check_only_uses_same_level_items(self):
        from mah_meri_quiz import align_mah_meri_lesson_quizzes

        course = self.app_module.COURSE_DATA["mah-meri"]
        for level_num in (1, 2, 3):
            steps = align_mah_meri_lesson_quizzes(
                list(course[level_num]["steps"]), level_num
            )
            quizzes = [s for s in steps if s.get("type") == "quiz"]
            self.assertGreaterEqual(len(quizzes), 4, level_num)
            for quiz in quizzes:
                blob_parts = [quiz.get("question") or ""] + list(quiz.get("options") or [])
                blob = " ".join(blob_parts)
                self.assertTrue(
                    any(_norm(word) in _norm(blob) for word in TAUGHT[level_num]),
                    (level_num, quiz.get("question")),
                )
                hint = quiz.get("hint") or ""
                answer = (quiz.get("options") or [])[int(quiz.get("correctIndex") or 0)]
                self.assertTrue(hint)
                self.assertNotEqual(_norm(hint), _norm(answer))
                explanation = (quiz.get("correctFeedback") or "") + " " + (quiz.get("wrongFeedback") or "")
                self.assertTrue(explanation.strip())
                self.assertTrue(
                    _norm(answer) in _norm(explanation) or _norm(answer) in _norm(blob)
                )

    def test_cross_level_words_do_not_appear_in_other_level_quizzes(self):
        from mah_meri_quiz import align_mah_meri_lesson_quizzes

        course = self.app_module.COURSE_DATA["mah-meri"]
        unique = {
            1: ["Nama saya", "Nama?"],
            2: ["keluarga", "kawan", "bapa"],
            3: ["Di mana?", "Siapa?", "Selamat datang"],
        }
        for level_num in (1, 2, 3):
            steps = align_mah_meri_lesson_quizzes(
                list(course[level_num]["steps"]), level_num
            )
            blob = " ".join(
                (s.get("question") or "") + " " + " ".join(s.get("options") or [])
                for s in steps
                if s.get("type") == "quiz"
            )
            for other_level, markers in unique.items():
                if other_level == level_num:
                    continue
                for marker in markers:
                    self.assertNotIn(marker, blob, (level_num, marker))

    def test_practice_level_stays_inside_taught_set(self):
        for level_num in (1, 2, 3):
            data = self.client.post(
                "/api/quiz/start",
                json={
                    "mode": "practice",
                    "lang_key": "mah-meri",
                    "level_num": level_num,
                    "difficulty": "medium",
                    "count": 5,
                },
                headers={"X-CSRFToken": self._csrf()},
            ).get_json()
            self.assertTrue(data.get("ok"), data)
            current = data.get("current_question") or {}
            blob = (current.get("question") or "") + " " + " ".join(current.get("options") or [])
            self.assertTrue(
                any(_norm(word) in _norm(blob) for word in TAUGHT[level_num]),
                blob,
            )
            self.assertTrue((current.get("hint") or "").strip())
            ans = self.client.post(
                "/api/quiz/answer",
                json={"answer_index": 0},
                headers={"X-CSRFToken": self._csrf()},
            ).get_json()
            self.assertTrue(ans.get("ok"), ans)
            self.assertTrue((ans.get("explanation") or "").strip())
            correct = ans.get("correct_answer") or ""
            self.assertTrue(correct)
            self.assertIn(_norm(correct).split()[0], _norm(ans.get("explanation") or "") + " " + _norm(blob))

    def test_daily_unlocked_level_1_does_not_use_level_2_or_3(self):
        from quiz_service import start_daily_quiz_session

        with self.client.session_transaction() as sess:
            user_id = sess["user_id"]
        with self.app.test_request_context():
            from flask import session as flask_session

            flask_session["user_id"] = user_id
            result = start_daily_quiz_session(
                user_id=user_id,
                unlocked_levels={"mah-meri": [1]},
                count=5,
                lang_key="mah-meri",
            )
        self.assertTrue(result.get("ok"), result)
        questions = []
        # Reconstruct from session via client after copying state is hard;
        # call API with all languages unlocked separately below.
        blob = (result.get("current_question") or {}).get("question", "")
        blob += " " + " ".join((result.get("current_question") or {}).get("options") or [])
        self.assertNotIn("keluarga", blob)
        self.assertNotIn("Di mana?", blob)
        self.assertTrue(
            any(_norm(word) in _norm(blob) for word in TAUGHT[1]),
            blob,
        )

    def test_other_languages_practice_still_starts(self):
        for lang in ("iban", "bidayuh", "kadazan-dusun"):
            data = self.client.post(
                "/api/quiz/start",
                json={
                    "mode": "practice",
                    "lang_key": lang,
                    "level_num": 1,
                    "difficulty": "medium",
                    "count": 5,
                },
                headers={"X-CSRFToken": self._csrf()},
            ).get_json()
            self.assertTrue(data.get("ok"), (lang, data))
            self.assertEqual(data.get("lang_key"), lang)

    def test_tutor_candidates_stay_in_level(self):
        from mah_meri_quiz import as_tutor_candidates, build_mah_meri_mcqs

        for level_num in (1, 2, 3):
            mcqs = build_mah_meri_mcqs(
                8, rng=random.Random(level_num), level_num=level_num
            )
            self.assertGreaterEqual(len(mcqs), 4, level_num)
            taught_words = {_norm(w) for w in TAUGHT[level_num]}
            for item in mcqs:
                self.assertIn(_norm(item["source_word"]), taught_words)
                hint = item.get("hint") or ""
                self.assertTrue(hint)
                self.assertNotEqual(_norm(hint), _norm(item["correct_answer"]))
            candidates = as_tutor_candidates(mcqs)
            self.assertEqual(len(candidates), len(mcqs))


if __name__ == "__main__":
    unittest.main()
