# AGENTS.md

**Malaysia Linguistics Lab** — Flask web app teaching four Malaysian
minority/indigenous languages (Iban, Kadazan-Dusun, Bidayuh, Mah Meri):
lessons, searchable dictionary, favorites, standalone practice quiz, progress
tracking, language comparison, a 3D world explorer, and an optional AI tutor
chat.

## Run / setup

- Install from [`requirements.txt`](requirements.txt) (`flask`, `flask-wtf`,
  `flask-limiter`, `authlib`, `python-dotenv`, `werkzeug`, `requests`,
  `openai`, `psycopg` — OpenAI client lives in [composer.py](composer.py)).
- Entry point: `python app.py` (from this folder). Requires a `.env` with at
  least `SECRET_KEY` (app raises `RuntimeError` at import time if missing).
  See [`.env.example`](.env.example) for optional keys (`FLASK_DEBUG`,
  `FLASK_ENV`, `DATABASE_URL`, `DATABASE_PATH`, `AI_TUTOR_API_KEY`,
  `AI_TUTOR_MODEL`, `DEBUG_TUTOR`, `TRUST_PROXY`, `FORCE_HTTPS`,
  `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
- Google OAuth is optional — registers when `GOOGLE_CLIENT_ID` +
  `GOOGLE_CLIENT_SECRET` are set (preferred on Render), or when a valid
  local `google_client_secret.json` exists; otherwise it logs a warning and
  skips it. Login/Register hide the Google button unless OAuth is configured.
  On Render set `TRUST_PROXY=true` and `FORCE_HTTPS=true` so OAuth callbacks
  use HTTPS on the custom domain.
- Database access goes through [`db.py`](db.py): if `DATABASE_URL` is set,
  use **PostgreSQL** (production / Render); otherwise use local **SQLite**
  `users.db` (optional `DATABASE_PATH`). Schema is created/migrated by
  `init_db()` in [app.py](app.py) (`CREATE IF NOT EXISTS` / additive
  columns — never DROP users). Delete local `users.db` only to reset local
  data.
- Non-AI product surface (dictionary, favorites, `/quiz`, lessons, compare,
  explorer, profile) works fully without an OpenAI key. See [`README.md`](README.md).

## Architecture: content vs. AI tutor are two separate systems

1. **Course content (`LANGUAGES`, `COURSE_DATA`, `EXPLORE_UNLOCKS` dicts in
   [app.py](app.py))** is the single source of truth for lesson/quiz text
   shown in the UI. It's plain Python data, not loaded from the DB.
2. **AI Tutor chat** ([tutor_service.py](tutor_service.py)) is **GPT-first**:
   user question (+ conversation history) → OpenAI via
   [composer.py](composer.py) `compose_general_tutor_response()` → direct answer.
   There is no mandatory course-database retrieval or domain gate before GPT
   can answer. The in-tutor Quiz button / active-quiz grading remain
   deterministic via [quiz_service.py](quiz_service.py).
   Course content is still seeded into the database (`vocabulary`, `grammar`,
   `culture`, `quiz` — [database.py](database.py)) for dictionary / standalone
   quiz / lessons — not as a tutor answer gate.
   Tutor turns are audited to [logs/tutor_retrieval.jsonl](logs/tutor_retrieval.jsonl).
   Tutor debug APIs (`/api/tutor/debug/*`) require a logged-in session and
   `DEBUG_TUTOR=true` on the server.

When changing tutor chat behavior, keep it GPT-first: do not reintroduce a
mandatory planner/retrieval refuse path for ordinary questions.

## Conventions / gotchas

- `app_backup.py`, `app_backup2.py`, `app_before_courses.py`,
  `app_wrong_courses.py` are stale snapshots of `app.py`, gitignored and not
  imported by anything — don't edit them expecting an effect.
- No automated test suite. [qa_temp/verify_pipeline.py](qa_temp/verify_pipeline.py)
  and [qa_temp/verify_rag.py](qa_temp/verify_rag.py) are manual one-off
  scripts for sanity-checking the tutor pipeline (`python qa_temp/verify_pipeline.py`).
- CSRF protection (`flask-wtf`) and login rate limiting (`flask-limiter`,
  5/min) are already wired up in [app.py](app.py) — reuse `csrf`/`limiter`,
  don't add a second CSRF/rate-limit mechanism.
- Password reset tokens are hashed (SHA-256) and time-limited (30 min);
  see `create_reset_token()`/`hash_reset_token()` in [app.py](app.py).
- Sibling folders at the Desktop level (`malaysian_minority_languages_explorer - Copy`,
  `- Copy (2)`, `- Copy (3)`) are unrelated manual backups outside this git
  repo — ignore them unless the user explicitly asks to compare/restore.
