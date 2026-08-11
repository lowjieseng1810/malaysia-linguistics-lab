"""Regression: one-shot account bootstrap restores local password hashes."""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-bootstrap-suite")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)
os.environ.pop("DATABASE_URL", None)


class AccountBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module
        from account_bootstrap import apply_local_account_bootstrap
        from account_bootstrap_data import BOOTSTRAP_KEY, BOOTSTRAP_USERS
        from db import get_db, row_value
        from werkzeug.security import check_password_hash, generate_password_hash

        cls.app_module = app_module
        cls.apply = staticmethod(apply_local_account_bootstrap)
        cls.BOOTSTRAP_KEY = BOOTSTRAP_KEY
        cls.BOOTSTRAP_USERS = BOOTSTRAP_USERS
        cls.db_get = staticmethod(get_db)
        cls.row_value = staticmethod(row_value)
        cls.check_password_hash = staticmethod(check_password_hash)
        cls.generate_password_hash = staticmethod(generate_password_hash)
        cls.app = app_module.app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = True
        with cls.app.app_context():
            app_module.init_db()

    def setUp(self):
        # Reset bootstrap marker and damage target users for a clean run.
        conn = self.db_get()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT)"
            )
            conn.execute(
                "DELETE FROM app_meta WHERE key = ?",
                (self.BOOTSTRAP_KEY,),
            )
            for entry in self.BOOTSTRAP_USERS:
                username = entry["username"]
                # Ensure row exists with a WRONG hash (simulates probe overwrite /
                # missing migration repaired by update).
                row = conn.execute(
                    "SELECT id FROM users WHERE LOWER(username)=LOWER(?)",
                    (username,),
                ).fetchone()
                bad = self.generate_password_hash("not-the-real-password")
                if row:
                    conn.execute(
                        "UPDATE users SET password = ? WHERE LOWER(username)=LOWER(?)",
                        (bad, username),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO users (username, password, provider, email)
                        VALUES (?, ?, 'local', ?)
                        """,
                        (username, bad, f"{username}@probe.example"),
                    )
            conn.commit()
        finally:
            conn.close()

    def test_bootstrap_restores_password_hash_from_payload(self):
        status = self.apply()
        self.assertTrue(status.get("applied"))
        self.assertGreaterEqual(status.get("updated", 0) + status.get("inserted", 0), 1)

        conn = self.db_get()
        try:
            for entry in self.BOOTSTRAP_USERS:
                row = conn.execute(
                    "SELECT password FROM users WHERE LOWER(username)=LOWER(?)",
                    (entry["username"],),
                ).fetchone()
                self.assertIsNotNone(row)
                stored = self.row_value(row, "password")
                self.assertEqual(stored, entry["password"])
                self.assertTrue(str(stored).startswith("scrypt:"))
        finally:
            conn.close()

        # Second call is a no-op
        status2 = self.apply()
        self.assertFalse(status2.get("applied"))
        self.assertEqual(status2.get("reason"), "already_applied")

    def test_login_succeeds_after_bootstrap_with_known_password_probe(self):
        """Optional: only when PASSWORD_PROBE is provided by the operator."""
        probe = os.environ.get("PASSWORD_PROBE")
        if not probe:
            self.skipTest("PASSWORD_PROBE not set")

        self.apply()
        client = self.app.test_client()
        for entry in self.BOOTSTRAP_USERS:
            # Confirm hash verifies
            conn = self.db_get()
            try:
                row = conn.execute(
                    "SELECT password FROM users WHERE LOWER(username)=LOWER(?)",
                    (entry["username"],),
                ).fetchone()
                stored = self.row_value(row, "password")
            finally:
                conn.close()
            self.assertTrue(self.check_password_hash(stored, probe))

            get_resp = client.get("/login")
            match = re.search(
                r'name="csrf_token"[^>]*value="([^"]+)"',
                get_resp.get_data(as_text=True),
            )
            self.assertIsNotNone(match)
            post = client.post(
                "/login",
                data={
                    "username": entry["username"],
                    "password": probe,
                    "csrf_token": match.group(1),
                },
                headers={"Referer": "https://localhost/login"},
            )
            # Successful login redirects to dashboard
            self.assertEqual(post.status_code, 302)
            self.assertIn("/dashboard", post.headers.get("Location", ""))
            client.get("/logout")


if __name__ == "__main__":
    unittest.main(verbosity=2)
