"""Nine-language extension: registry, teaching-set consistency, map counts.

Run: python -m unittest tests.test_extended_languages -v
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DB_FD, _DB_PATH = tempfile.mkstemp(prefix="mmle_nine_", suffix=".db")
os.close(_DB_FD)
os.environ["DATABASE_PATH"] = _DB_PATH
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-nine-language-suite")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)
os.environ.pop("DATABASE_URL", None)

from course_from_dataset import all_extended_course_data
from language_catalog import COURSE_LANGUAGES, EXTENDED_LANGUAGES, MAP_COORDS
from language_registry import resolve_language


class NineLanguageDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.client = app_module.app.test_client()

    def test_nine_languages_registered(self):
        langs = self.app_module.LANGUAGES
        self.assertEqual(len(langs), 9)
        for key in COURSE_LANGUAGES:
            self.assertIn(key, langs)
            self.assertTrue(langs[key].get("display_name"))
            self.assertTrue(langs[key].get("region"))

    def test_original_four_still_present(self):
        for key in ("iban", "kadazan-dusun", "bidayuh", "mah-meri"):
            self.assertIn(key, self.app_module.COURSE_DATA)
            self.assertGreaterEqual(len(self.app_module.COURSE_DATA[key]), 3)

    def test_extended_courses_have_three_levels(self):
        course = all_extended_course_data()
        for key in EXTENDED_LANGUAGES:
            self.assertIn(key, course)
            self.assertEqual(set(course[key].keys()), {1, 2, 3})

    def test_knowledge_quizzes_are_complete(self):
        course = all_extended_course_data()
        asjp_noise = ("m3*7", "E*N", "%tom", "a7oc", "oraN", "mata5a")
        for lang_key, levels in course.items():
            quiz_count = 0
            for payload in levels.values():
                steps = payload.get("steps") or []
                self.assertTrue(steps, lang_key)
                blob = " ".join(str(s) for s in steps)
                for token in asjp_noise:
                    self.assertNotIn(token, blob, lang_key)
                for step in steps:
                    if step.get("type") != "quiz":
                        continue
                    quiz_count += 1
                    options = [str(o).strip() for o in (step.get("options") or []) if str(o).strip()]
                    self.assertGreaterEqual(len(options), 2, lang_key)
                    self.assertEqual(len(options), len(set(o.lower() for o in options)), lang_key)
                    idx = step["correctIndex"]
                    self.assertLess(idx, len(options))
                    hint = (step.get("hint") or "").lower()
                    self.assertTrue(step.get("hint"))
                    self.assertNotIn("think carefully", hint)
                    self.assertNotIn("look at the options", hint)
                    self.assertTrue(step.get("correctFeedback") or step.get("wrongFeedback"))
                    q = (step.get("question") or "")
                    q_low = q.lower()
                    self.assertNotRegex(
                        q,
                        r'What does\s+[\'"“][^\'"”]{1,12}[\'"”]\s+mean',
                        lang_key,
                    )
                    self.assertNotRegex(
                        q_low,
                        r"which (word|expression) means",
                        lang_key,
                    )
                    self.assertNotIn("iso 639", q_low)
                    self.assertNotIn("dk0743", q_low)
                    self.assertNotIn("what does \"in\" mean", q_low)
            self.assertGreaterEqual(quiz_count, 4, lang_key)

    def test_bookan_facts_excluded_from_dictionary_harvest(self):
        from database import _collect_vocab_from_steps

        course = all_extended_course_data()["bookan"]
        for level_num, payload in course.items():
            harvested = _collect_vocab_from_steps("bookan", level_num, payload["steps"])
            self.assertEqual(harvested, [])

    def test_bookan_marked_without_dictionary_lexicon(self):
        self.assertTrue(self.app_module.LANGUAGES["bookan"].get("exclude_dictionary"))
        for key in ("chewong", "baba-malay", "temoq"):
            self.assertTrue(self.app_module.LANGUAGES[key].get("exclude_dictionary"), key)
        self.assertFalse(self.app_module.LANGUAGES["kristang"].get("exclude_dictionary"))
        self.assertFalse(self.app_module.LANGUAGES["iban"].get("exclude_dictionary"))

    def test_quiz_options_are_unique_and_contain_answer(self):
        course = all_extended_course_data()
        for lang_key, levels in course.items():
            for payload in levels.values():
                for step in payload.get("steps") or []:
                    if step.get("type") != "quiz":
                        continue
                    options = [str(o).strip() for o in (step.get("options") or []) if str(o).strip()]
                    self.assertEqual(len(options), len(set(o.lower() for o in options)), lang_key)
                    idx = step["correctIndex"]
                    self.assertLess(idx, len(options))
                    self.assertTrue(step.get("hint"))
                    self.assertNotIn("think carefully", (step.get("hint") or "").lower())

    def test_map_state_counts(self):
        payload = self.app_module.LANGUAGE_MAP
        counts = payload["state_counts"]
        self.assertEqual(counts["Sarawak"], 2)
        self.assertEqual(counts["Sabah"], 2)
        self.assertEqual(counts["Selangor"], 1)
        self.assertEqual(counts["Pahang"], 2)
        self.assertEqual(counts["Melaka"], 2)
        self.assertEqual(len(payload["points"]), 9)
        self.assertEqual(MAP_COORDS["chewong"]["state"], "Pahang")
        self.assertEqual(MAP_COORDS["temoq"]["state"], "Pahang")
        self.assertEqual(MAP_COORDS["kristang"]["state"], "Melaka")
        self.assertEqual(MAP_COORDS["baba-malay"]["state"], "Melaka")

    def test_tutor_aliases_resolve(self):
        self.assertEqual(resolve_language("Papía Kristang".replace("í", "i")), "kristang")
        self.assertEqual(resolve_language("Cheq Wong"), "chewong")
        self.assertEqual(resolve_language("Murut Bookan"), "bookan")
        self.assertEqual(resolve_language("Baba Malay"), "baba-malay")
        self.assertEqual(resolve_language("Temoq"), "temoq")
        self.assertEqual(resolve_language("Iban"), "iban")

    def test_dashboard_and_language_routes(self):
        # dashboard requires login
        resp = self.client.get("/about")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("9 languages", body)
        self.assertIn("Bookan", body)
        self.assertIn("Chewong", body)
        self.assertIn("Kristang", body)
        self.assertIn("Baba Malay", body)
        self.assertIn("Temoq", body)
        self.assertIn("Iban", body)

        for key in EXTENDED_LANGUAGES:
            page = self.client.get(f"/language/{key}")
            self.assertIn(page.status_code, (200, 302), key)

    def test_compare_includes_new_languages(self):
        resp = self.client.get("/compare?a=kristang&b=baba-malay")
        self.assertIn(resp.status_code, (200, 302))

    def _login_session(self):
        from werkzeug.security import generate_password_hash
        from db import get_db

        conn = get_db()
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("nine_qa_user",)
        ).fetchone()
        if not row:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "email" in cols:
                conn.execute(
                    """
                    INSERT INTO users (username, password, email, provider, role)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "nine_qa_user",
                        generate_password_hash("NineQaPass1"),
                        "nine_qa@example.com",
                        "local",
                        "student",
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    ("nine_qa_user", generate_password_hash("NineQaPass1")),
                )
            conn.commit()
            row = conn.execute(
                "SELECT id FROM users WHERE username = ?", ("nine_qa_user",)
            ).fetchone()
        conn.close()
        with self.client.session_transaction() as sess:
            sess["user_id"] = int(row["id"])
            sess["username"] = "nine_qa_user"

    def test_logged_in_pages_show_nine_languages(self):
        self._login_session()
        names = (
            "Iban",
            "Kadazan-Dusun",
            "Bidayuh",
            "Mah Meri",
            "Bookan",
            "Chewong",
            "Kristang",
            "Baba Malay",
            "Temoq",
        )
        dash = self.client.get("/dashboard")
        self.assertEqual(dash.status_code, 200)
        body = dash.get_data(as_text=True)
        for name in names:
            self.assertIn(name, body)
        self.assertIn("Lexicon under review", body)
        self.assertIn("heritage-passport", body)
        self.assertIn("Listen & Discover", body)
        self.assertNotIn("bookan-record", body)

        dictionary = self.client.get("/dictionary")
        self.assertEqual(dictionary.status_code, 200)
        dict_html = dictionary.get_data(as_text=True)
        self.assertIn("Lexicon not bundled", dict_html)
        self.assertIn("docs only", dict_html)

        quiz = self.client.get("/quiz")
        self.assertEqual(quiz.status_code, 200)
        quiz_html = quiz.get_data(as_text=True)
        for name in names:
            self.assertIn(name, quiz_html)

        daily = self.client.get("/quiz?mode=daily")
        self.assertEqual(daily.status_code, 200)
        self.assertIn("Daily Quiz", daily.get_data(as_text=True))

        compare = self.client.get("/compare?a=iban&b=kristang")
        self.assertEqual(compare.status_code, 200)

        review = self.client.get("/review")
        self.assertIn(review.status_code, (200, 302))

        for key in (
            "iban",
            "kadazan-dusun",
            "bidayuh",
            "mah-meri",
            "bookan",
            "chewong",
            "kristang",
            "baba-malay",
            "temoq",
        ):
            page = self.client.get(f"/language/{key}")
            self.assertEqual(page.status_code, 200, key)
            html = page.get_data(as_text=True)
            self.assertTrue(html)
            learn = self.client.get(f"/language/{key}/learn")
            self.assertEqual(learn.status_code, 200, key)

        bookan = self.client.get("/language/bookan").get_data(as_text=True)
        self.assertIn("Keningau", bookan)
        self.assertIn("No community-verified lexicon is claimed here", bookan)
        self.assertIn("does not invent Bookan words", bookan)

    def test_map_script_has_only_state_beacons(self):
        js = (ROOT / "static" / "js" / "dashboard.js").read_text(encoding="utf-8")
        self.assertNotIn("extraBeaconButtonsHTML", js)
        self.assertNotIn("exploration-beacon lang-beacon", js)
        self.assertNotIn("bookan-beacon", js)
        self.assertNotIn("chewong-beacon", js)
        self.assertIn('data-region="selangor"', js)
        self.assertIn('data-region="pahang"', js)
        self.assertIn('data-region="melaka"', js)
        self.assertIn("function livingCountLabel", js)
        self.assertIn('livingCountLabel("Sabah", 2)', js)
        self.assertIn('livingCountLabel("Selangor", 1)', js)
        self.assertIn('livingCountLabel("Pahang", 2)', js)
        self.assertIn('livingCountLabel("Melaka", 2)', js)
        self.assertIn('livingCountLabel("Sarawak", 2)', js)

    def test_practice_and_daily_have_new_language_questions(self):
        from db import get_db
        from database import sync_extended_course_quizzes

        sync_extended_course_quizzes(self.app_module.COURSE_DATA)
        conn = get_db()
        for key in EXTENDED_LANGUAGES:
            n = conn.execute(
                "SELECT COUNT(*) AS c FROM quiz WHERE language = ?", (key,)
            ).fetchone()["c"]
            self.assertGreaterEqual(n, 4, key)
            asjp_rows = conn.execute(
                """
                SELECT question, option_a, option_b, option_c, option_d, correct_answer
                FROM quiz WHERE language = ?
                """,
                (key,),
            ).fetchall()
            blob = " ".join(" ".join(str(v or "") for v in dict(r).values()) for r in asjp_rows)
            for token in ("m3*7", "a7oc", "E*N", "%tom"):
                self.assertNotIn(token, blob, key)
        conn.close()

        self._login_session()
        html = self.client.get("/quiz").get_data(as_text=True)
        csrf = re.search(r'name="csrf-token"\s+content="([^"]+)"', html)
        if not csrf:
            csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
        self.assertIsNotNone(csrf)
        headers = {"X-CSRFToken": csrf.group(1)}
        for key in EXTENDED_LANGUAGES:
            started = self.client.post(
                "/api/quiz/start",
                json={
                    "mode": "practice",
                    "lang_key": key,
                    "level_num": 1,
                    "difficulty": "medium",
                    "count": 5,
                },
                headers=headers,
            ).get_json()
            self.assertTrue(started.get("ok"), (key, started))
            current = started.get("current_question") or {}
            self.assertTrue(current.get("question"), key)
            daily = self.client.post(
                "/api/quiz/start",
                json={"mode": "daily", "lang_key": key},
                headers=headers,
            ).get_json()
            self.assertTrue(daily.get("ok"), (key, daily))
            self.assertTrue((daily.get("current_question") or {}).get("question"), key)


if __name__ == "__main__":
    unittest.main()
