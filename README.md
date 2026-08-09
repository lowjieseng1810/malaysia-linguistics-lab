# Malaysian Linguistics Lab — Exploring Malaysia's Languages Through Technology

**Malaysian Linguistics Lab** is a Flask web app for learning four Malaysian minority/indigenous languages —
**Iban**, **Kadazan-Dusun**, **Bidayuh**, and **Mah Meri** — through
structured lessons, a searchable dictionary, quizzes, progress tracking, an
interactive 3D language-family globe, and an optional GPT-powered AI tutor.

> **Honesty note:** the AI Tutor depends on the OpenAI API and is
> **optional**. Every other feature — dictionary, favorites, quizzes,
> lessons, progress, comparison, and the world explorer — is built on local
> Python logic and a local SQLite database, and works fully **without** an
> OpenAI API key or any internet-dependent AI service.

## Features

| Area | What it does |
|---|---|
| **Lessons** | Structured, level-based lessons per language with vocabulary, grammar, and culture steps; progress and unlocks are persisted per user. |
| **Dictionary** | Full-text vocabulary search across all four languages with language/POS/difficulty filters, sorting (A→Z, Z→A, longest/shortest, difficulty), pagination, and a word-detail view with IPA, examples, and culture notes where recorded. |
| **Favorites** | Save/unsave any dictionary word to a personal, per-user "Saved Words" page. |
| **Standalone Quiz** | A deterministic, database-backed quiz product (no AI involved): pick a language, level, difficulty, and question count; get instant feedback, a score, and a shareable results screen with retry. |
| **Progress** | Two clearly separated metrics: **lesson completion** (unlocks levels on the dashboard/profile) and **quiz mastery** (practice accuracy, streaks, weak areas, recent quiz session history on the profile). |
| **Language Comparison** | Side-by-side comparison of any two supported languages (region, family, vitality, writing system, sample vocabulary, available levels). |
| **World Explorer** | An interactive 3D globe (Three.js) for discovering each language's origin, with live vocabulary counts and deep links into the dictionary/comparison pages. |
| **AI Tutor (optional)** | A GPT-backed chat tutor that explains, teaches, and answers language questions, grounded by the same SQLite course data. Falls back to a clear "AI unavailable" message if no API key/credits are configured — it never blocks the rest of the site. |
| **Accounts** | Email/password registration and login (with Google OAuth as an optional extra if configured), password reset, and CSRF-protected session-based auth. |

## Architecture

Two independent systems share the same course data:

1. **Course content** (`LANGUAGES`, `COURSE_DATA`, `EXPLORE_UNLOCKS` in
   [`app.py`](app.py)) is the single source of truth for lesson/quiz text.
   It's plain Python data, not stored in the database.
2. **AI Tutor pipeline** ([`tutor_service.py`](tutor_service.py)) seeds that
   same course data into SQLite (`vocabulary`, `grammar`, `culture`, `quiz`
   tables — schema in [`database.py`](database.py)) once at startup, then
   answers tutor questions with a strict
   **Planner → Retriever → Validator → optional LLM rewrite** flow. The LLM
   is only ever allowed to rephrase already-validated database facts; it
   never answers directly from its own knowledge, and it is never required
   for the dictionary, quiz, favorites, progress, comparison, or explorer
   features to work.

See [`AGENTS.md`](AGENTS.md) for a deeper breakdown of the AI Tutor pipeline
and file layout, aimed at contributors/agents working on the codebase.

## Getting started

### Requirements

- Python 3.10+
- No external services required for the core product. An OpenAI API key is
  only needed if you want the AI Tutor chat to give live GPT answers instead
  of its offline fallback message.

### Setup

```bash
git clone <this-repo>
cd malaysian_minority_languages_explorer

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `.env` and set at minimum:

```
SECRET_KEY=<a long random string>
```

Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

All other variables in `.env.example` are optional — see the comments in
that file for what each one does. Leaving `AI_TUTOR_API_KEY` blank is fine;
the app runs normally and the AI Tutor simply reports itself as
unavailable.

### Run

```bash
python app.py
```

Then open `http://127.0.0.1:5000`.

On first run, `init_db()` creates `users.db` (SQLite) in the project root
and seeds it with the course vocabulary/grammar/culture/quiz content.
Delete `users.db` at any time to fully reset local data — it will be
recreated automatically on the next run.

### Production HTTPS (deployment-ready)

Do **not** expose `python app.py` / the Flask development server to the
public internet. Terminate TLS at a reverse proxy (Nginx, Caddy, etc.) or
a platform load balancer, and run the app with a WSGI server (e.g.
Waitress/Gunicorn) behind it.

On the app side, set in `.env`:

```
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=<long random value>
TRUST_PROXY=true
FORCE_HTTPS=true
```

- `TRUST_PROXY=true` — honour `X-Forwarded-Proto` / `Host` from the proxy
  (required so Secure cookies and redirects see HTTPS correctly).
- `FORCE_HTTPS=true` — redirect HTTP→HTTPS (localhost skipped), Prefer
  HTTPS URL generation, Secure session cookies, and HSTS on secure
  responses.

**Remaining step on the server (not done in this repo):** obtain a trusted
certificate for your domain (e.g. Let’s Encrypt via Certbot or your host’s
managed TLS), point the proxy at the WSGI app, and forward
`X-Forwarded-Proto` / `X-Forwarded-For`. A self-signed cert is fine for
local experiments only — not production.

### Optional: Google sign-in

Google OAuth only activates if a valid `google_client_secret.json` (Google
Cloud OAuth client credentials) is placed in the project root. If it's
missing or invalid, the app logs a warning at startup and simply omits the
"Sign in with Google" option — email/password accounts still work fully.

## Project structure

```
app.py                 Flask routes, auth, dashboard, dictionary/quiz/favorites APIs
database.py             SQLite schema + seeding for the AI Tutor's content tables
tutor_service.py        AI Tutor orchestration (planner -> retrieval -> validator -> composer)
planner.py               Classifies user questions into structured retrieval operations
retrieval.py             Executes SQL / dictionary search, returns rows + query used
validator.py             Rejects zero/low-confidence evidence before any LLM call
composer.py               OpenAI API integration (only ever rephrases validated facts)
quiz_service.py          Deterministic quiz logic for both the chat quiz and standalone quiz
learning_memory.py       Per-user quiz mastery / weak-area tracking
language_registry.py     Canonical language keys, display names, aliases
templates/               Jinja2 templates (dashboard, dictionary, quiz, favorites, compare, ...)
static/js, static/css    Frontend behavior and styling
qa_temp/                 Manual QA/acceptance scripts used during development (not shipped tests)
```

## Testing

There is no `pytest` suite; instead there are runnable Python scripts under
`qa_temp/` that exercise the real Flask app + SQLite database via Flask's
test client:

```bash
python qa_temp/non_ai_acceptance.py   # dictionary, favorites, quiz, progress, lessons, compare, explorer, security
python qa_temp/test_dictionary_suite.py
python qa_temp/robustness_audit.py
```

These do **not** require an OpenAI API key — they specifically cover the
non-AI product surface.

## Known limitations

- The AI Tutor depends on OpenAI API availability/quota. If the API key is
  missing or billing/quota is exhausted, the Tutor chat falls back to its
  offline path — **dictionary, favorites, standalone quiz, lessons,
  progress, comparison, and the world explorer keep working fully**.
- Vocabulary coverage varies by language and is limited to what has been
  manually curated in `COURSE_DATA` — the dictionary does not claim to be
  an exhaustive lexicon, and missing IPA/examples are left blank rather
  than invented.
- Linguistic classifications (family, vitality status, speaker estimates)
  shown on the comparison/explorer pages are general reference information
  and may be refined as the project incorporates more community/linguistic
  sources.
- The 3D World Explorer requires WebGL; devices without it see a clear
  fallback message and can still use every other learning feature.

## Contributing

Issues and pull requests are welcome. Please keep the separation described
above (course data vs. AI Tutor pipeline) intact, and avoid hardcoding
answers for individual test questions — the retrieval/validator layers are
meant to generalize.
