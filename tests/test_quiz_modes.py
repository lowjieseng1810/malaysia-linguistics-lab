"""Practice / Daily Quiz mode, language isolation, and Mah Meri selection.

Run: python -m unittest tests.test_quiz_modes -v
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DB_FD, _DB_PATH = tempfile.mkstemp(prefix="mmle_quiz_", suffix=".db")
os.close(_DB_FD)
os.environ["DATABASE_PATH"] = _DB_PATH
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-quiz-mode-suite")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)
os.environ.pop("DATABASE_URL", None)


def _csrf_meta(html: str) -> str:
    match = re.search(r'name="csrf-token"\s+content="([^"]+)"', html)
    if not match:
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        raise AssertionError("csrf token missing")
    return match.group(1)


class QuizModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module
        from database import import_verified_vocabulary_packs, init_content_tables, seed_tutor_content
        from app import COURSE_DATA, LANGUAGES, EXPLORE_UNLOCKS

        cls.app_module = app_module
        cls.app = app_module.app
        cls.app.config["TESTING"] = True
        with cls.app.app_context():
            app_module.init_db()
            init_content_tables()
            seed_tutor_content(COURSE_DATA, LANGUAGES, EXPLORE_UNLOCKS)
            import_verified_vocabulary_packs()

    def setUp(self):
        self.client = self.app.test_client()
        self._ensure_user()
        self._login()

    def _ensure_user(self):
        from db import get_db

        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("quiz_user",)
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
                        "quiz_user",
                        generate_password_hash("QuizPass1"),
                        "quiz_user@example.com",
                        "local",
                        "student",
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    ("quiz_user", generate_password_hash("QuizPass1")),
                )
            conn.commit()
        conn.close()

    def _login(self):
        from db import get_db

        conn = get_db()
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("quiz_user",)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        with self.client.session_transaction() as sess:
            sess["user_id"] = int(row["id"])
            sess["username"] = "quiz_user"

    def _csrf(self):
        return _csrf_meta(self.client.get("/quiz").get_data(as_text=True))

    def _start(self, payload):
        return self.client.post(
            "/api/quiz/start",
            json=payload,
            headers={"X-CSRFToken": self._csrf()},
        )

    def test_daily_page_is_not_practice_and_does_not_autostart(self):
        html = self.client.get("/quiz?mode=daily").get_data(as_text=True)
        self.assertIn("Daily Quiz", html)
        self.assertNotIn("<h1>Practice Quiz</h1>", html)
        self.assertIn('data-quiz-mode="daily"', html)
        self.assertNotIn('beginSession({ mode: "daily", count: 5 })', html)
        practice = self.client.get("/quiz").get_data(as_text=True)
        self.assertIn("<h1 id=\"quiz-title\">Practice Quiz</h1>", practice)
        self.assertIn('data-quiz-mode="practice"', practice)

    def test_daily_requires_language_and_stays_on_that_language(self):
        missing = self._start({"mode": "daily", "count": 5})
        self.assertEqual(missing.status_code, 200)
        body = missing.get_json()
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("reason"), "language_required")

        mah = self._start({"mode": "daily", "lang_key": "mah-meri"}).get_json()
        self.assertTrue(mah.get("ok"), mah)
        self.assertEqual(mah.get("mode"), "daily")
        self.assertEqual(mah.get("lang_key"), "mah-meri")
        q = (mah.get("current_question") or {}).get("question") or ""
        self.assertTrue(q)
        self.assertEqual((mah.get("current_question") or {}).get("source_lang"), "mah-meri")
        blob = q + " " + " ".join((mah.get("current_question") or {}).get("options") or [])
        self.assertNotIn("Kadazan", blob)
        self.assertNotIn("Bidayuh", blob)

        kad = self._start({"mode": "daily", "lang_key": "kadazan-dusun"}).get_json()
        self.assertTrue(kad.get("ok"), kad)
        self.assertEqual(kad.get("lang_key"), "kadazan-dusun")
        self.assertEqual(kad.get("mode"), "daily")
        self.assertNotEqual(kad.get("lang_key"), "mah-meri")

    def test_practice_languages_do_not_leak(self):
        for lang in ("iban", "bidayuh", "kadazan-dusun", "mah-meri"):
            data = self._start(
                {
                    "mode": "practice",
                    "lang_key": lang,
                    "level_num": 1,
                    "difficulty": "medium",
                    "count": 5,
                }
            ).get_json()
            self.assertTrue(data.get("ok"), (lang, data))
            self.assertEqual(data.get("mode"), "practice")
            self.assertEqual(data.get("lang_key"), lang)
            current = data.get("current_question") or {}
            self.assertTrue(current.get("question"))
            if lang == "mah-meri":
                text = current.get("question") or ""
                self.assertIn("Mah Meri", text)

    def test_changing_daily_language_replaces_session(self):
        first = self._start({"mode": "daily", "lang_key": "iban"}).get_json()
        self.assertEqual(first.get("lang_key"), "iban")
        second = self._start({"mode": "daily", "lang_key": "bidayuh"}).get_json()
        self.assertEqual(second.get("lang_key"), "bidayuh")
        state = self.client.get("/api/quiz/state").get_json()
        self.assertEqual(state.get("lang_key"), "bidayuh")
        self.assertEqual(state.get("mode"), "daily")

    def test_refresh_keeps_daily_mode_in_session(self):
        started = self._start({"mode": "daily", "lang_key": "mah-meri"}).get_json()
        self.assertTrue(started.get("ok"))
        html = self.client.get("/quiz?mode=daily").get_data(as_text=True)
        self.assertIn("Daily Quiz", html)
        state = self.client.get("/api/quiz/state").get_json()
        self.assertEqual(state.get("mode"), "daily")
        self.assertEqual(state.get("lang_key"), "mah-meri")


if __name__ == "__main__":
    unittest.main()
