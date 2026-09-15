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
os.environ.pop("ADMIN_USERNAMES", None)


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


class ReviewerPermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LanguageReviewTests.setUpClass()
        cls.app_module = LanguageReviewTests.app_module
        cls.app = LanguageReviewTests.app

    def setUp(self):
        self.client = self.app.test_client()
    def _insert_user(self, username, password, role=None):
        from db import get_db
        from reviewer_auth import ensure_reviewer_schema

        conn = get_db()
        ensure_reviewer_schema(conn)
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
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
                        username,
                        generate_password_hash(password),
                        f"{username}@example.com",
                        "local",
                        role or "student",
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), role or "student"),
                )
        elif role:
            conn.execute(
                "UPDATE users SET role = ? WHERE username = ?",
                (role, username),
            )
        conn.commit()
        conn.close()

    def _login_as(self, username, password):
        page = self.client.get("/login")
        resp = self.client.post(
            "/login",
            data={
                "csrf_token": _csrf(page.get_data(as_text=True)),
                "username": username,
                "password": password,
            },
        )
        self.assertNotIn(resp.status_code, (400, 401, 403, 500))

    def _token(self, path="/login"):
        return _csrf(self.client.get(path).get_data(as_text=True))

    def _queue_vocab(self, language="mah-meri"):
        from db import get_db

        conn = get_db()
        row = conn.execute(
            """
            SELECT id, word, review_status FROM vocabulary
            WHERE language = ?
              AND (review_status = 'needs_verification' OR review_status = 'source_derived')
            ORDER BY id
            LIMIT 1
            """,
            (language,),
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return int(row["id"]), row["word"]

    def test_student_cannot_change_review_status_or_call_mutations(self):
        self._insert_user("student_user", "StudentPass1", "student")
        self._login_as("student_user", "StudentPass1")
        html = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        self.assertIn("Review Queue", html)
        self.assertIn("read-only", html)
        self.assertNotIn("review-select-trigger", html)
        token = self._token("/language/mah-meri/review")
        vocab_id, _ = self._queue_vocab("mah-meri")
        section = self.client.post(
            "/language/mah-meri/review/section",
            data={
                "csrf_token": token,
                "section_key": "community",
                "status": "academically_reviewed",
            },
        )
        self.assertEqual(section.status_code, 403)
        vocab = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
                "note": "should fail",
            },
        )
        self.assertEqual(vocab.status_code, 403)
        note = self.client.post(
            "/language/mah-meri/review/academic-note",
            data={
                "csrf_token": token,
                "comments": "should fail",
            },
        )
        self.assertEqual(note.status_code, 403)

    def test_student_cannot_grant_themselves_reviewer_access(self):
        self._insert_user("student_user", "StudentPass1", "student")
        self._login_as("student_user", "StudentPass1")
        token = self._token("/login")
        resp = self.client.post(
            "/admin/reviewers/grant",
            data={
                "csrf_token": token,
                "username": "student_user",
                "language": "mah-meri",
                "reviewer_kind": "academic",
            },
        )
        self.assertEqual(resp.status_code, 403)
        from reviewer_auth import get_user_access
        from db import get_db

        conn = get_db()
        user = conn.execute(
            "SELECT id, role FROM users WHERE username = ?", ("student_user",)
        ).fetchone()
        conn.close()
        access = get_user_access(user["id"])
        self.assertEqual(access["role"], "student")
        self.assertFalse(access["can_edit_any"])

    def test_reviewer_scope_is_language_limited(self):
        from reviewer_auth import grant_reviewer_access

        self._insert_user("site_admin", "AdminPass1", "admin")
        self._insert_user("roshidah_hassan", "ReviewPass1", "student")
        grant_reviewer_access(
            "roshidah_hassan", "mah-meri", "academic", granted_by=1
        )
        self._login_as("roshidah_hassan", "ReviewPass1")
        mah = self.client.get("/language/mah-meri/review")
        self.assertEqual(mah.status_code, 200)
        body = mah.get_data(as_text=True)
        self.assertIn("Review Queue", body)
        self.assertIn("review-select-trigger", body)
        self.assertIn("Academically reviewed", body)
        token = self._token("/language/mah-meri/review")
        vocab_id, word = self._queue_vocab("mah-meri")
        ok = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
                "note": "Checked against source.",
            },
            follow_redirects=True,
        )
        self.assertEqual(ok.status_code, 200)
        reviewed_page = ok.get_data(as_text=True)
        self.assertNotIn(f'data-vocab-id="{vocab_id}"', reviewed_page)
        self.assertIn("Academically reviewed", reviewed_page)
        vocab_json = re.search(
            r'<script id="review-vocab-data" type="application/json">(.*?)</script>',
            reviewed_page,
            re.S,
        )
        self.assertIsNotNone(vocab_json)
        import json

        rows = json.loads(vocab_json.group(1))
        match = next(r for r in rows if r.get("id") == vocab_id)
        self.assertEqual(match["review_status"], "academically_reviewed")
        self.assertEqual(match["review_status_label"], "Academically reviewed")
        self.assertIn("Checked against source", match.get("review_note") or "")
        self.assertTrue(match.get("history"))

        from db import get_db

        conn = get_db()
        history = conn.execute(
            "SELECT * FROM vocabulary_review_history WHERE vocabulary_id = ?",
            (vocab_id,),
        ).fetchall()
        conn.close()
        self.assertTrue(history)

        for other in ("iban", "bidayuh", "kadazan-dusun"):
            other_id, _ = self._queue_vocab(other)
            blocked = self.client.post(
                f"/language/{other}/review/vocabulary",
                data={
                    "csrf_token": token,
                    "vocab_id": str(other_id),
                    "status": "academically_reviewed",
                    "note": "out of scope",
                },
            )
            self.assertEqual(blocked.status_code, 403, other)
            section = self.client.post(
                f"/language/{other}/review/section",
                data={
                    "csrf_token": token,
                    "section_key": "community",
                    "status": "academically_reviewed",
                },
            )
            self.assertEqual(section.status_code, 403, other)

    def test_admin_grants_and_revokes_by_username(self):
        from reviewer_auth import get_user_access, list_reviewer_grants

        self._insert_user("site_admin", "AdminPass1", "admin")
        self._insert_user("scoped_reviewer", "ReviewPass1", "student")
        self._login_as("site_admin", "AdminPass1")
        admin_page = self.client.get("/admin/reviewers")
        self.assertEqual(admin_page.status_code, 200)
        body = admin_page.get_data(as_text=True)
        self.assertIn("Reviewer Management", body)
        self.assertIn("Grant Access", body)
        token = self._token("/admin/reviewers")
        grant = self.client.post(
            "/admin/reviewers/grant",
            data={
                "csrf_token": token,
                "username": "scoped_reviewer",
                "language": "iban",
                "reviewer_kind": "community",
            },
            follow_redirects=True,
        )
        self.assertEqual(grant.status_code, 200)
        self.assertIn("scoped_reviewer", grant.get_data(as_text=True))
        grants = [g for g in list_reviewer_grants() if g["username"] == "scoped_reviewer"]
        self.assertTrue(grants)
        self.assertEqual(grants[0]["language"], "iban")
        self.assertEqual(grants[0]["reviewer_kind"], "community")
        from db import get_db

        conn = get_db()
        user = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("scoped_reviewer",)
        ).fetchone()
        conn.close()
        access = get_user_access(user["id"])
        self.assertTrue(access["can_edit_any"])
        self.assertIn("iban", access["active_languages"])
        self.assertNotIn("mah-meri", access["active_languages"])

        revoke = self.client.post(
            "/admin/reviewers/revoke",
            data={
                "csrf_token": token,
                "scope_id": str(grants[0]["id"]),
            },
            follow_redirects=True,
        )
        self.assertEqual(revoke.status_code, 200)
        access = get_user_access(user["id"])
        self.assertFalse(access["can_edit_any"])
        self.assertEqual(access["role"], "student")

    def test_dropdown_is_visible_overlay_and_does_not_use_white_native_control(self):
        from pathlib import Path
        from reviewer_auth import grant_reviewer_access

        css = (ROOT / "static" / "css" / "language-review.css").read_text(encoding="utf-8")
        self.assertIn(".review-select-menu", css)
        self.assertIn("position: fixed", css)
        self.assertIn("z-index: 80", css)
        self.assertIn("color: #efd77e", css)
        js = (ROOT / "static" / "js" / "language-review.js").read_text(encoding="utf-8")
        self.assertIn('menu.style.position = "fixed"', js)
        self.assertNotRegex(js, r"REVIEWER_TOKEN|shared.secret|access_key")

        self._insert_user("dropdown_reviewer", "ReviewPass1", "student")
        grant_reviewer_access("dropdown_reviewer", "mah-meri", "academic", granted_by=1)
        self._login_as("dropdown_reviewer", "ReviewPass1")
        html = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        self.assertIn("review-select-value", html)
        self.assertIn("Needs verification", html)
        self.assertIn("Academically reviewed", html)
        self.assertIn('aria-haspopup="listbox"', html)
        self.assertNotRegex(
            html,
            r'<select name="status" onchange="this.form.submit()"',
        )

    def test_existing_auth_and_learner_pages_still_work(self):
        self._insert_user("student_user", "StudentPass1", "student")
        self._login_as("student_user", "StudentPass1")
        login = self.client.get("/login")
        self.assertEqual(login.status_code, 200)
        learner = self.client.get("/language/mah-meri")
        self.assertEqual(learner.status_code, 200)
        self.assertIn("Language Review", learner.get_data(as_text=True))
        dictionary = self.client.get("/dictionary")
        self.assertIn(dictionary.status_code, (200, 302))
        for key in ("mah-meri", "iban", "bidayuh", "kadazan-dusun"):
            resp = self.client.get(f"/language/{key}/review")
            self.assertEqual(resp.status_code, 200, key)
            self.assertIn("Language Review", resp.get_data(as_text=True))
            self.assertIn("Review Queue", resp.get_data(as_text=True))

    def test_student_sees_review_menu_and_stays_read_only(self):
        self._insert_user("student_user", "StudentPass1", "student")
        self._login_as("student_user", "StudentPass1")
        dash = self.client.get("/dashboard").get_data(as_text=True)
        self.assertIn('href="/review"', dash)
        self.assertRegex(dash, r">\s*Review\s*<")
        self.assertIn("id=\"navbar-user\"", dash)
        hub = self.client.get("/review")
        self.assertEqual(hub.status_code, 200)
        hub_html = hub.get_data(as_text=True)
        self.assertIn("read-only", hub_html.lower())
        self.assertIn("Open read-only review", hub_html)
        self.assertNotIn("Open Reviewer Management", hub_html)
        token = self._token("/language/mah-meri/review")
        vocab_id, _ = self._queue_vocab("mah-meri")
        mutate = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
                "note": "student must not save",
            },
        )
        self.assertEqual(mutate.status_code, 403)

    def test_reviewer_review_menu_goes_to_assigned_queue_only(self):
        from reviewer_auth import grant_reviewer_access

        self._insert_user("scoped_reviewer", "ReviewPass1", "student")
        grant_reviewer_access("scoped_reviewer", "mah-meri", "academic", granted_by=1)
        self._login_as("scoped_reviewer", "ReviewPass1")
        menu = self.client.get("/dashboard").get_data(as_text=True)
        self.assertIn('href="/review"', menu)
        resp = self.client.get("/review", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        location = resp.headers.get("Location", "")
        self.assertIn("/language/mah-meri/review", location)
        self.assertIn("queue", location)
        token = self._token("/language/mah-meri/review")
        other_id, _ = self._queue_vocab("iban")
        blocked = self.client.post(
            "/language/iban/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(other_id),
                "status": "academically_reviewed",
                "note": "out of scope",
            },
        )
        self.assertEqual(blocked.status_code, 403)

    def test_admin_review_hub_and_env_username_can_mutate(self):
        self._insert_user("owner_account", "OwnerPass1", "student")
        os.environ["ADMIN_USERNAMES"] = '"owner_account"'
        try:
            from reviewer_auth import admin_usernames_from_env, get_user_access
            from db import get_db

            self.assertIn("owner_account", admin_usernames_from_env())
            self._login_as("owner_account", "OwnerPass1")
            dash = self.client.get("/dashboard").get_data(as_text=True)
            self.assertIn('href="/review"', dash)
            self.assertRegex(dash, r">\s*Review\s*<")
            self.assertIn("Reviewer Management", dash)
            hub = self.client.get("/review")
            self.assertEqual(hub.status_code, 200)
            html = hub.get_data(as_text=True)
            self.assertIn("Review Queue", html)
            self.assertIn("Reviewer Management", html)
            self.assertIn("Mah Meri", html)
            conn = get_db()
            user = conn.execute(
                "SELECT id, role FROM users WHERE username = ?",
                ("owner_account",),
            ).fetchone()
            conn.close()
            access = get_user_access(user["id"])
            self.assertTrue(access["is_admin"])
            self.assertEqual(access["role"], "admin")
            token = self._token("/language/mah-meri/review")
            vocab_id, _ = self._queue_vocab("mah-meri")
            saved = self.client.post(
                "/language/mah-meri/review/vocabulary",
                data={
                    "csrf_token": token,
                    "vocab_id": str(vocab_id),
                    "status": "academically_reviewed",
                    "note": "admin queue edit",
                },
                follow_redirects=False,
            )
            self.assertEqual(saved.status_code, 302)
        finally:
            os.environ.pop("ADMIN_USERNAMES", None)

    def test_logout_still_works_and_review_requires_login(self):
        self._insert_user("student_user", "StudentPass1", "student")
        self._login_as("student_user", "StudentPass1")
        out = self.client.get("/logout", follow_redirects=False)
        self.assertIn(out.status_code, (302, 303))
        review = self.client.get("/review", follow_redirects=False)
        self.assertEqual(review.status_code, 302)
        self.assertIn("/login", review.headers.get("Location", ""))




if __name__ == "__main__":
    unittest.main()
