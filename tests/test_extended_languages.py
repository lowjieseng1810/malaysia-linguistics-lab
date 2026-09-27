"""Nine-language extension: registry, teaching-set consistency, map counts.

Run: python -m unittest tests.test_extended_languages -v
"""

from __future__ import annotations

import os
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

from course_from_dataset import TEACHING_SETS, all_extended_course_data
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

    def test_teaching_set_matches_quiz_answers(self):
        course = all_extended_course_data()
        for lang_key, levels in TEACHING_SETS.items():
            for level_num, words in levels.items():
                steps = course[lang_key][level_num]["steps"]
                taught = {
                    (s.get("word") or "").strip()
                    for s in steps
                    if s.get("type") == "vocabulary"
                }
                self.assertTrue(taught)
                for step in steps:
                    if step.get("type") != "quiz":
                        continue
                    options = step.get("options") or []
                    idx = step.get("correctIndex", 0)
                    answer = options[idx]
                    hint = (step.get("hint") or "").lower()
                    self.assertTrue(answer)
                    self.assertNotIn("think carefully", hint)
                    self.assertNotIn("look at the choices", hint)
                    # reverse items use a taught word as the answer
                    if answer in taught or any(opt in taught for opt in options):
                        continue
                    meanings = {
                        (s.get("meaning") or "").strip()
                        for s in steps
                        if s.get("type") == "vocabulary"
                    }
                    self.assertIn(answer, meanings)

    def test_bookan_facts_excluded_from_dictionary_harvest(self):
        from database import _collect_vocab_from_steps

        course = all_extended_course_data()["bookan"]
        for level_num, payload in course.items():
            harvested = _collect_vocab_from_steps("bookan", level_num, payload["steps"])
            self.assertEqual(harvested, [])

    def test_bookan_marked_without_dictionary_lexicon(self):
        self.assertTrue(self.app_module.LANGUAGES["bookan"].get("exclude_dictionary"))
        for key in ("chewong", "kristang", "baba-malay", "temoq", "iban"):
            self.assertFalse(self.app_module.LANGUAGES[key].get("exclude_dictionary"))

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


if __name__ == "__main__":
    unittest.main()
