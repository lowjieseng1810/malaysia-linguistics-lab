"""CSRF / session regression tests for GET /login.

Run: python -m unittest tests.test_auth_csrf -v
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-csrf-suite-only")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)


class LoginCsrfRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.app = app_module.app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = True
        with cls.app.app_context():
            app_module.init_db()

    def setUp(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.client = self.app.test_client()

    def test_get_login_succeeds_and_issues_csrf_session(self):
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertNotIn("CSRF session token is missing", body)
        self.assertIn("csrf-token", body)
        self.assertIn('name="csrf_token"', body)
        self.assertIn("session=", resp.headers.get("Set-Cookie") or "")

    def test_get_login_behind_proxy_headers_succeeds(self):
        resp = self.client.get(
            "/login",
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "malaysialinguisticlab.com",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(
            "CSRF session token is missing",
            resp.get_data(as_text=True),
        )

    def test_post_login_without_csrf_token_is_rejected(self):
        resp = self.client.post(
            "/login",
            data={"username": "nobody", "password": "nope"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("CSRF", resp.get_data(as_text=True))

    def test_post_login_with_csrf_token_and_session_is_accepted(self):
        get_resp = self.client.get("/login")
        match = re.search(
            r'name="csrf_token"[^>]*value="([^"]+)"',
            get_resp.get_data(as_text=True),
        )
        self.assertIsNotNone(match)
        post_resp = self.client.post(
            "/login",
            data={
                "username": "nobody",
                "password": "nope",
                "csrf_token": match.group(1),
            },
            headers={"Referer": "https://localhost/login"},
        )
        self.assertNotEqual(post_resp.status_code, 400)
        self.assertNotIn(
            "CSRF session token is missing",
            post_resp.get_data(as_text=True),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
