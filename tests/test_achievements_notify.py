"""Achievement popup delivery: newly unlocked vs already delivered.

Run: python -m unittest tests.test_achievements_notify -v
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DB_FD, _DB_PATH = tempfile.mkstemp(prefix="mmle_achievements_", suffix=".db")
os.close(_DB_FD)
os.environ["DATABASE_PATH"] = _DB_PATH
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-achievement-notify-suite")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)
os.environ.pop("DATABASE_URL", None)


def _csrf_from_form(html: str) -> str:
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        raise AssertionError("csrf_token field missing")
    return match.group(1)


def _csrf_from_meta(html: str) -> str:
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    if not match:
        raise AssertionError("csrf-token meta missing")
    return match.group(1)


def _pending_keys(payload: dict) -> list[str]:
    return [item.get("key") for item in (payload.get("pending") or [])]


class AchievementNotifyRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import db
        import app as app_module

        db.set_sqlite_path(_DB_PATH)
        cls.db = db
        cls.app_module = app_module
        cls.app = app_module.app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = True
        cls.app.config["RATELIMIT_ENABLED"] = False
        with cls.app.app_context():
            app_module.init_db()

    @classmethod
    def tearDownClass(cls):
        for suffix in ("", "-wal", "-shm"):
            path = _DB_PATH + suffix
            try:
                os.remove(path)
            except OSError:
                pass

    def setUp(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.app.config["RATELIMIT_ENABLED"] = False
        self.client = self.app.test_client()
        suffix = uuid.uuid4().hex[:10]
        self.username = f"ach_{suffix}"
        self.password = f"Achieve_{suffix}!"
        self.email = f"{self.username}@example.com"
        self.user_id = self._insert_local_user(
            self.username, self.email, self.password
        )

    def _insert_local_user(self, username: str, email: str, password: str) -> int:
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
            row = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return int(row["id"])
        finally:
            conn.close()

    def _login(self):
        get_resp = self.client.get("/login")
        self.assertEqual(get_resp.status_code, 200)
        token = _csrf_from_form(get_resp.get_data(as_text=True))
        resp = self.client.post(
            "/login",
            data={
                "username": self.username,
                "password": self.password,
                "csrf_token": token,
            },
            headers={"Referer": "/login"},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers.get("Location", ""))
        return resp

    def _logout(self):
        resp = self.client.get("/logout", follow_redirects=False)
        self.assertIn(resp.status_code, (302, 303))
        return resp

    def _dashboard_csrf(self) -> str:
        dash = self.client.get("/dashboard")
        self.assertEqual(dash.status_code, 200)
        return _csrf_from_meta(dash.get_data(as_text=True))

    def _get_pending(self) -> dict:
        resp = self.client.get("/api/achievements/pending")
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()

    def _ack(self, keys: list[str], csrf: str) -> dict:
        resp = self.client.post(
            "/api/achievements/ack",
            json={"keys": keys},
            headers={"X-CSRFToken": csrf},
        )
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()

    def test_new_unlock_pending_once_then_refresh_is_empty(self):
        """TEST 1 + TEST 2: first login unlocks once; repeat pending is empty."""
        self._login()
        first = self._get_pending()
        keys = _pending_keys(first)
        self.assertIn(
            "first_steps",
            keys,
            msg="A genuinely new first-login achievement must be pending once",
        )
        self.assertTrue(all(item.get("newly_unlocked") for item in first["pending"]))

        # Refresh / repeated pending fetch must not replay the same unlock.
        second = self._get_pending()
        self.assertEqual(
            _pending_keys(second),
            [],
            msg="Refresh must not treat an already-delivered achievement as new",
        )

    def test_navigation_and_repeated_page_loads_do_not_replay(self):
        """TEST 3 + TEST 4: dashboard/quiz/achievements loads do not re-queue."""
        self._login()
        first_keys = _pending_keys(self._get_pending())
        self.assertIn("first_steps", first_keys)

        dash = self.client.get("/dashboard")
        self.assertEqual(dash.status_code, 200)
        quiz = self.client.get("/quiz")
        self.assertEqual(quiz.status_code, 200)
        gallery = self.client.get("/achievements")
        self.assertEqual(gallery.status_code, 200)
        self.assertIn("First Steps", gallery.get_data(as_text=True))

        for _ in range(3):
            self.assertEqual(_pending_keys(self._get_pending()), [])
            self.assertEqual(self.client.get("/dashboard").status_code, 200)

        listed = self.client.get("/api/achievements")
        self.assertEqual(listed.status_code, 200)
        entries = listed.get_json().get("entries") or []
        unlocked = {row["key"] for row in entries if row.get("unlocked")}
        self.assertIn("first_steps", unlocked)

    def test_logout_login_does_not_replay_already_unlocked(self):
        """TEST 5: re-login must not pop an already-delivered achievement."""
        self._login()
        self.assertIn("first_steps", _pending_keys(self._get_pending()))

        self._logout()
        self._login()

        dash = self.client.get("/dashboard")
        self.assertEqual(dash.status_code, 200)
        replay = _pending_keys(self._get_pending())
        self.assertNotIn(
            "first_steps",
            replay,
            msg="Logout/login must not replay an already-unlocked achievement",
        )
        self.assertEqual(replay, [])

    def test_evaluate_json_delivers_new_achievement_only_once(self):
        """TEST 6: a later genuine unlock pops once; repeats do not."""
        self._login()
        self.assertIn("first_steps", _pending_keys(self._get_pending()))
        csrf = self._dashboard_csrf()

        first_eval = self.client.post(
            "/api/achievements/evaluate",
            json={"milestone": "world_explorer_visit"},
            headers={"X-CSRFToken": csrf},
        )
        self.assertEqual(first_eval.status_code, 200)
        newly = first_eval.get_json().get("new_achievements") or []
        new_keys = [item.get("key") for item in newly]
        self.assertIn("welcome_explorer", new_keys)
        self.assertEqual(new_keys.count("welcome_explorer"), 1)

        pending_after = _pending_keys(self._get_pending())
        self.assertNotIn(
            "welcome_explorer",
            pending_after,
            msg="JSON-delivered unlock must not also sit in pending for a replay",
        )

        second_eval = self.client.post(
            "/api/achievements/evaluate",
            json={"milestone": "world_explorer_visit"},
            headers={"X-CSRFToken": csrf},
        )
        self.assertEqual(second_eval.status_code, 200)
        self.assertEqual(second_eval.get_json().get("new_achievements") or [], [])
        self.assertEqual(_pending_keys(self._get_pending()), [])

        third = self.client.post(
            "/api/achievements/evaluate",
            json={"milestone": "malaysia_arrived"},
            headers={"X-CSRFToken": csrf},
        )
        self.assertEqual(third.status_code, 200)
        third_keys = [
            item.get("key")
            for item in (third.get_json().get("new_achievements") or [])
        ]
        self.assertIn("world_traveller", third_keys)
        self.assertEqual(
            self.client.post(
                "/api/achievements/evaluate",
                json={"milestone": "malaysia_arrived"},
                headers={"X-CSRFToken": csrf},
            ).get_json().get("new_achievements")
            or [],
            [],
        )
        self.assertEqual(_pending_keys(self._get_pending()), [])

    def test_ack_is_idempotent_and_login_still_works(self):
        """ACK remains valid; already-notified rows stay quiet."""
        self._login()
        csrf = self._dashboard_csrf()
        pending = self._get_pending()
        keys = _pending_keys(pending)
        self.assertTrue(keys)
        self._ack(keys, csrf)
        self._ack(keys, csrf)
        self.assertEqual(_pending_keys(self._get_pending()), [])

        self._logout()
        self._login()
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        self.assertEqual(_pending_keys(self._get_pending()), [])

    def test_engine_distinguishes_new_from_already_unlocked(self):
        """Direct engine: login-style evaluate leaves pending; pop claims once."""
        from achievements import (
            evaluate_achievements,
            evaluate_achievements_for_display,
            get_achievements_gallery,
            pop_pending_achievement_notifications,
            set_explorer_milestone,
        )

        set_explorer_milestone(self.user_id, "first_login")
        newly = evaluate_achievements(self.user_id)
        new_keys = [item["key"] for item in newly]
        self.assertIn("first_steps", new_keys)

        first_pop = pop_pending_achievement_notifications(self.user_id)
        self.assertIn("first_steps", [item["key"] for item in first_pop])
        second_pop = pop_pending_achievement_notifications(self.user_id)
        self.assertEqual(second_pop, [])

        again = evaluate_achievements(self.user_id)
        self.assertEqual(again, [])
        self.assertEqual(pop_pending_achievement_notifications(self.user_id), [])

        set_explorer_milestone(self.user_id, "world_explorer_visit")
        displayed = evaluate_achievements_for_display(self.user_id)
        self.assertIn("welcome_explorer", [item["key"] for item in displayed])
        self.assertEqual(pop_pending_achievement_notifications(self.user_id), [])
        self.assertEqual(evaluate_achievements_for_display(self.user_id), [])

        gallery = get_achievements_gallery(self.user_id)
        unlocked = {row["key"] for row in gallery["entries"] if row["unlocked"]}
        self.assertIn("first_steps", unlocked)
        self.assertIn("welcome_explorer", unlocked)


if __name__ == "__main__":
    unittest.main(verbosity=2)
