"""Login rate-limit regressions: re-login vs failed-attempt protection.

Run: python -m unittest tests.test_login_rate_limit -v
"""

from __future__ import annotations

import os
import re
import sys
import unittest
import uuid
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-rate-limit-suite-only")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)


def _csrf_from(html: str) -> str:
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        raise AssertionError("csrf_token field missing from login HTML")
    return match.group(1)


class LoginRateLimitRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.app = app_module.app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = True
        # Ensure limiter is active for these regressions.
        cls.app.config["RATELIMIT_ENABLED"] = True
        with cls.app.app_context():
            app_module.init_db()

    def setUp(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.app.config["RATELIMIT_ENABLED"] = True
        self.client = self.app.test_client()
        # Reset in-memory limiter storage between tests.
        try:
            self.app_module.limiter.reset()
        except Exception:
            storage = getattr(self.app_module.limiter, "_storage", None)
            if storage is not None and hasattr(storage, "reset"):
                storage.reset()

        suffix = uuid.uuid4().hex[:10]
        self.username = f"rl_{suffix}"
        self.password = f"RateLimit_{suffix}!"
        self.email = f"{self.username}@example.com"
        self._insert_local_user(self.username, self.email, self.password)

    def _insert_local_user(self, username: str, email: str, password: str) -> None:
        conn = self.app_module.get_db()
        try:
            conn.execute(
                """
                INSERT INTO users (username, email, password, provider)
                VALUES (?, ?, ?, 'local')
                """,
                (username, email, generate_password_hash(password)),
            )
            conn.commit()
        finally:
            conn.close()

    def _post_login(self, username: str, password: str):
        get_resp = self.client.get("/login")
        self.assertEqual(get_resp.status_code, 200)
        token = _csrf_from(get_resp.get_data(as_text=True))
        return self.client.post(
            "/login",
            data={
                "username": username,
                "password": password,
                "csrf_token": token,
            },
            headers={"Referer": "/login"},
            follow_redirects=False,
        )

    def test_login_logout_login_again_is_not_rate_limited(self):
        first = self._post_login(self.username, self.password)
        self.assertEqual(first.status_code, 302)
        self.assertIn("/dashboard", first.headers.get("Location", ""))
        self.assertNotEqual(first.status_code, 429)

        logout = self.client.get("/logout", follow_redirects=False)
        self.assertIn(logout.status_code, (302, 303))

        second = self._post_login(self.username, self.password)
        self.assertNotEqual(
            second.status_code,
            429,
            msg="Successful re-login after logout must not be blocked by login rate limit",
        )
        self.assertEqual(second.status_code, 302)
        self.assertIn("/dashboard", second.headers.get("Location", ""))

        # One more cycle for stability.
        self.client.get("/logout", follow_redirects=False)
        third = self._post_login(self.username, self.password)
        self.assertNotEqual(third.status_code, 429)
        self.assertEqual(third.status_code, 302)

    def test_repeated_failed_logins_are_still_rate_limited(self):
        statuses = []
        for _ in range(6):
            resp = self._post_login(self.username, "definitely-wrong-password")
            statuses.append(resp.status_code)
            if resp.status_code == 429:
                break

        self.assertIn(
            429,
            statuses,
            msg=f"Expected failed logins to hit rate limit; statuses={statuses}",
        )
        body = ""
        # Re-fetch last 429 body if needed
        for _ in range(2):
            resp = self._post_login(self.username, "definitely-wrong-password")
            if resp.status_code == 429:
                body = resp.get_data(as_text=True)
                break
        self.assertIn("Too Many Requests", body)
        self.assertNotIn("Invalid username or password", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
