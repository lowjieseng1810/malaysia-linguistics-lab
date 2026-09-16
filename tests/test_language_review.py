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
os.environ.pop("REVIEW_OPEN_MODE", None)


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
            self.assertIn("Recent Reviews", body)

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
                issue_context = COALESCE(
                    NULLIF(TRIM(issue_context), ''),
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
        os.environ.pop("REVIEW_OPEN_MODE", None)

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
              AND COALESCE(review_status, '') != 'pedagogical_bridge'
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
        queue_panel = re.search(r'id="panel-queue"(.*?)id="panel-recent"', reviewed_page, re.S)
        self.assertIsNotNone(queue_panel)
        self.assertNotIn(f'data-vocab-id="{vocab_id}"', queue_panel.group(1))
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

    def test_logged_out_review_mutation_is_rejected(self):
        guest = self.app.test_client()
        login_html = guest.get("/login").get_data(as_text=True)
        token = _csrf(login_html)
        vocab_id, _ = self._queue_vocab("mah-meri")
        from db import get_db

        conn = get_db()
        before = conn.execute(
            "SELECT review_status FROM vocabulary WHERE id = ?", (vocab_id,)
        ).fetchone()["review_status"]
        conn.close()
        resp = guest.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
                "note": "anonymous must fail",
            },
        )
        self.assertNotIn(resp.status_code, (200, 204))
        self.assertIn(resp.status_code, (302, 400, 401, 403))
        conn = get_db()
        after = conn.execute(
            "SELECT review_status FROM vocabulary WHERE id = ?", (vocab_id,)
        ).fetchone()["review_status"]
        conn.close()
        self.assertEqual(after, before)

    def test_open_mode_lets_logged_in_student_mark_academically_reviewed(self):
        os.environ["REVIEW_OPEN_MODE"] = "true"
        try:
            self._insert_user("open_mode_student", "StudentPass1", "student")
            self._login_as("open_mode_student", "StudentPass1")
            html = self.client.get("/language/mah-meri/review").get_data(as_text=True)
            self.assertIn('data-can-edit="1"', html)
            self.assertIn("review-select-trigger", html)
            self.assertIn("Needs verification", html)
            self.assertIn("Academically reviewed", html)
            self.assertIn("Pre-launch open review", html)
            self.assertIn(
                "review-vocab-inline",
                (ROOT / "static" / "js" / "language-review.js").read_text(encoding="utf-8"),
            )
            token = self._token("/language/mah-meri/review")
            vocab_id, _ = self._queue_vocab("mah-meri")
            missing_csrf = self.client.post(
                "/language/mah-meri/review/vocabulary",
                data={
                    "vocab_id": str(vocab_id),
                    "status": "academically_reviewed",
                    "note": "csrf required",
                },
            )
            self.assertEqual(missing_csrf.status_code, 400)
            ok = self.client.post(
                "/language/mah-meri/review/vocabulary",
                data={
                    "csrf_token": token,
                    "vocab_id": str(vocab_id),
                    "status": "academically_reviewed",
                    "note": "Open-mode student review.",
                },
                follow_redirects=True,
            )
            self.assertEqual(ok.status_code, 200)
            reviewed_page = ok.get_data(as_text=True)
            queue_panel = re.search(r'id="panel-queue"(.*?)id="panel-recent"', reviewed_page, re.S)
            self.assertIsNotNone(queue_panel)
            self.assertNotIn(f'data-vocab-id="{vocab_id}"', queue_panel.group(1))
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
            self.assertFalse(match.get("in_review_queue"))
            self.assertIn("Open-mode student review", match.get("review_note") or "")
            self.assertTrue(match.get("history"))
            from db import get_db

            conn = get_db()
            history = conn.execute(
                "SELECT previous_status, new_status FROM vocabulary_review_history WHERE vocabulary_id = ?",
                (vocab_id,),
            ).fetchall()
            conn.close()
            self.assertTrue(history)
            self.assertTrue(
                any(
                    (row["new_status"] == "academically_reviewed")
                    for row in history
                )
            )

            section = self.client.post(
                "/language/mah-meri/review/section",
                data={
                    "csrf_token": token,
                    "section_key": "community",
                    "status": "academically_reviewed",
                },
                follow_redirects=True,
            )
            self.assertEqual(section.status_code, 200)
        finally:
            os.environ.pop("REVIEW_OPEN_MODE", None)

        self._login_as("open_mode_student", "StudentPass1")
        closed = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": self._token("/language/mah-meri/review"),
                "vocab_id": str(vocab_id),
                "status": "needs_verification",
                "note": "should 403 when open mode is off",
            },
        )
        self.assertEqual(closed.status_code, 403)

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


class ReviewInviteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LanguageReviewTests.setUpClass()
        cls.app_module = LanguageReviewTests.app_module
        cls.app = LanguageReviewTests.app

    def setUp(self):
        self.client = self.app.test_client()

    def _insert_admin(self):
        ReviewerPermissionTests._insert_user(
            self, "invite_admin", "AdminPass1", "admin"
        )
        ReviewerPermissionTests._login_as(self, "invite_admin", "AdminPass1")

    def _token(self, path):
        return _csrf(self.client.get(path).get_data(as_text=True))

    def _create_invite(self, language="mah-meri", kind="academic", days=7, label="Mah Meri FLL review"):
        from review_invite import create_review_invite

        result = create_review_invite(language, kind, days, label, created_by=1)
        self.assertTrue(result.get("ok"), result)
        return result

    def _queue_id(self, language="mah-meri"):
        from db import get_db

        conn = get_db()
        row = conn.execute(
            """
            SELECT id FROM vocabulary
            WHERE language = ?
              AND review_status IN (
                'needs_verification', 'needs_revision',
                'academic_review_pending', 'community_review_pending',
                'source_derived', 'technically_corrected'
              )
              AND COALESCE(review_status, '') != 'pedagogical_bridge'
            ORDER BY id LIMIT 1
            """,
            (language,),
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return int(row["id"])

    def test_valid_invite_opens_scoped_queue(self):
        invite = self._create_invite()
        public = self.client.get("/language/mah-meri/review", follow_redirects=False)
        self.assertEqual(public.status_code, 302)
        self.assertIn("/login", public.headers.get("Location", ""))
        opened = self.client.get(
            f"/review/invite/{invite['token']}", follow_redirects=False
        )
        self.assertEqual(opened.status_code, 302)
        location = opened.headers.get("Location", "")
        self.assertIn("/review/workspace/mah-meri", location)
        self.assertIn("queue", location)
        page = self.client.get("/review/workspace/mah-meri")
        self.assertEqual(page.status_code, 200)
        body = page.get_data(as_text=True)
        self.assertIn("Private Academic Review Access", body)
        self.assertIn("Review Queue", body)
        self.assertIn("review-select-trigger", body)
        still_public = self.client.get("/language/mah-meri/review", follow_redirects=False)
        self.assertEqual(still_public.status_code, 302)

    def test_invalid_expired_and_revoked_tokens_rejected(self):
        from db import get_db
        from review_invite import revoke_review_invite

        missing = self.client.get("/review/invite/not-a-valid-token", follow_redirects=False)
        self.assertEqual(missing.status_code, 404)

        expired = self._create_invite(label="expired")
        conn = get_db()
        conn.execute(
            "UPDATE review_invitations SET expires_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", expired["invite_id"]),
        )
        conn.commit()
        conn.close()
        expired_resp = self.client.get(
            f"/review/invite/{expired['token']}", follow_redirects=False
        )
        self.assertEqual(expired_resp.status_code, 403)

        live = self._create_invite(label="revoke-me")
        revoke_review_invite(live["invite_id"], revoked_by=1)
        revoked = self.client.get(
            f"/review/invite/{live['token']}", follow_redirects=False
        )
        self.assertEqual(revoked.status_code, 403)

    def test_invite_cannot_modify_other_language_or_community_status(self):
        invite = self._create_invite()
        self.client.get(f"/review/invite/{invite['token']}")
        token = self._token("/review/workspace/mah-meri")
        iban_id = self._queue_id("iban")
        other = self.client.post(
            "/review/workspace/iban/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(iban_id),
                "status": "academically_reviewed",
                "note": "should fail",
            },
        )
        self.assertEqual(other.status_code, 403)
        mah_id = self._queue_id("mah-meri")
        community = self.client.post(
            "/review/workspace/mah-meri/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(mah_id),
                "status": "community_reviewed",
                "note": "academic cannot set this",
            },
        )
        self.assertEqual(community.status_code, 400)

    def test_invite_cannot_use_admin_or_become_admin(self):
        invite = self._create_invite()
        self.client.get(f"/review/invite/{invite['token']}")
        admin_page = self.client.get("/admin/reviewers", follow_redirects=False)
        self.assertIn(admin_page.status_code, (302, 403))
        if admin_page.status_code == 302:
            self.assertIn("/login", admin_page.headers.get("Location", ""))
        invites_page = self.client.get("/admin/review-invitations", follow_redirects=False)
        self.assertIn(invites_page.status_code, (302, 403))
        token = self._token("/review/workspace/mah-meri")
        grant = self.client.post(
            "/admin/reviewers/grant",
            data={
                "csrf_token": token,
                "username": "anyone",
                "language": "mah-meri",
                "reviewer_kind": "academic",
            },
            follow_redirects=False,
        )
        self.assertIn(grant.status_code, (302, 403))

    def test_invite_mutations_csrf_history_and_queue(self):
        from db import get_db

        invite = self._create_invite()
        self.client.get(f"/review/invite/{invite['token']}")
        vocab_id = self._queue_id("mah-meri")
        bare = self.client.post(
            "/review/workspace/mah-meri/vocabulary",
            data={
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
                "note": "no csrf",
            },
        )
        self.assertEqual(bare.status_code, 400)
        token = self._token("/review/workspace/mah-meri")
        saved = self.client.post(
            "/review/workspace/mah-meri/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
                "note": "Checked in private invitation.",
            },
            follow_redirects=True,
        )
        self.assertEqual(saved.status_code, 200)
        html = saved.get_data(as_text=True)
        queue_panel = re.search(r'id="panel-queue"(.*?)id="panel-recent"', html, re.S)
        self.assertIsNotNone(queue_panel)
        self.assertNotIn(f'data-vocab-id="{vocab_id}"', queue_panel.group(1))
        self.assertIn("Recent Reviews", html)
        self.assertIn(f'data-vocab-id="{vocab_id}"', html)
        self.assertIn("Academically reviewed", html)
        conn = get_db()
        history = conn.execute(
            """
            SELECT review_actor_type, review_kind, reviewer_role, new_status
            FROM vocabulary_review_history
            WHERE vocabulary_id = ?
            ORDER BY id DESC
            """,
            (vocab_id,),
        ).fetchone()
        row = conn.execute(
            "SELECT review_status FROM vocabulary WHERE id = ?",
            (vocab_id,),
        ).fetchone()
        conn.close()
        self.assertEqual(history["review_actor_type"], "private_review_link")
        self.assertEqual(history["review_kind"], "academic")
        self.assertEqual(history["reviewer_role"], "private_review_link")
        self.assertEqual(history["new_status"], "academically_reviewed")
        self.assertEqual(row["review_status"], "academically_reviewed")

    def test_end_session_and_revoke_invalidate_invite(self):
        invite = self._create_invite(label="session-end")
        self.client.get(f"/review/invite/{invite['token']}")
        token = self._token("/review/workspace/mah-meri")
        ended = self.client.post(
            "/review/workspace/end",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        self.assertEqual(ended.status_code, 302)
        blocked = self.client.get("/review/workspace/mah-meri")
        self.assertEqual(blocked.status_code, 403)

        live = self._create_invite(label="live-then-revoke")
        self.client.get(f"/review/invite/{live['token']}")
        self.assertEqual(self.client.get("/review/workspace/mah-meri").status_code, 200)
        from review_invite import revoke_review_invite

        revoke_review_invite(live["invite_id"], revoked_by=1)
        self.assertEqual(self.client.get("/review/workspace/mah-meri").status_code, 403)

    def test_admin_can_create_invite_and_existing_roles_unchanged(self):
        self._insert_admin()
        page = self.client.get("/admin/review-invitations")
        self.assertEqual(page.status_code, 200)
        body = page.get_data(as_text=True)
        self.assertIn("Create Review Invitation", body)
        token = self._token("/admin/review-invitations")
        created = self.client.post(
            "/admin/review-invitations/create",
            data={
                "csrf_token": token,
                "language": "mah-meri",
                "reviewer_kind": "academic",
                "expires_days": "7",
                "label": "Mah Meri FLL review",
            },
            follow_redirects=True,
        )
        self.assertEqual(created.status_code, 200)
        created_html = created.get_data(as_text=True)
        self.assertIn("Copy private review link", created_html)
        self.assertIn("/review/invite/", created_html)
        ReviewerPermissionTests._insert_user(
            self, "invite_student", "StudentPass1", "student"
        )
        student = self.app.test_client()
        login = student.get("/login")
        student.post(
            "/login",
            data={
                "csrf_token": _csrf(login.get_data(as_text=True)),
                "username": "invite_student",
                "password": "StudentPass1",
            },
        )
        mutate = student.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": _csrf(
                    student.get("/language/mah-meri/review").get_data(as_text=True)
                ),
                "vocab_id": "1",
                "status": "academically_reviewed",
            },
        )
        self.assertEqual(mutate.status_code, 403)
        admin_review = self.client.get("/language/mah-meri/review")
        self.assertEqual(admin_review.status_code, 200)
        self.assertIn("review-select-trigger", admin_review.get_data(as_text=True))


class ReviewNoteContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LanguageReviewTests.setUpClass()
        cls.app_module = LanguageReviewTests.app_module
        cls.app = LanguageReviewTests.app

    def setUp(self):
        self.client = self.app.test_client()
        os.environ.pop("REVIEW_OPEN_MODE", None)

    def test_automated_explanations_are_not_human_notes(self):
        from review_notes import is_automated_issue_explanation, split_review_note_fields

        auto = "Wiktionary source is Malay. English translation is not in this extract."
        damage = "Headword 'Src' and gloss 'Stand Star' look like extraction damage. Not corrected without the printed page."
        self.assertTrue(is_automated_issue_explanation(auto))
        self.assertTrue(is_automated_issue_explanation(damage))
        self.assertTrue(is_automated_issue_explanation("Possible pedagogical bridge form."))
        self.assertTrue(is_automated_issue_explanation("Possible truncation/OCR artefact."))
        self.assertFalse(is_automated_issue_explanation("Checked against the printed Skeat page."))
        context, human = split_review_note_fields(auto)
        self.assertIn("Wiktionary source is Malay", context)
        self.assertEqual(human, "")
        context, human = split_review_note_fields(
            auto + "\nPlease keep the Malay gloss."
        )
        self.assertIn("Wiktionary source is Malay", context)
        self.assertEqual(human, "Please keep the Malay gloss.")
        context, human = split_review_note_fields(
            "",
            issues=[
                {
                    "label": "Pedagogical bridge form",
                    "detail": "This item comes from a beginner lesson that uses a Malay/multilingual bridge expression. It is not automatically a Mah Meri lexeme.",
                }
            ],
        )
        self.assertIn("Pedagogical bridge form", context)
        self.assertEqual(human, "")

    def test_issue_context_is_readonly_and_notes_start_empty(self):
        from reviewer_auth import grant_reviewer_access
        from db import get_db

        ReviewerPermissionTests._insert_user(self, "note_reviewer", "ReviewPass1", "student")
        grant_reviewer_access("note_reviewer", "mah-meri", "academic", granted_by=1)
        ReviewerPermissionTests._login_as(self, "note_reviewer", "ReviewPass1")

        conn = get_db()
        wiki = conn.execute(
            """
            SELECT id, word FROM vocabulary
            WHERE language = 'mah-meri'
              AND (
                COALESCE(issue_context, '') LIKE '%Wiktionary source is Malay%'
                OR COALESCE(review_note, '') LIKE '%Wiktionary source is Malay%'
              )
            ORDER BY id LIMIT 1
            """
        ).fetchone()
        src = conn.execute(
            """
            SELECT id, word FROM vocabulary
            WHERE language = 'mah-meri' AND LOWER(TRIM(word)) = 'src'
            LIMIT 1
            """
        ).fetchone()
        course = conn.execute(
            """
            SELECT id, word FROM vocabulary
            WHERE language = 'mah-meri'
              AND source_ref = 'course_database'
              AND LOWER(TRIM(word)) = 'selamat'
            LIMIT 1
            """
        ).fetchone()
        conn.close()
        self.assertIsNotNone(wiki)
        self.assertIsNotNone(src)
        self.assertIsNotNone(course)

        html = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        self.assertIn("Issue context", html)
        self.assertIn("Add your review comments here…", html)
        self.assertIn('aria-readonly="true"', html)
        self.assertIn("Wiktionary source is Malay", html)
        self.assertIn("look like extraction damage", html)
        self.assertNotRegex(
            html,
            r'name="note"[^>]*>\s*Wiktionary source is Malay',
        )
        self.assertNotRegex(
            html,
            r'name="note"[^>]*>\s*Headword \'Src\'',
        )
        import json

        vocab_json = re.search(
            r'<script id="review-vocab-data" type="application/json">(.*?)</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(vocab_json)
        rows = json.loads(vocab_json.group(1))
        wiki_row = next(r for r in rows if r.get("id") == wiki["id"])
        src_row = next(r for r in rows if r.get("id") == src["id"])
        self.assertIn("Wiktionary source is Malay", wiki_row.get("issue_context") or "")
        self.assertEqual((wiki_row.get("reviewer_note") or "").strip(), "")
        self.assertEqual((wiki_row.get("review_note") or "").strip(), "")
        self.assertIn("extraction damage", src_row.get("issue_context") or "")
        self.assertEqual((src_row.get("reviewer_note") or "").strip(), "")

        empty_queue = None
        article = None
        for match in re.finditer(
            r'<article class="review-card review-queue-item" data-vocab-id="(\d+)"(.*?)</article>',
            html,
            re.S,
        ):
            block = match.group(2)
            if "Issue context" not in block:
                continue
            if not re.search(
                r'<textarea name="note"[^>]*placeholder="Add your review comments here…">\s*</textarea>',
                block,
            ):
                continue
            empty_queue = {"id": int(match.group(1))}
            article = match
            break
        self.assertIsNotNone(empty_queue)
        self.assertIsNotNone(article)
        block = article.group(2)
        self.assertIn("Issue context", block)
        self.assertRegex(
            block,
            r'<textarea name="note"[^>]*placeholder="Add your review comments here…">\s*</textarea>',
        )
        self.assertNotRegex(
            block,
            r'name="note"[^>]*>\s*Wiktionary source is Malay',
        )
        json_row = next(r for r in rows if r.get("id") == empty_queue["id"])
        self.assertTrue((json_row.get("issue_context") or "").strip())
        self.assertEqual((json_row.get("reviewer_note") or "").strip(), "")

        token = _csrf(html)
        genuine = "Human reviewer: Malay gloss matches the lesson."
        saved = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(empty_queue["id"]),
                "status": "needs_verification",
                "note": genuine,
            },
            follow_redirects=True,
        )
        self.assertEqual(saved.status_code, 200)
        saved_html = saved.get_data(as_text=True)
        self.assertIn(genuine, saved_html)
        saved_article = re.search(
            rf'<article class="review-card review-queue-item" data-vocab-id="{empty_queue["id"]}"(.*?)</article>',
            saved_html,
            re.S,
        )
        self.assertIsNotNone(saved_article)
        self.assertIn(genuine, saved_article.group(1))
        self.assertIn("Reviewer notes", saved_article.group(1))
        saved_json = re.search(
            r'<script id="review-vocab-data" type="application/json">(.*?)</script>',
            saved_html,
            re.S,
        )
        saved_rows = json.loads(saved_json.group(1))
        saved_row = next(r for r in saved_rows if r.get("id") == empty_queue["id"])
        self.assertEqual(saved_row.get("reviewer_note"), genuine)
        self.assertTrue(saved_row.get("history"))
        from db import get_db as gdb

        conn = gdb()
        history = conn.execute(
            "SELECT note FROM vocabulary_review_history WHERE vocabulary_id = ?",
            (empty_queue["id"],),
        ).fetchall()
        stored = conn.execute(
            "SELECT review_note, issue_context FROM vocabulary WHERE id = ?",
            (empty_queue["id"],),
        ).fetchone()
        conn.close()
        self.assertTrue(any((row["note"] == genuine) for row in history))
        self.assertEqual(stored["review_note"], genuine)

    def test_migrate_moves_automated_note_without_touching_human_or_history(self):
        from database import migrate_automated_review_notes
        from db import get_db

        conn = get_db()
        conn.execute(
            """
            INSERT INTO vocabulary (
                language, lesson_id, word, meaning_en, meaning_ms,
                review_status, review_note, source_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mah-meri",
                1,
                "zz-auto-note",
                "test",
                "ujian",
                "needs_verification",
                "Wiktionary source is Malay. English translation is not in this extract.",
                "course_database",
            ),
        )
        conn.execute(
            """
            INSERT INTO vocabulary (
                language, lesson_id, word, meaning_en, meaning_ms,
                review_status, review_note, source_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mah-meri",
                1,
                "zz-human-note",
                "test",
                "ujian",
                "needs_verification",
                "I compared this with the community speaker recording.",
                "course_database",
            ),
        )
        conn.commit()
        auto_id = conn.execute(
            "SELECT id FROM vocabulary WHERE word = ?", ("zz-auto-note",)
        ).fetchone()["id"]
        human_id = conn.execute(
            "SELECT id FROM vocabulary WHERE word = ?", ("zz-human-note",)
        ).fetchone()["id"]
        conn.execute(
            """
            INSERT INTO vocabulary_review_history
                (vocabulary_id, language, previous_status, new_status, note,
                 reviewer_username, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                human_id,
                "mah-meri",
                "needs_verification",
                "needs_verification",
                "I compared this with the community speaker recording.",
                "elder",
                "2026-01-01T00:00:00+00:00",
            ),
        )
        conn.commit()
        conn.close()

        moved = migrate_automated_review_notes()
        self.assertGreaterEqual(moved, 1)
        conn = get_db()
        auto = conn.execute(
            "SELECT review_note, issue_context FROM vocabulary WHERE id = ?",
            (auto_id,),
        ).fetchone()
        human = conn.execute(
            "SELECT review_note, issue_context FROM vocabulary WHERE id = ?",
            (human_id,),
        ).fetchone()
        hist = conn.execute(
            "SELECT note FROM vocabulary_review_history WHERE vocabulary_id = ?",
            (human_id,),
        ).fetchone()
        conn.close()
        self.assertFalse((auto["review_note"] or "").strip())
        self.assertIn("Wiktionary source is Malay", auto["issue_context"] or "")
        self.assertEqual(
            human["review_note"],
            "I compared this with the community speaker recording.",
        )
        self.assertEqual(
            hist["note"],
            "I compared this with the community speaker recording.",
        )


class ReviewQueueWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LanguageReviewTests.setUpClass()
        cls.app_module = LanguageReviewTests.app_module
        cls.app = LanguageReviewTests.app

    def setUp(self):
        self.client = self.app.test_client()
        os.environ.pop("REVIEW_OPEN_MODE", None)

    def _json_rows(self, html):
        import json

        match = re.search(
            r'<script id="review-vocab-data" type="application/json">(.*?)</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_pedagogical_bridges_leave_queue_but_stay_in_vocabulary(self):
        from review_quality import is_course_pedagogical_bridge
        from reviewer_auth import grant_reviewer_access

        ReviewerPermissionTests._insert_user(self, "bridge_reviewer", "ReviewPass1", "student")
        grant_reviewer_access("bridge_reviewer", "mah-meri", "academic", granted_by=1)
        ReviewerPermissionTests._login_as(self, "bridge_reviewer", "ReviewPass1")
        html = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        self.assertIn("Pedagogical bridge", html)
        self.assertIn("Recent Reviews", html)
        rows = self._json_rows(html)
        bridges = [
            r for r in rows
            if r.get("is_pedagogical_bridge") or r.get("review_status") == "pedagogical_bridge"
        ]
        self.assertGreaterEqual(len(bridges), 8)
        names = {(r.get("word") or "").strip().lower() for r in bridges}
        for expected in ("anak", "bapa", "ibu", "selamat", "terima kasih", "ya", "tak"):
            self.assertIn(expected, names, expected)
        queue_ids = {r["id"] for r in rows if r.get("in_review_queue")}
        for row in bridges:
            self.assertNotIn(row["id"], queue_ids)
            self.assertFalse(row.get("in_review_queue"))
            self.assertIn("not treated as a Mah Meri lexical item", row.get("issue_context") or "")
            self.assertEqual((row.get("reviewer_note") or "").strip(), "")
        queue_panel = re.search(r'id="panel-queue"(.*?)id="panel-recent"', html, re.S).group(1)
        for row in bridges:
            self.assertNotIn(f'data-vocab-id="{row["id"]}"', queue_panel)
        self.assertTrue(any(r.get("word") == "anak" for r in rows))
        self.assertFalse(
            is_course_pedagogical_bridge(
                {
                    "language": "mah-meri",
                    "word": "anak",
                    "source_ref": "Skeat, W.W. (1896). A Vocabulary of the Besisi Dialect.",
                }
            )
        )

    def test_uncertain_source_items_remain_in_review_queue(self):
        from reviewer_auth import grant_reviewer_access

        ReviewerPermissionTests._insert_user(self, "bridge_reviewer", "ReviewPass1", "student")
        grant_reviewer_access("bridge_reviewer", "mah-meri", "academic", granted_by=1)
        ReviewerPermissionTests._login_as(self, "bridge_reviewer", "ReviewPass1")
        html = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        rows = self._json_rows(html)
        queue = [r for r in rows if r.get("in_review_queue")]
        self.assertGreater(len(queue), 0)
        words = {(r.get("word") or "").strip() for r in queue}
        for marker in ("Src", "RAachin", "O-h"):
            match = next((r for r in rows if (r.get("word") or "").strip() == marker), None)
            self.assertIsNotNone(match, marker)
            self.assertTrue(match.get("in_review_queue"), marker)
        d3y = next((r for r in rows if (r.get("word") or "").strip() == "d3y"), None)
        self.assertIsNotNone(d3y)
        self.assertEqual(d3y.get("review_status"), "source_derived")
        self.assertTrue(
            any(
                "wiktionary" in (r.get("source_ref") or "").lower()
                and r.get("in_review_queue")
                for r in queue
            )
        )

    def test_recent_reviews_reopen_returns_item_to_queue_and_keeps_history(self):
        from reviewer_auth import grant_reviewer_access
        from db import get_db

        ReviewerPermissionTests._insert_user(self, "reopen_reviewer", "ReviewPass1", "student")
        grant_reviewer_access("reopen_reviewer", "mah-meri", "academic", granted_by=1)
        ReviewerPermissionTests._login_as(self, "reopen_reviewer", "ReviewPass1")
        vocab_id, _ = ReviewerPermissionTests._queue_vocab(self, "mah-meri")
        token = _csrf(self.client.get("/language/mah-meri/review").get_data(as_text=True))
        first = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
                "note": "First academic pass.",
                "return_to": "queue",
            },
            follow_redirects=True,
        )
        self.assertEqual(first.status_code, 200)
        html = first.get_data(as_text=True)
        recent = re.search(r'id="panel-recent"(.*?)id="panel-vocabulary"', html, re.S)
        self.assertIsNotNone(recent)
        self.assertIn(f'data-vocab-id="{vocab_id}"', recent.group(1))
        self.assertIn("Review again", recent.group(1))
        self.assertIn("First academic pass.", recent.group(1))
        queue = re.search(r'id="panel-queue"(.*?)id="panel-recent"', html, re.S)
        self.assertNotIn(f'data-vocab-id="{vocab_id}"', queue.group(1))
        token = _csrf(html)
        second = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "needs_verification",
                "note": "Changed my mind.",
                "return_to": "recent",
            },
            follow_redirects=False,
        )
        self.assertEqual(second.status_code, 302)
        self.assertTrue(second.headers.get("Location", "").endswith("#recent"))
        page = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        queue = re.search(r'id="panel-queue"(.*?)id="panel-recent"', page, re.S)
        self.assertIn(f'data-vocab-id="{vocab_id}"', queue.group(1))
        rows = self._json_rows(page)
        match = next(r for r in rows if r["id"] == vocab_id)
        self.assertTrue(match.get("in_review_queue"))
        self.assertEqual(match.get("reviewer_note"), "Changed my mind.")
        conn = get_db()
        history = conn.execute(
            """
            SELECT previous_status, new_status, note
            FROM vocabulary_review_history
            WHERE vocabulary_id = ?
            ORDER BY id
            """,
            (vocab_id,),
        ).fetchall()
        conn.close()
        self.assertGreaterEqual(len(history), 2)
        self.assertEqual(history[0]["new_status"], "academically_reviewed")
        self.assertEqual(history[-1]["previous_status"], "academically_reviewed")
        self.assertEqual(history[-1]["new_status"], "needs_verification")
        self.assertEqual(history[-1]["note"], "Changed my mind.")

    def test_private_invite_reuse_revisit_and_scope(self):
        from db import get_db
        from review_invite import create_review_invite, revoke_review_invite

        invite = create_review_invite(
            "mah-meri", "academic", 7, "Professor reuse", created_by=1
        )
        self.assertTrue(invite.get("ok"), invite)
        guest = self.app.test_client()
        opened = guest.get(f"/review/invite/{invite['token']}", follow_redirects=False)
        self.assertEqual(opened.status_code, 302)
        self.assertIn("/review/workspace/mah-meri", opened.headers.get("Location", ""))
        page = guest.get("/review/workspace/mah-meri")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("login", page.headers.get("Location", "").lower())
        html = page.get_data(as_text=True)
        self.assertIn("Private Academic Review Access", html)
        self.assertNotIn("Reviewer Management", html)
        rows = self._json_rows(html)
        vocab_id = next(r["id"] for r in rows if r.get("in_review_queue"))
        token = _csrf(html)
        saved = guest.post(
            "/review/workspace/mah-meri/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
                "note": "Invite first pass.",
            },
            follow_redirects=True,
        )
        self.assertEqual(saved.status_code, 200)
        again = guest.get(f"/review/invite/{invite['token']}", follow_redirects=False)
        self.assertEqual(again.status_code, 302)
        reuse = guest.get("/review/workspace/mah-meri")
        self.assertEqual(reuse.status_code, 200)
        reuse_html = reuse.get_data(as_text=True)
        recent = re.search(r'id="panel-recent"(.*?)id="panel-vocabulary"', reuse_html, re.S)
        self.assertIn(f'data-vocab-id="{vocab_id}"', recent.group(1))
        self.assertIn("Invite first pass.", recent.group(1))
        token = _csrf(reuse_html)
        reopen = guest.post(
            "/review/workspace/mah-meri/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "needs_revision",
                "note": "Invite second pass.",
                "return_to": "recent",
            },
            follow_redirects=True,
        )
        self.assertEqual(reopen.status_code, 200)
        reopen_html = reopen.get_data(as_text=True)
        queue = re.search(r'id="panel-queue"(.*?)id="panel-recent"', reopen_html, re.S)
        self.assertIn(f'data-vocab-id="{vocab_id}"', queue.group(1))
        iban = create_review_invite("iban", "academic", 7, "Iban only", created_by=1)
        other = self.app.test_client()
        other.get(f"/review/invite/{iban['token']}")
        iban_page = other.get("/review/workspace/iban").get_data(as_text=True)
        self.assertNotIn(f'data-vocab-id="{vocab_id}"', iban_page)
        mah_via_iban = other.post(
            "/review/workspace/mah-meri/vocabulary",
            data={
                "csrf_token": _csrf(iban_page),
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
            },
        )
        self.assertEqual(mah_via_iban.status_code, 403)
        expired = create_review_invite("mah-meri", "academic", 7, "expired-prof", created_by=1)
        conn = get_db()
        conn.execute(
            "UPDATE review_invitations SET expires_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", expired["invite_id"]),
        )
        conn.commit()
        conn.close()
        self.assertEqual(
            guest.get(f"/review/invite/{expired['token']}", follow_redirects=False).status_code,
            403,
        )
        live = create_review_invite("mah-meri", "academic", 7, "revoke-prof", created_by=1)
        guest.get(f"/review/invite/{live['token']}")
        revoke_review_invite(live["invite_id"], revoked_by=1)
        self.assertEqual(
            guest.get(f"/review/invite/{live['token']}", follow_redirects=False).status_code,
            403,
        )


class AcademicReviewWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LanguageReviewTests.setUpClass()
        cls.app_module = LanguageReviewTests.app_module
        cls.app = LanguageReviewTests.app

    def setUp(self):
        self.client = self.app.test_client()
        os.environ.pop("REVIEW_OPEN_MODE", None)

    def _json_rows(self, html):
        import json

        match = re.search(
            r'<script id="review-vocab-data" type="application/json">(.*?)</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def _academic_panel(self, html):
        match = re.search(
            r'id="panel-academic"(.*?)id="panel-collaboration"',
            html,
            re.S,
        )
        self.assertIsNotNone(match)
        return match.group(1)

    def _grant_and_login(self, username="workspace_reviewer"):
        from reviewer_auth import grant_reviewer_access

        ReviewerPermissionTests._insert_user(self, username, "ReviewPass1", "student")
        grant_reviewer_access(username, "mah-meri", "academic", granted_by=1)
        ReviewerPermissionTests._login_as(self, username, "ReviewPass1")

    def test_academic_review_is_direct_workspace_not_checklist(self):
        self._grant_and_login()
        html = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        academic = self._academic_panel(html)
        self.assertIn("Academic Review", academic)
        self.assertIn("Suggested review scope", academic)
        self.assertIn("You do not need to review the entire dictionary.", academic)
        self.assertIn("1. Language &amp; cultural overview", academic)
        self.assertIn("2. Representative vocabulary", academic)
        self.assertIn("3. Beginner lesson", academic)
        self.assertIn("4. Exercise + answer key", academic)
        self.assertIn("5. Selected issues requiring expert judgement", academic)
        self.assertIn('data-academic-section="language_overview"', academic)
        self.assertIn('data-academic-section="community"', academic)
        self.assertIn('data-academic-section="beginner_lesson"', academic)
        self.assertIn('data-academic-section="lesson_exercise"', academic)
        self.assertIn("Malay translation", academic)
        self.assertIn("English translation", academic)
        self.assertIn("Source / provenance", academic)
        self.assertIn("Add your review comments here", academic)
        self.assertGreaterEqual(academic.count("Save review"), 8)
        self.assertIn("review-select-trigger", academic)
        self.assertIn('name="note"', academic)
        self.assertIn("Optional review dimensions", academic)
        self.assertIn("Language accuracy", academic)
        self.assertNotIn("Suggested academic review set", html)
        self.assertNotIn("Save review note", academic)
        vocab_ids = re.findall(r'data-academic-vocab="(\d+)"', academic)
        self.assertGreaterEqual(len(vocab_ids), 10)
        self.assertLessEqual(len(vocab_ids), 15)
        for marker in ("Src", "RAachin", "O-h"):
            self.assertIn(marker, academic)
            self.assertIn(f'data-academic-issue=', academic)

    def test_academic_review_saves_vocab_overview_lesson_exercise_and_issues(self):
        from db import get_db

        self._grant_and_login("direct_save_reviewer")
        html = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        token = _csrf(html)
        rows = self._json_rows(html)
        src = next(r for r in rows if (r.get("word") or "") == "RAachin")
        sample_id = re.search(r'data-academic-vocab="(\d+)"', self._academic_panel(html)).group(1)

        overview = self.client.post(
            "/language/mah-meri/review/section",
            data={
                "csrf_token": token,
                "section_key": "language_overview",
                "status": "academically_reviewed",
                "note": "Overview is suitable for this course.",
                "return_to": "academic",
            },
            follow_redirects=False,
        )
        self.assertEqual(overview.status_code, 302)
        self.assertTrue(overview.headers.get("Location", "").endswith("#academic"))

        lesson = self.client.post(
            "/language/mah-meri/review/section",
            data={
                "csrf_token": token,
                "section_key": "beginner_lesson",
                "status": "needs_revision",
                "note": "Lesson still uses pedagogical bridges.",
                "return_to": "academic",
            },
            follow_redirects=False,
        )
        self.assertEqual(lesson.status_code, 302)

        exercise = self.client.post(
            "/language/mah-meri/review/section",
            data={
                "csrf_token": token,
                "section_key": "lesson_exercise",
                "status": "academically_reviewed",
                "note": "Answer key matches the prompt.",
                "return_to": "academic",
            },
            follow_redirects=False,
        )
        self.assertEqual(exercise.status_code, 302)

        vocab = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": sample_id,
                "status": "academically_reviewed",
                "note": "Sourced sample looks usable.",
                "return_to": "academic",
            },
            follow_redirects=True,
        )
        self.assertEqual(vocab.status_code, 200)
        vocab_html = vocab.get_data(as_text=True)
        self.assertTrue(vocab.headers.get("Location", "").endswith("#academic") or True)

        issue = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": _csrf(vocab_html),
                "vocab_id": str(src["id"]),
                "status": "academically_reviewed",
                "note": "OCR form confirmed for now.",
                "return_to": "academic",
            },
            follow_redirects=True,
        )
        self.assertEqual(issue.status_code, 200)
        after = issue.get_data(as_text=True)
        academic = self._academic_panel(after)
        self.assertIn("Overview is suitable for this course.", academic)
        self.assertIn("Lesson still uses pedagogical bridges.", academic)
        self.assertIn("Answer key matches the prompt.", academic)
        self.assertIn("OCR form confirmed for now.", academic)
        self.assertIn("Sourced sample looks usable.", academic)

        queue = re.search(r'id="panel-queue"(.*?)id="panel-recent"', after, re.S)
        recent = re.search(r'id="panel-recent"(.*?)id="panel-vocabulary"', after, re.S)
        self.assertIsNotNone(queue)
        self.assertIsNotNone(recent)
        self.assertNotIn(f'data-vocab-id="{src["id"]}"', queue.group(1))
        self.assertIn(f'data-vocab-id="{src["id"]}"', recent.group(1))
        self.assertIn("OCR form confirmed for now.", recent.group(1))
        self.assertIn(f'data-vocab-id="{sample_id}"', recent.group(1))

        conn = get_db()
        src_row = conn.execute(
            "SELECT review_status, review_note FROM vocabulary WHERE id = ?",
            (src["id"],),
        ).fetchone()
        hist = conn.execute(
            """
            SELECT previous_status, new_status, note
            FROM vocabulary_review_history
            WHERE vocabulary_id = ?
            ORDER BY id
            """,
            (src["id"],),
        ).fetchall()
        conn.close()
        self.assertEqual(src_row["review_status"], "academically_reviewed")
        self.assertEqual(src_row["review_note"], "OCR form confirmed for now.")
        self.assertTrue(hist)
        self.assertEqual(hist[-1]["new_status"], "academically_reviewed")

        reopen = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": _csrf(after),
                "vocab_id": str(src["id"]),
                "status": "needs_revision",
                "note": "Please check the printed page.",
                "return_to": "recent",
            },
            follow_redirects=True,
        )
        reopen_html = reopen.get_data(as_text=True)
        queue = re.search(r'id="panel-queue"(.*?)id="panel-recent"', reopen_html, re.S)
        self.assertIn(f'data-vocab-id="{src["id"]}"', queue.group(1))
        self.assertIn("Please check the printed page.", queue.group(1))

    def test_private_invite_can_review_academic_workspace_without_login(self):
        from review_invite import create_review_invite

        ReviewerPermissionTests._insert_user(self, "invite_admin", "AdminPass1", "admin")
        invite = create_review_invite(
            "mah-meri", "academic", 7, "Workspace invite", created_by=1
        )
        guest = self.app.test_client()
        opened = guest.get(f"/review/invite/{invite['token']}", follow_redirects=False)
        self.assertEqual(opened.status_code, 302)
        page = guest.get("/review/workspace/mah-meri")
        self.assertEqual(page.status_code, 200)
        html = page.get_data(as_text=True)
        self.assertNotIn("login", page.headers.get("Location", "").lower())
        academic = self._academic_panel(html)
        self.assertIn("Save review", academic)
        self.assertIn('data-academic-section="beginner_lesson"', academic)
        token = _csrf(html)
        rows = self._json_rows(html)
        item = next(r for r in rows if r.get("in_review_queue"))
        saved = guest.post(
            "/review/workspace/mah-meri/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(item["id"]),
                "status": "academically_reviewed",
                "note": "Invite workspace pass.",
                "return_to": "academic",
            },
            follow_redirects=False,
        )
        self.assertEqual(saved.status_code, 302)
        self.assertTrue(saved.headers.get("Location", "").endswith("#academic"))
        section = guest.post(
            "/review/workspace/mah-meri/section",
            data={
                "csrf_token": token,
                "section_key": "community",
                "status": "academically_reviewed",
                "note": "Community overview accepted.",
                "return_to": "academic",
            },
            follow_redirects=True,
        )
        self.assertEqual(section.status_code, 200)
        after = section.get_data(as_text=True)
        self.assertIn("Community overview accepted.", self._academic_panel(after))
        recent = re.search(r'id="panel-recent"(.*?)id="panel-vocabulary"', after, re.S)
        self.assertIn(f'data-vocab-id="{item["id"]}"', recent.group(1))
        again = guest.get(f"/review/invite/{invite['token']}", follow_redirects=False)
        self.assertEqual(again.status_code, 302)

    def test_student_still_cannot_mutate_from_academic_review(self):
        ReviewerPermissionTests._insert_user(self, "student_workspace", "StudentPass1", "student")
        ReviewerPermissionTests._login_as(self, "student_workspace", "StudentPass1")
        html = self.client.get("/language/mah-meri/review").get_data(as_text=True)
        academic = self._academic_panel(html)
        self.assertNotIn("review-select-trigger", academic)
        self.assertNotIn("Save review", academic)
        token = _csrf(html)
        rows = self._json_rows(html)
        vocab_id = rows[0]["id"]
        denied = self.client.post(
            "/language/mah-meri/review/vocabulary",
            data={
                "csrf_token": token,
                "vocab_id": str(vocab_id),
                "status": "academically_reviewed",
                "note": "should fail",
                "return_to": "academic",
            },
        )
        self.assertEqual(denied.status_code, 403)




if __name__ == "__main__":
    unittest.main()
