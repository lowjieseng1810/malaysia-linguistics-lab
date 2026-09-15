"""Language Review & Documentation routes and quality checks.

Run: python -m unittest tests.test_language_review -v
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

_DB_FD, _DB_PATH = tempfile.mkstemp(prefix="mmle_review_", suffix=".db")
os.close(_DB_FD)
os.environ["DATABASE_PATH"] = _DB_PATH
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-language-review-suite")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)
os.environ.pop("DATABASE_URL", None)


def _csrf(html: str) -> str:
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        raise AssertionError("csrf_token missing")
    return match.group(1)


class LanguageReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module
        from database import import_verified_vocabulary_packs, init_content_tables

        cls.app_module = app_module
        cls.app = app_module.app
        cls.app.config["TESTING"] = True
        with cls.app.app_context():
            app_module.init_db()
            init_content_tables()
            import_verified_vocabulary_packs()

    def setUp(self):
        self.client = self.app.test_client()

    def _login(self):
        from db import get_db

        conn = get_db()
        username = "reviewer1"
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if not existing:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "email" in cols:
                conn.execute(
                    """
                    INSERT INTO users (username, password, email, provider)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        username,
                        generate_password_hash("ReviewPass1"),
                        "reviewer1@example.com",
                        "local",
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, generate_password_hash("ReviewPass1")),
                )
            conn.commit()
        conn.close()
        page = self.client.get("/login")
        self.client.post(
            "/login",
            data={
                "csrf_token": _csrf(page.get_data(as_text=True)),
                "username": username,
                "password": "ReviewPass1",
            },
        )

    def test_review_requires_login(self):
        resp = self.client.get("/language/mah-meri/review", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers.get("Location", ""))

    def test_unknown_language_404(self):
        self._login()
        resp = self.client.get("/language/not-a-language/review")
        self.assertEqual(resp.status_code, 404)

    def test_review_pages_for_all_course_languages(self):
        self._login()
        for key in ("mah-meri", "iban", "bidayuh", "kadazan-dusun"):
            resp = self.client.get(f"/language/{key}/review")
            self.assertEqual(resp.status_code, 200, key)
            body = resp.get_data(as_text=True)
            self.assertIn("Language Review", body)
            self.assertIn("Overview", body)
            self.assertIn("Vocabulary", body)
            self.assertIn("Academic Review", body)
            self.assertIn("Collaboration", body)

    def test_mah_meri_corrupt_asjp_id_removed(self):
        from review_quality import detect_entry_issues

        self._login()
        body = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        self.assertNotIn(">3735<", body)
        issues = detect_entry_issues(
            {
                "word": "3735",
                "meaning_en": "2.83 101.50 2990 mhm mhe 1 I",
                "source_ref": "ASJP",
            }
        )
        codes = {i["code"] for i in issues}
        self.assertIn("isolated_number", codes)
        self.assertIn("asjp_header_bleed", codes)

    def test_mah_meri_learner_page_still_renders(self):
        self._login()
        resp = self.client.get("/language/mah-meri")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Language Review", resp.get_data(as_text=True))

    def test_unusual_form_not_auto_wrong(self):
        from review_quality import detect_entry_issues

        issues = detect_entry_issues(
            {
                "word": "hma7",
                "meaning_en": "person",
                "meaning_ms": "",
                "source_ref": "ASJP Database wordlist Mah Meri (CLLD); CC BY 4.0",
                "language": "mah-meri",
            }
        )
        self.assertEqual(issues, [])

    def test_repair_sql_is_safe_for_psycopg_placeholders(self):
        import inspect

        import db as dbmod
        from database import apply_mah_meri_vocabulary_repairs
        from psycopg._queries import _query2pg

        source = inspect.getsource(apply_mah_meri_vocabulary_repairs)
        self.assertNotIn("LIKE '%", source)
        self.assertNotIn('LIKE "%', source)

        queries = [
            """
            UPDATE vocabulary
            SET meaning_ms = COALESCE(NULLIF(TRIM(meaning_ms), ''), meaning_en),
                review_status = 'needs_verification',
                review_note = COALESCE(
                    NULLIF(TRIM(review_note), ''),
                    'Wiktionary source is Malay. English translation is not in this extract.'
                )
            WHERE language = 'mah-meri'
              AND LOWER(TRIM(word)) = LOWER(TRIM(?))
              AND COALESCE(source_ref, '') LIKE ?
            """,
            """
            UPDATE vocabulary
            SET part_of_speech = ?
            WHERE language = 'mah-meri'
              AND LOWER(TRIM(word)) = LOWER(TRIM(?))
              AND COALESCE(source_ref, '') LIKE ?
            """,
        ]
        previous = dbmod._dialect
        dbmod._dialect = "postgres"
        try:
            for sql in queries:
                adapted = dbmod.adapt_sql(sql)
                _query2pg(adapted.encode("utf-8"), "utf-8")
                self.assertNotRegex(adapted, r"%(?![st])")
        finally:
            dbmod._dialect = previous

    def test_apply_repairs_runs_on_sqlite_startup(self):
        from database import apply_mah_meri_vocabulary_repairs

        result = apply_mah_meri_vocabulary_repairs()
        self.assertIn("deleted", result)
        self.assertIn("updated", result)



if __name__ == "__main__":
    unittest.main()
