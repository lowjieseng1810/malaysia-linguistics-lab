# Malaysia Linguistics Lab

### Explore Malaysia's Living Languages

An interactive open-source platform for discovering Malaysia's minority and indigenous languages through language, place, culture, voice, and community.

**Live Demo:** [https://malaysialinguisticlab.com](https://malaysialinguisticlab.com)

[Live Demo](https://malaysialinguisticlab.com) · [GitHub](https://github.com/lowjieseng1810/malaysia-linguistics-lab) · [Report a Bug](https://github.com/lowjieseng1810/malaysia-linguistics-lab/issues)

**License:** MIT

---

## What makes it different?

Malaysia is home to many living languages that receive far less digital representation than major world languages.

Malaysia Linguistics Lab turns that linguistic diversity into an interactive exploration experience.

### Explore

- Where languages are spoken
- Interactive geographic exploration
- Language and voice content
- Vocabulary and learning
- Cultural context
- Interactive learning activities

The product currently focuses on four languages — **Iban**, **Kadazan-Dusun**, **Bidayuh**, and **Mah Meri** — through structured lessons, a searchable dictionary, quizzes, progress tracking, a 3D World Explorer, and an optional AI tutor.

Course lesson text lives in application data (`COURSE_DATA` in `app.py`). Dictionary, quiz, favorites, and related features use database tables seeded from that content. The optional AI Tutor is separate: chat answers go through OpenAI when configured, while the rest of the product does not require an AI API key.

---

## Features

- **Language lessons** — Level-based learning paths per language (vocabulary, discovery, response, and quiz-style steps), with unlocks and step progress saved per account.
- **Dictionary** — Searchable vocabulary with language filters, sorting, pagination, word detail, and a random-word discovery card on the dashboard.
- **Saved Words / Favorites** — Save and manage dictionary entries on a personal Saved Words page.
- **Practice Quiz** — Deterministic, database-backed quizzes (language, level, difficulty, question count) with grading and results.
- **Daily Quiz** — A daily challenge mode (`/quiz?mode=daily`) using the same quiz engine.
- **Progress tracking** — Lesson completion and unlock state on language/learn pages; quiz mastery and related history on the profile.
- **Achievements** — Collectible achievement stamps earned through exploration and learning.
- **Heritage Passport** — Dashboard passport cards for discovering languages as you explore.
- **Language comparison** — Side-by-side comparison of two supported languages.
- **World Explorer** — Interactive Three.js Earth on the dashboard, with Malaysia exploration and deep links into learning content (WebGL required for the 3D view; other features remain available without it).
- **AI Tutor (optional)** — In-app chat companion powered by OpenAI when an API key is set; core learning features keep working if the key is missing.
- **Accounts** — Registration and login with email/password, password reset, CSRF-protected sessions, optional Google OAuth (`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` or local `google_client_secret.json`), plus profile and mascot settings pages.

---

## Live Demo

**[https://malaysialinguisticlab.com](https://malaysialinguisticlab.com)**

Create your own account on the demo; do not rely on it for private or production data. Hosted demos may have cold starts after idle periods.

---

## Technology

| Layer | Stack |
|---|---|
| Backend | Python, Flask |
| Templates | Jinja2 (`templates/`) |
| Frontend | HTML/CSS/JavaScript (`static/`) |
| 3D explorer | Three.js (CDN) + `static/js/earth-globe.js` |
| Database | **SQLite** locally (`users.db`); **PostgreSQL** when `DATABASE_URL` is set (production) |
| Auth extras | Flask-WTF (CSRF), Flask-Limiter, Authlib (optional Google OAuth) |
| AI Tutor | OpenAI Python client (`composer.py`) when `AI_TUTOR_API_KEY` / `OPENAI_API_KEY` is set |
| Production server | Gunicorn (see `requirements.txt`) |

---

## Getting Started

### Requirements

- Python 3.10+
- No external services for core learning features
- An OpenAI API key only if you want live AI Tutor replies

### Setup

```bash
git clone https://github.com/lowjieseng1810/malaysia-linguistics-lab.git
cd malaysia-linguistics-lab

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt

# Windows
copy .env.example .env
# macOS / Linux
# cp .env.example .env
```

Edit `.env` and set at least:

```
SECRET_KEY=<a long random string>
```

Generate a key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Run locally

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

On first run, `init_db()` creates schema and seeds course vocabulary/grammar/culture/quiz content as needed.

### Database: local SQLite vs production PostgreSQL

- **Local development:** leave `DATABASE_URL` unset. The app uses SQLite at `<project_root>/users.db` (optional override: `DATABASE_PATH`).
- **Production:** set `DATABASE_URL` to your PostgreSQL URL. The app uses Postgres whenever that variable is set. Render may provide `postgres://…`; the app normalizes it to `postgresql://…`.

Do not commit `.env` or real database URLs. Schema init is idempotent (`CREATE IF NOT EXISTS` / additive columns).

### Optional: Google sign-in

Prefer environment variables (required for Render / production):

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
TRUST_PROXY=true
FORCE_HTTPS=true
```

Local development may instead use a gitignored `google_client_secret.json` in the project root (Google Cloud “Download JSON” for a Web application client). If neither env vars nor the JSON file are present, Google sign-in is disabled and the Google button is hidden.

In Google Cloud Console, add authorized redirect URIs for your production hosts, for example:

- `https://malaysialinguisticlab.com/login/google/callback`
- `https://www.malaysialinguisticlab.com/login/google/callback`

Never commit OAuth secrets.

### Production notes

Do not expose the Flask development server publicly. Use a WSGI server (for example Gunicorn) behind TLS termination. For reverse-proxy HTTPS setups, see `TRUST_PROXY` and `FORCE_HTTPS` in `.env.example`.

---

## Environment Variables

Copy [`.env.example`](.env.example) to `.env` and supply your own values. Never commit real credentials.

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | **Yes** | Signs session cookies and CSRF tokens |
| `FLASK_DEBUG` | No | Debug mode (keep `false` on public hosts) |
| `FLASK_ENV` | No | `development` or `production` |
| `FLASK_HOST` | No | Bind host for `python app.py` |
| `DATABASE_PATH` | No | Override local SQLite file path |
| `DATABASE_URL` | No | PostgreSQL URL (enables Postgres instead of SQLite) |
| `TRUST_PROXY` | No | Honour `X-Forwarded-*` behind a reverse proxy |
| `FORCE_HTTPS` | No | Prefer HTTPS redirects / Secure cookies |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID (production) |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth client secret (production) |
| `AI_TUTOR_API_KEY` | No | OpenAI key for AI Tutor chat (`OPENAI_API_KEY` also accepted) |
| `AI_TUTOR_MODEL` | No | Model name when the tutor is enabled |
| `DEBUG_TUTOR` | No | Enables `/api/tutor/debug/*` for logged-in users when `true` |

`.env.example` contains placeholders only. Use your own API keys, OAuth client file, and database credentials.

---

## AI Tutor

The AI Tutor is **optional**.

- With a valid `AI_TUTOR_API_KEY` (or `OPENAI_API_KEY`), chat replies are generated via OpenAI (`compose_general_tutor_response()` in `composer.py`), orchestrated by `tutor_service.py`.
- Without a key (or if the API is unavailable), the tutor reports that AI is unavailable; **dictionary, favorites, practice/daily quiz, lessons, progress, comparison, achievements, and World Explorer continue to work**.
- In-tutor quiz actions remain deterministic (`quiz_service.py`) and do not require the LLM for grading.
- Course content is still stored in the database for dictionary/quiz/lessons; it is not used as a mandatory refuse-gate for ordinary tutor chat.

---

## Project Structure

```
app.py                 Flask app: routes, auth, course data, init_db
db.py                  SQLite / PostgreSQL connection layer
db_path.py             Local SQLite path helper
database.py            Content table seeding (vocabulary, grammar, culture, quiz)
quiz_service.py        Practice and daily quiz session logic
tutor_service.py       AI Tutor chat orchestration
composer.py            OpenAI client for tutor replies
achievements.py        Achievement definitions and evaluation
language_registry.py   Language keys and display names from DB content
learning_memory.py     Quiz mastery / weak-area helpers
templates/             Jinja2 pages (dashboard, lessons, dictionary, quiz, …)
static/js              Frontend (earth-globe, level, dashboard, tutor, …)
static/css             Stylesheets
static/images          Product imagery and Earth textures
data/vocabulary        Curated vocabulary packs
tests/                 Focused auth/CSRF and login rate-limit regression tests
requirements.txt       Python dependencies
.env.example           Environment variable template (no secrets)
AGENTS.md              Contributor/agent notes for this codebase
LICENSE                MIT License
```

---

## Testing

Focused unit tests (no full `pytest` suite) cover authentication CSRF/session
behaviour and login rate-limit regressions:

```bash
python -m unittest tests.test_auth_csrf tests.test_login_rate_limit -v
```

Optional local OAuth/auth smoke scripts may exist under `qa_temp/` on a
developer machine; that folder is gitignored and is not part of the public
test surface.

Practical manual checks:

1. Create `.env` from `.env.example`, set `SECRET_KEY`, install dependencies, and run `python app.py`.
2. Exercise dictionary, favorites, practice/daily quiz, a lesson level, compare, achievements, and profile while logged in.
3. Confirm the AI Tutor shows an unavailable state when no API key is set, and replies when a valid key is configured.
4. Optionally run Python’s compiler check on modules you change, for example:
   `python -m py_compile app.py`

---

## Password reset (development)

Forgot-password creates a time-limited reset token when a matching local
account email exists. **Reset links are written to the server console only
when `FLASK_ENV=development` or `FLASK_DEBUG=true`.** Production does not
send reset email out of the box; deployers who need email delivery must add
their own mailer.

---

## Known Limitations

- The AI Tutor depends on OpenAI availability and quota when enabled; without a key, only the tutor chat is limited.
- Vocabulary and course coverage are curated for the four supported languages and are not an exhaustive lexicon.
- Linguistic metadata on comparison/explorer surfaces (family, region, vitality-style notes) is general reference material and may be refined over time.
- The 3D World Explorer needs WebGL; unsupported devices see a fallback and can still use other features.
- Free hosted demos (including Render free tier) may sleep when idle and are not a substitute for your own deployment.

---

## Contributing

Issues and pull requests are welcome.

Please keep course content and the optional AI Tutor as separate concerns, avoid committing secrets (`.env`, `google_client_secret.json`, local `users.db`), and prefer small, reviewable changes. See [`AGENTS.md`](AGENTS.md) for codebase conventions aimed at contributors.

---

## License

This project is licensed under the **MIT License**.
