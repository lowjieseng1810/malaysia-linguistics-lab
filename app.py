# ================= ENVIRONMENT (must load before Composer / tutor imports) =================

from dotenv import load_dotenv

load_dotenv()

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    flash,
    url_for,
    jsonify,
    abort
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.middleware.proxy_fix import ProxyFix

from authlib.integrations.flask_client import OAuth
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from database import (
    init_content_tables,
    seed_tutor_content,
    enrich_vocabulary_from_quiz_stems,
    sync_missing_vocabulary_from_course,
    import_verified_vocabulary_packs,
    vocabulary_counts_by_language,
    vocabulary_coverage_report,
    TARGET_VOCAB_PER_LANGUAGE,
)
from db import (
    describe_backend,
    get_db,
    get_sqlite_path,
    is_postgres,
    set_sqlite_path,
    startup_lock,
    table_columns,
)
from composer import (
    print_composer_startup_status,
    refresh_composer_enabled,
    run_composer_health_check,
)
from tutor_service import answer_tutor_query
from tutor_debug import (
    is_debug_enabled,
    database_diagnostics,
    find_duplicates,
    run_selfcheck,
)
from retrieval import (
    RetrievalError,
    dictionary_search,
    dictionary_word_by_id,
    dictionary_random_word,
)
from language_registry import get_language_keys, resolve_language, display_name
from quiz_service import (
    start_quiz_session,
    quiz_session_state,
    submit_quiz_session_answer,
    quiz_session_results,
    restart_quiz_session,
    clear_quiz_session,
    start_daily_quiz_session,
    daily_quiz_status,
)
from learning_memory import get_user_mastery_summary, get_quiz_history
from achievements import (
    init_achievement_tables,
    evaluate_achievements,
    get_achievements_gallery,
    pop_pending_achievement_notifications,
    mark_achievements_notified,
    set_explorer_milestone,
    record_dictionary_view,
    record_activity_day,
    get_activity_streak,
    get_mascot_preferences,
    update_mascot_preferences,
    collect_user_stats,
)
from heritage_facts import pick_heritage_fact


import hashlib
import json
import os
import random
import re
import requests
import secrets
import time


# Re-read composer flags now that .env is loaded
refresh_composer_enabled()


def _report_composer_on_startup():
    """Print status + health check once per process (supports flask reloader)."""
    # Parent reloader process sets WERKZEUG_RUN_MAIN to empty / unset then child to "true"
    if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        return
    if os.environ.get("_MMLE_COMPOSER_STARTUP_DONE") == "1":
        return
    os.environ["_MMLE_COMPOSER_STARTUP_DONE"] = "1"
    try:
        print_composer_startup_status()
        run_composer_health_check()
    except Exception as exc:
        print(f"Composer startup report failed: {exc}")


# ================= APP =================

app = Flask(__name__)


secret_key = os.getenv("SECRET_KEY")

if not secret_key:
    raise RuntimeError(
        "SECRET_KEY is missing. "
        "Add it to your .env file."
    )


app.config["SECRET_KEY"] = secret_key

_FLASK_ENV = (os.getenv("FLASK_ENV") or "development").strip().lower()
_FORCE_HTTPS = (os.getenv("FORCE_HTTPS") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_TRUST_PROXY = (os.getenv("TRUST_PROXY") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Reject known placeholder secrets when deploying as production.
if _FLASK_ENV == "production" and secret_key.strip().lower() in {
    "change-me-to-a-long-random-value",
    "change-me",
    "secret",
    "dev",
}:
    raise RuntimeError(
        "SECRET_KEY looks like a placeholder. "
        "Set a long random value before production deployment."
    )

# Prefer HTTPS URL generation when forced (reverse-proxy / production TLS).
if _FORCE_HTTPS:
    app.config["PREFERRED_URL_SCHEME"] = "https"

# When behind Nginx/Cloudflare/etc., honour X-Forwarded-* so request.is_secure
# and url_for(_external=True) reflect the public HTTPS scheme.
if _TRUST_PROXY:
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_prefix=1,
    )

# Composer readiness (also re-run from __main__)
_report_composer_on_startup()


# ================= CSRF =================

csrf = CSRFProtect()

csrf.init_app(app)

app.jinja_env.globals["csrf_token"] = generate_csrf

# ================= LOGIN RATE LIMIT =================

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[]
)


# ================= SESSION SECURITY =================

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Secure cookies only when HTTPS is forced or the deployment is marked
# production. Keep False for local HTTP so sessions remain usable.
app.config["SESSION_COOKIE_SECURE"] = _FORCE_HTTPS or (_FLASK_ENV == "production")
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 14
app.config["SESSION_REFRESH_EACH_REQUEST"] = True


def _establish_login_session(user_id, username):
    """Replace the session on login to prevent session fixation."""
    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    session.permanent = True


# ================= DATABASE =================

# Production: DATABASE_URL → PostgreSQL. Local: SQLite under project root
# (optional DATABASE_PATH). Never log credentials.
if not is_postgres():
    set_sqlite_path(get_sqlite_path(app.root_path))
print(f"[db] Backend: {describe_backend()}")


# ================= GOOGLE OAUTH =================

GOOGLE_CLIENT_SECRET_FILE = os.path.join(
    app.root_path,
    "google_client_secret.json"
)


oauth = OAuth(app)


def register_google_oauth():

    if not os.path.exists(
        GOOGLE_CLIENT_SECRET_FILE
    ):

        print(
            "Google OAuth secret file "
            "was not found."
        )

        return


    with open(
        GOOGLE_CLIENT_SECRET_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        google_config = json.load(
            file
        )


    web_config = google_config.get(
        "web",
        {}
    )


    client_id = web_config.get(
        "client_id"
    )


    client_secret = web_config.get(
        "client_secret"
    )


    if (
        not client_id
        or not client_secret
    ):

        print(
            "Google OAuth configuration "
            "is incomplete."
        )

        return


    oauth.register(

        name="google",

        client_id=client_id,

        client_secret=client_secret,

        server_metadata_url=(
            "https://accounts.google.com/"
            ".well-known/"
            "openid-configuration"
        ),

        client_kwargs={
            "scope":
            "openid email profile"
        }

    )


register_google_oauth()


# ================= AI TUTOR FEATURE FLAG =================

AI_TUTOR_API_KEY = os.getenv("AI_TUTOR_API_KEY")

AI_TUTOR_MODEL = os.getenv("AI_TUTOR_MODEL")

AI_TUTOR_ENABLED = bool(
    AI_TUTOR_API_KEY
    and AI_TUTOR_MODEL
)


# ================= DATABASE FUNCTIONS =================

def init_db():

    conn = get_db()


    # ================= USERS TABLE =================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER
            PRIMARY KEY
            AUTOINCREMENT,

            username TEXT
            UNIQUE
            NOT NULL,

            password TEXT
            NOT NULL

        )
    """)


    user_columns = table_columns(conn, "users")


    if "provider" not in user_columns:

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN provider TEXT
            DEFAULT 'local'
        """)


    if "provider_user_id" not in user_columns:

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN provider_user_id TEXT
        """)


    if "email" not in user_columns:

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN email TEXT
        """)


    conn.execute("""
        UPDATE users

        SET provider = 'local'

        WHERE provider IS NULL
           OR provider = ''
    """)


    conn.execute("""
        CREATE UNIQUE INDEX
        IF NOT EXISTS
        idx_users_provider_identity

        ON users (
            provider,
            provider_user_id
        )

        WHERE provider_user_id
        IS NOT NULL
    """)


    conn.execute("""
        CREATE INDEX
        IF NOT EXISTS
        idx_users_email

        ON users (
            email
        )
    """)


    # ================= PROGRESS TABLE =================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress (

            id INTEGER
            PRIMARY KEY
            AUTOINCREMENT,

            user_id INTEGER
            NOT NULL,

            lang_key TEXT
            NOT NULL,

            level_num INTEGER
            NOT NULL,

            completed INTEGER
            NOT NULL
            DEFAULT 0,

            UNIQUE(
                user_id,
                lang_key,
                level_num
            ),

            FOREIGN KEY (
                user_id
            )

            REFERENCES users(id)
            ON DELETE CASCADE

        )
    """)


    # ================= LESSON PROGRESS TABLE =================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS lesson_progress (

            id INTEGER
            PRIMARY KEY
            AUTOINCREMENT,

            user_id INTEGER
            NOT NULL,

            lang_key TEXT
            NOT NULL,

            level_num INTEGER
            NOT NULL,

            current_step INTEGER
            NOT NULL
            DEFAULT 0,

            UNIQUE(
                user_id,
                lang_key,
                level_num
            ),

            FOREIGN KEY (
                user_id
            )

            REFERENCES users(id)
            ON DELETE CASCADE

        )
    """)


    # ================= PASSWORD RESET TABLE =================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (

            id INTEGER
            PRIMARY KEY
            AUTOINCREMENT,

            user_id INTEGER
            NOT NULL,

            token_hash TEXT
            UNIQUE
            NOT NULL,

            created_at INTEGER
            NOT NULL,

            used INTEGER
            NOT NULL
            DEFAULT 0,

            FOREIGN KEY (
                user_id
            )

            REFERENCES users(id)
            ON DELETE CASCADE

        )
    """)


    # ================= SAVED WORDS (FAVORITES) TABLE =================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_words (

            id INTEGER
            PRIMARY KEY
            AUTOINCREMENT,

            user_id INTEGER
            NOT NULL,

            vocabulary_id INTEGER
            NOT NULL,

            lang_key TEXT
            NOT NULL,

            created_at INTEGER
            NOT NULL,

            UNIQUE(
                user_id,
                vocabulary_id
            ),

            FOREIGN KEY (
                user_id
            )

            REFERENCES users(id)
            ON DELETE CASCADE

        )
    """)

    conn.execute("""
        CREATE INDEX
        IF NOT EXISTS
        idx_saved_words_user

        ON saved_words (
            user_id,
            lang_key
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS heritage_passport (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lang_key TEXT NOT NULL,
            discovered_at INTEGER NOT NULL,
            UNIQUE(user_id, lang_key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_heritage_passport_user
        ON heritage_passport (user_id)
    """)

    # Achievements, activity days, dictionary views, mascot prefs
    init_achievement_tables(conn)

    # ================= TUTOR CONTENT TABLES =================
    init_content_tables(conn)

    conn.commit()

    conn.close()

# ================= LANGUAGE DATA =================

LANGUAGES = {

    "iban": {
        "display_name": "Iban",
        "blurb": "Explore the language and living heritage of Iban communities in Sarawak.",
        "region": "Sarawak, Malaysia",
        "community": "Iban communities",
        "eyebrow": "Language of Sarawak",

        "about_title": "A major indigenous language of Sarawak",
        "about": (
            "Iban is closely connected with Iban communities across Sarawak. "
            "The language forms an important part of communication, cultural "
            "expression, storytelling, and community identity."
        ),

        "speakers_title": "The Iban community",
        "speakers": (
            "Iban is spoken within Iban communities and continues to connect "
            "people across generations. The language is part of a wider living "
            "heritage that includes oral traditions, stories, songs, customs, "
            "and everyday communication."
        ),

        "location_title": "Across Sarawak",
        "location": (
            "Iban is strongly associated with Sarawak and is used by "
            "communities in different parts of the state."
        ),

        "preservation_title": "Keeping language and knowledge connected",
        "preservation": (
            "Language can carry cultural memory, local knowledge, expressions, "
            "and stories. Supporting responsible learning and documentation "
            "can help more people engage with this heritage."
        ),

        "verification_status": "Under Review",
        "verification_note": (
            "Learning content should be reviewed with reliable sources and "
            "community contributors before being marked as community verified."
        ),

               "gallery": [
            {
                "title": "Community Life",
                "caption": (
                    "An Iban family sharing dinner with visiting travellers "
                    "at a longhouse settlement near Bintulu, offering a glimpse "
                    "of everyday community life and hospitality."
                ),
                "image_url": "/static/images/iban_community.jpg",
                "source_name": (
                    "Photo by Pavel Kirillov · CC BY-SA 2.0"
                ),
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    "File:Dinner_with_Iban_family_(8035179786).jpg"
                )
            },
            {
                "title": "Culture & Heritage",
                "caption": (
                    "Ngajat is a traditional Iban dance that reflects "
                    "cultural expression, movement, and living heritage."
                ),
                "image_url": "/static/images/iban-ngajat-dance.png",
                "source_name": (
                    "John Ragai / Wikimedia Commons · CC BY 2.0"
                ),
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    "File:Ngajat,_the_Iban%27s_Warrior_Dance.jpg"
                )
            },
            {
                "title": "Language and Place",
                "caption": (
                    "A map showing the geographical distribution of the "
                    "Iban language across parts of Borneo."
                ),
                "image_url": (
                    "/static/images/iban_language_distribution.svg"
                ),
                "source_name": (
                    "Map by Nyilvoskt · CC BY-SA 4.0"
                ),
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    "File:Iban_language_distribution.svg"
                )
            }
        ],
        "videos": [
    {
        "title": "Erik & The Iban",
        "creator": "Stash Movies & TV",
        "description": (
            "A documentary following Dr. Erik Jensen as he returns to Borneo "
            "to revisit the Iban community he knew in the 1960s and explore "
            "how community life and culture have changed in the 21st century."
        ),
        "embed_url": "https://www.youtube.com/embed/TceW514HsQ0",
        "source_url": "https://www.youtube.com/watch?v=TceW514HsQ0"
    }
],

        "sources": [
            {
                "title": "Language background source",
                "organization": "Source to be added",
                "url": ""
            }
        ]
    },


    "kadazan-dusun": {
        "display_name": "Kadazan-Dusun",
        "blurb": "Explore a major indigenous language tradition connected with communities in Sabah.",
        "region": "Sabah, Malaysia",
        "community": "Kadazan and Dusun communities",
        "eyebrow": "Language of Sabah",

        "about_title": "An indigenous language tradition of Sabah",
        "about": (
            "Kadazan-Dusun is associated with Kadazan and Dusun communities "
            "in Sabah. It forms part of the state's diverse indigenous "
            "linguistic and cultural heritage."
        ),

        "speakers_title": "Kadazan and Dusun communities",
        "speakers": (
            "The language tradition is connected with communities that have "
            "their own local histories, identities, traditions, and varieties "
            "of speech across Sabah."
        ),

        "location_title": "Across Sabah",
        "location": (
            "Kadazan-Dusun is associated with communities in several areas "
            "of Sabah. Language use and local varieties may differ between places."
        ),

        "preservation_title": "Supporting learning across generations",
        "preservation": (
            "Accessible and carefully reviewed digital resources can support "
            "language learning while increasing awareness of Sabah's indigenous "
            "linguistic and cultural heritage."
        ),

        "verification_status": "Under Review",
        "verification_note": (
            "Course content is currently being developed and should be checked "
            "with reliable sources and community contributors before being "
            "marked as community verified."
        ),

                "gallery": [
            {
                "title": "Community Life",
                "caption": (
                    "Members of the Dusun Lotud community in Tuaran, Sabah, "
                    "reflecting one of the distinct communities within the "
                    "wider Kadazan-Dusun cultural and linguistic landscape."
                ),
                "image_url": (
                    "/static/images/kadazan_dusun_community.jpg"
                ),
                "source_name": (
                    "Wikimedia Commons contributor · "
                    "see source page for licence"
                ),
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    "File:Dusun_Lotud_Tuaran.jpg"
                )
            },
            {
                "title": "Culture & Heritage",
                "caption": (
                    "A traditional dance performance at Monsopiad Cultural "
                    "Village, reflecting the living cultural heritage of "
                    "Kadazan-Dusun communities in Sabah."
                ),
                "image_url": (
                    "/static/images/kadazan_dusun_dance.jpg"
                ),
                "source_name": (
                    "CEphoto, Uwe Aranas · CC BY-SA 3.0"
                ),
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    "File:KgKuaiKandazon_Sabah_Monsopiad-Cultural-Village-"
                    "DansePerformance-01.jpg"
                )
            },
            {
                "title": "Land & Living Heritage",
                "caption": (
                    "A Dusun family harvesting rice in Sabah, reflecting "
                    "the close relationship between community life, the land, "
                    "and living agricultural traditions."
                ),
                "image_url": (
                    "/static/images/kadazan_dusun_rice_harvest.jpg"
                ),
                "source_name": (
                    "CEphoto, Uwe Aranas · CC BY-SA 3.0"
                ),
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    "File:Kudat-District_Rice-Harvesting-03.jpg"
                )
            }
        ],
                "videos": [
            {
                "title": (
                    "The Kadazandusun Story: "
                    "Through the Eyes of a People"
                ),
                "creator": "Documentary feature",
                "description": (
                    "A documentary exploring the story, identity, heritage, "
                    "and cultural experiences of the Kadazandusun people "
                    "of Sabah."
                ),
                "embed_url": (
                    "https://www.youtube.com/embed/FkXMv2_GPtE"
                ),
                "source_url": (
                    "https://www.youtube.com/watch?v=FkXMv2_GPtE"
                )
            }
        ],

        "sources": [
            {
                "title": "Language background source",
                "organization": "Source to be added",
                "url": ""
            }
        ]
    },

        "bidayuh": {
        "display_name": "Bidayuh",
        "blurb": "Explore the diverse language heritage of Bidayuh communities in Sarawak.",
        "region": "Sarawak, Malaysia",
        "community": "Bidayuh communities",
        "eyebrow": "Language Heritage of Sarawak",

        "about_title": "A diverse language heritage",
        "about": (
            "Bidayuh language heritage is connected with Bidayuh communities "
            "in Sarawak. It includes regional varieties, making careful local "
            "context important when presenting learning materials."
        ),

        "speakers_title": "Bidayuh communities",
        "speakers": (
            "Bidayuh communities have distinct local histories and traditions. "
            "Different communities may use different language varieties, so "
            "documentation should clearly identify the variety being presented."
        ),

        "location_title": "Southwestern Sarawak",
        "location": (
            "Bidayuh communities are especially associated with areas of "
            "southwestern Sarawak and surrounding regions."
        ),

        "preservation_title": "Respecting linguistic diversity",
        "preservation": (
            "Responsible documentation should make language differences visible "
            "rather than treating all Bidayuh varieties as one completely "
            "uniform form of speech."
        ),

        "verification_status": "Under Review",
        "verification_note": (
            "The specific Bidayuh variety used in future lessons should be "
            "clearly identified and reviewed with appropriate speakers, "
            "contributors, and reliable sources."
        ),

                "gallery": [
            {
                "title": "Historical Community Life",
                "caption": (
                    "A historical artwork depicting a Bidayuh village "
                    "community. This is an artistic representation from "
                    "an earlier period, not a photograph of present-day "
                    "Bidayuh life. It offers a historical view of how "
                    "Bidayuh community and village life were represented "
                    "at the time."
                ),
                "image_url": (
                    "/static/images/bidayuh_community.jpg"
                ),
                "source_name": (
                    "Historical artwork · Wikimedia Commons"
                ),
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    "File:Bethune_Bidayuh_village.jpg"
                )
            },
            {
                "title": "Craft & Living Heritage",
                "caption": (
                    "Traditional rope-making reflects practical knowledge "
                    "and craft skills connected with everyday life and "
                    "living heritage in Bidayuh communities."
                ),
                "image_url": (
                    "/static/images/bidayuh_rope_making.jpg"
                ),
                "source_name": (
                    "Wikimedia Commons · see source page for licence"
                ),
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    "File:Making_rope,_the_traditional_way_(103248059).jpg"
                )
            },
            {
                "title": "Place & Living Heritage",
                "caption": (
                    "A traditional Bidayuh roundhouse in Sarawak, "
                    "reflecting the relationship between community, "
                    "place, architecture, and living heritage."
                ),
                "image_url": (
                    "/static/images/bidayuh_roundhouse.jpg"
                ),
                "source_name": (
                    "Wikimedia Commons · see source page for licence"
                ),
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    "File:A_traditional_Bidayuh_roundhouse.jpg"
                )
            }
        ],
               "videos": [
            {
                "title": (
                    "Dawn of the Bidayuh | "
                    "Journey of the Bidayuh | Episode 1"
                ),
                "creator": "TVS Entertainment",
                "description": (
                    "The first episode of Journey of the Bidayuh, "
                    "exploring Bidayuh people, community, identity, "
                    "heritage, and cultural life in Sarawak."
                ),
                "embed_url": (
                    "https://www.youtube.com/embed/v0sji5JISdc"
                ),
                "source_url": (
                    "https://www.youtube.com/watch?v=v0sji5JISdc"
                )
            }
        ],

        "sources": [
            {
                "title": "Language background source",
                "organization": "Source to be added",
                "url": ""
            }
        ]
    },


    "mah-meri": {
        "display_name": "Mah Meri",

        "blurb": (
            "Explore a living Indigenous language connected with "
            "Mah Meri communities in coastal Selangor."
        ),

        "region": "Coastal Selangor, Peninsular Malaysia",

        "community": "Mah Meri communities",

        "eyebrow": "Language of Coastal Selangor",

        "about_title": (
            "A distinctive Indigenous language of Peninsular Malaysia"
        ),

        "about": (
            "Mah Meri is an Austroasiatic language belonging to the "
            "Southern Aslian branch. It is part of the linguistic heritage "
            "of the Mah Meri, one of the Orang Asli peoples of Peninsular "
            "Malaysia. The language carries knowledge, relationships, "
            "expressions, and ways of understanding community life."
        ),

        "speakers_title": "The Mah Meri community",

        "speakers": (
            "Mah Meri is spoken within Mah Meri communities in Peninsular "
            "Malaysia. Language is closely connected with community identity "
            "and with knowledge passed between generations. The community is "
            "also widely known for distinctive cultural traditions, but the "
            "language should be understood as a living part of everyday "
            "community heritage rather than only through cultural objects."
        ),

        "location_title": "Coastal communities of Selangor",

        "location": (
            "Mah Meri is especially associated with coastal areas of "
            "Selangor, including communities on and around Carey Island, "
            "also known locally as Pulau Carey. Its coastal setting makes "
            "the language geographically distinctive among the Aslian "
            "languages of Peninsular Malaysia."
        ),

        "preservation_title": (
            "Keeping a living language connected across generations"
        ),

        "preservation": (
            "The future of a language depends not only on documentation, "
            "but also on continued use, learning, and transmission between "
            "generations. Research on Mah Meri has raised concerns about "
            "language shift, particularly as Malay becomes more dominant "
            "in some parts of everyday life. Responsible digital resources "
            "can support awareness, but learning content should be developed "
            "carefully with reliable linguistic sources and community input."
        ),

        "verification_status": "Under Review",

        "verification_note": (
            "Mah Meri learning content is being developed with a source-first "
            "approach. Language expressions and lesson material should be "
            "checked against reliable linguistic documentation and, where "
            "possible, reviewed with Mah Meri speakers or community "
            "contributors before being marked as community verified."
        ),

        "gallery": [
    {
        "title": "Community Life",
        "caption": (
            "A glimpse of everyday life on Pulau Carey, "
            "one of the places closely associated with Mah Meri communities."
        ),
        "image_url": "/static/images/mah_meri_community.jpg",
        "source_name": "Photo by Amirul Hilmi Ariffin · CC BY 2.0",
        "source_url": "https://commons.wikimedia.org/wiki/File:Orang_asli_pulau_carey_banting_(3657468274).jpg"
    },
    {
        "title": "Living Heritage",
        "caption": (
            "A Mah Meri carved mask, reflecting one aspect of the "
            "community's distinctive woodcarving heritage."
        ),
        "image_url": "/static/images/mah_meri_mask.jpg",
        "source_name": "Photo by Tessa Houghton · CC BY 2.0",
        "source_url": "https://commons.wikimedia.org/wiki/File:Mah_Meri_spider_spirit_mask_(6346812079).jpg"
    },
    {
        "title": "Language and Place",
        "caption": (
            "A research map showing the geographical locations of "
            "Orang Asli communities included in a published study, "
            "including Mah Meri communities in Selangor."
        ),
        "image_url": "/static/images/mah_meri_location_map.jpg",
        "source_name": "Research figure · CC BY 4.0",
        "source_url": "https://commons.wikimedia.org/wiki/File:Geographical_location_of_Orang_Asli_communities_recruited_in_the_study.jpg"
    }
],

       "videos": [
    {
        "title": "Mah Meri Community Video",
        "creator": "YouTube",
        "description": (
            "A video offering visual and cultural context connected with "
            "the Mah Meri community and the living heritage surrounding "
            "the language."
        ),
        "embed_url": "https://www.youtube.com/embed/4CfopBe67PU",
        "source_url": "https://www.youtube.com/watch?v=4CfopBe67PU"
    }
],

        "sources": [
            {
                "title": "Mah Meri language documentation",
                "organization": "Linguistic research source to be added",
                "url": ""
            },
            {
                "title": "Research on Mah Meri language vitality",
                "organization": "Academic research source to be added",
                "url": ""
            }
        ]
    }
}


LEVEL_TITLES = {
    1: "First Meeting",
    2: "People Around You",
    3: "Everyday Encounters"
}


# ================= LANGUAGE COMPARISON METADATA =================
#
# These are lightweight, general reference facts that are not already
# captured anywhere else in LANGUAGES / COURSE_DATA. Anything that already
# exists elsewhere (name, region, speakers, verification/vitality status,
# greetings) is reused/derived from LANGUAGES and COURSE_DATA instead of
# being duplicated here.

LANGUAGE_FAMILY = {
    "iban": "Austronesian (Malayo-Polynesian, Malayic)",
    "kadazan-dusun": "Austronesian (Malayo-Polynesian, Dusunic)",
    "bidayuh": "Austronesian (Malayo-Polynesian, Land Dayak)",
    "mah-meri": "Austroasiatic (Aslian, Southern Aslian)"
}

LANGUAGE_WRITING_SYSTEM = "Latin-based (Romanized) script"


def get_language_family_tree(current_lang_key):
    """
    Builds a lightweight Root Family -> Branch -> Languages tree purely by
    parsing the existing LANGUAGE_FAMILY strings (e.g.
    "Austronesian (Malayo-Polynesian, Malayic)" -> root "Austronesian",
    branch "Malayic"). No new family data is introduced here - languages
    that have no entry in LANGUAGE_FAMILY are placed in "unclassified" and
    rendered with "Relationship currently under research." instead.
    """

    tree = {}
    unclassified = []

    for lang_key, language in LANGUAGES.items():

        display_name = language.get(
            "display_name",
            lang_key
        )

        family_text = LANGUAGE_FAMILY.get(lang_key)

        if not family_text:
            unclassified.append({
                "lang_key": lang_key,
                "display_name": display_name,
                "is_current": lang_key == current_lang_key
            })
            continue

        root = family_text.split("(")[0].strip()
        branch = root

        if "(" in family_text:
            inside = family_text.split("(", 1)[1].rstrip(")")
            parts = [
                part.strip()
                for part in inside.split(",")
                if part.strip()
            ]

            if parts:
                branch = parts[-1]

        tree.setdefault(
            root,
            {}
        ).setdefault(
            branch,
            []
        ).append({
            "lang_key": lang_key,
            "display_name": display_name,
            "is_current": lang_key == current_lang_key
        })

    return {
        "roots": tree,
        "unclassified": unclassified
    }


# ================= VITALITY METER SCALE =================
#
# This maps *known* UNESCO-style vitality wording to a generic 10-segment
# meter + colour + one-line explanation for display purposes only. It does
# not assign a category to any language - it is only consulted with
# whatever "verification_status" text a language already has in LANGUAGES.
# Since every language currently stores "Under Review", the meter falls
# back to the honest "Data currently under review." state below for all of
# them today; nothing here invents a classification for a specific language.

VITALITY_SCALE = {
    "safe": {
        "filled": 10,
        "css_class": "safe",
        "explanation": (
            "Spoken by all generations with unbroken transmission."
        )
    },
    "vulnerable": {
        "filled": 8,
        "css_class": "vulnerable",
        "explanation": (
            "Most children speak it, but often only in certain settings."
        )
    },
    "definitely endangered": {
        "filled": 6,
        "css_class": "definitely-endangered",
        "explanation": (
            "Children no longer learn it as a first language at home."
        )
    },
    "severely endangered": {
        "filled": 4,
        "css_class": "severely-endangered",
        "explanation": (
            "Spoken mainly by grandparents and older generations."
        )
    },
    "critically endangered": {
        "filled": 2,
        "css_class": "critically-endangered",
        "explanation": (
            "Spoken by only a few elderly speakers, used infrequently."
        )
    },
    "extinct": {
        "filled": 0,
        "css_class": "extinct",
        "explanation": "No remaining speakers."
    }
}

VITALITY_TOTAL_SEGMENTS = 10


def get_vitality_meter(vitality_status):
    lookup_key = (vitality_status or "").strip().lower()

    scale = VITALITY_SCALE.get(lookup_key)

    if not scale:
        # "Under Review" (or any status we don't recognise) is not the
        # same as "no data" - leaving the meter at 0/10 looked like the
        # feature was broken. We show a clearly-labelled estimate instead
        # of a real classification: a mid-scale yellow meter with an
        # "Estimated" badge, so it's obvious this is a placeholder and not
        # a fabricated UNESCO category.
        return {
            "available": False,
            "estimated": True,
            "filled_segments": 5,
            "total_segments": VITALITY_TOTAL_SEGMENTS,
            "css_class": "estimated",
            "explanation": "Data currently under review."
        }

    return {
        "available": True,
        "estimated": False,
        "filled_segments": scale["filled"],
        "total_segments": VITALITY_TOTAL_SEGMENTS,
        "css_class": scale["css_class"],
        "explanation": scale["explanation"]
    }


# ================= COURSE DATA =================

COURSE_DATA = {'iban': {1: {'steps': [{'type': 'scene',
                         'label': 'Journey 01',
                         'journeyNumber': 'A Living Language Journey',
                         'title': 'A First Meeting',
                         'instruction': 'You arrive and meet someone for the first time.',
                         'description': 'Listen to the language, work out what it means, and '
                                        'respond as the meeting unfolds.',
                         'path': ['Encounter', 'Understand', 'Respond'],
                         'buttonText': 'Begin Encounter',
                         'actionHint': 'Enter the conversation when you are ready.'},
                        {'type': 'discover',
                         'label': 'Encounter',
                         'title': 'Someone welcomes you',
                         'instruction': 'What do you think this expression means?',
                         'speaker': 'Someone',
                         'expression': 'Selamat datai',
                         'options': ['Welcome', 'How are you?', 'What is your name?'],
                         'correctIndex': 0,
                         'meaning': 'Welcome',
                         'context': 'A welcoming expression used when someone arrives.',
                         'hint': 'Think about what someone might say when you arrive.',
                         'correctFeedback': 'You worked out the meaning from the moment.',
                         'wrongFeedback': 'Now you understand what the welcome means.',
                         'continueText': 'Continue the Meeting'},
                        {'type': 'discover',
                         'label': 'The Meeting Continues',
                         'title': 'They ask you something',
                         'instruction': 'What is happening in the conversation?',
                         'speaker': 'Someone',
                         'expression': 'Nama berita nuan?',
                         'options': ['They are asking how you are.',
                                     'They are asking your name.',
                                     'They are saying goodbye.'],
                         'correctIndex': 0,
                         'meaning': 'How are you?',
                         'context': 'A basic expression used to ask how someone is.',
                         'hint': 'Think about what often comes after a welcome.',
                         'correctFeedback': 'You followed the conversation.',
                         'wrongFeedback': 'Now the direction of the conversation is clear.',
                         'continueText': 'Your Turn'},
                        {'type': 'respond',
                         'label': 'Your Turn',
                         'title': 'Respond to the question',
                         'instruction': 'Choose the response that fits this moment.',
                         'speaker': 'Someone',
                         'userLabel': 'You',
                         'prompt': 'Nama berita nuan?',
                         'promptMeaning': 'How are you?',
                         'options': ['Manah', 'Selamat datai', 'Nama aku ...'],
                         'correctIndex': 0,
                         'responseMeaning': 'Good / Fine',
                         'hint': 'Choose the expression that describes how you are.',
                         'successMessage': 'You completed your first exchange in Iban.',
                         'correctFeedback': 'Your response fits the conversation.',
                         'wrongFeedback': 'That expression does not answer how you are.',
                         'continueText': 'Continue the Meeting'},
                        {'type': 'discover',
                         'label': 'A New Question',
                         'title': 'The conversation becomes personal',
                         'instruction': 'What are they likely asking now?',
                         'speaker': 'Someone',
                         'expression': 'Sapa nama nuan?',
                         'options': ['What is your name?', 'Where are you going?', 'How are you?'],
                         'correctIndex': 0,
                         'meaning': 'What is your name?',
                         'context': 'A question used when asking someone their name.',
                         'hint': 'You have already greeted each other. Think about what often '
                                 'comes next.',
                         'correctFeedback': 'You understood the next moment in the meeting.',
                         'wrongFeedback': 'Now you know they are asking for your name.',
                         'continueText': 'Introduce Yourself'},
                        {'type': 'respond',
                         'label': 'Introduce Yourself',
                         'title': 'Complete the introduction',
                         'instruction': 'Choose the response that answers the question.',
                         'speaker': 'Someone',
                         'userLabel': 'You',
                         'prompt': 'Sapa nama nuan?',
                         'promptMeaning': 'What is your name?',
                         'options': ['Nama aku ...', 'Manah', 'Selamat datai'],
                         'correctIndex': 0,
                         'responseMeaning': 'My name is ...',
                         'hint': 'Choose the expression that begins your introduction.',
                         'successMessage': 'You can now begin introducing yourself.',
                         'correctFeedback': 'You answered the question with an introduction.',
                         'wrongFeedback': 'That expression does not introduce your name.',
                         'continueText': 'Enter the Final Encounter'},
                        {'type': 'conversation',
                         'label': 'Final Encounter',
                         'title': 'A First Meeting',
                         'instruction': 'Complete the conversation one moment at a time.',
                         'turns': [{'speaker': 'Someone',
                                    'userLabel': 'You',
                                    'prompt': 'Selamat datai',
                                    'options': ['Selamat datai', 'Manah', 'Nama aku ...'],
                                    'correctIndex': 0,
                                    'correctFeedback': 'You return the welcome.',
                                    'wrongFeedback': 'Choose the response that fits the welcome.'},
                                   {'speaker': 'Someone',
                                    'userLabel': 'You',
                                    'prompt': 'Nama berita nuan?',
                                    'options': ['Nama aku ...', 'Manah', 'Sapa nama nuan?'],
                                    'correctIndex': 1,
                                    'correctFeedback': 'You answer how you are.',
                                    'wrongFeedback': 'Choose the response that answers how you '
                                                     'are.'},
                                   {'speaker': 'Someone',
                                    'userLabel': 'You',
                                    'prompt': 'Sapa nama nuan?',
                                    'options': ['Selamat datai', 'Manah', 'Nama aku ...'],
                                    'correctIndex': 2,
                                    'correctFeedback': 'You complete your introduction.',
                                    'wrongFeedback': 'Choose the expression that introduces your '
                                                     'name.'}],
                         'completeLabel': 'First Meeting Complete',
                         'completeMessage': 'You followed and responded to a complete first '
                                            'meeting.',
                         'successMessage': 'You stayed with the conversation from beginning to '
                                           'end.',
                         'continueText': 'Complete Journey'}]},
          2: {'steps': [{'type': 'vocabulary',
                         'title': 'Father',
                         'instruction': 'Learn a basic Iban family word.',
                         'word': 'Apai',
                         'meaning': 'Father',
                         'note': 'Apai means father.'},
                        {'type': 'vocabulary',
                         'title': 'Mother',
                         'instruction': 'Learn another basic family word.',
                         'word': 'Indai',
                         'meaning': 'Mother',
                         'note': 'Indai means mother.'},
                        {'type': 'vocabulary',
                         'title': 'Child',
                         'instruction': 'Study this common family word.',
                         'word': 'Anak',
                         'meaning': 'Child',
                         'note': 'Anak means child or offspring.'},
                        {'type': 'vocabulary',
                         'title': 'Friend',
                         'instruction': 'Learn how to say friend in Iban.',
                         'word': 'Kaban',
                         'meaning': 'Friend',
                         'note': 'Kaban is a common word for friend.'},
                        {'type': 'vocabulary',
                         'title': 'Eat',
                         'instruction': 'Learn a useful everyday action word.',
                         'word': 'Makai',
                         'meaning': 'Eat',
                         'note': 'Makai is used for eating.'},
                        {'type': 'quiz',
                         'question': 'What does "Kaban" mean?',
                         'instruction': 'Choose the correct answer.',
                         'options': ['Eat', 'Father', 'Friend', 'Child'],
                         'correctIndex': 2,
                         'hint': 'Think about a person you enjoy spending time with.',
                         'correctFeedback': 'Correct. "Kaban" means "Friend."',
                         'wrongFeedback': 'Not quite. "Kaban" means "Friend."'},
                        {'type': 'quiz',
                         'question': 'Which word means "Eat"?',
                         'instruction': 'Choose the correct Iban word.',
                         'options': ['Anak', 'Makai', 'Indai', 'Apai'],
                         'correctIndex': 1,
                         'hint': 'The correct word begins with the letter M.',
                         'correctFeedback': 'Correct. "Makai" means "Eat."',
                         'wrongFeedback': 'Not quite. The correct answer is "Makai."'},
                        {'type': 'quiz',
                         'question': 'What does "Apai" mean?',
                         'instruction': 'Choose the correct answer.',
                         'options': ['Mother', 'Father', 'Friend', 'Child'],
                         'correctIndex': 1,
                         'hint': 'Think about one of the two parent words you learned.',
                         'correctFeedback': 'Correct. "Apai" means "Father."',
                         'wrongFeedback': 'Not quite. "Apai" means "Father."'},
                        {'type': 'quiz',
                         'question': 'Which Iban word means "Mother"?',
                         'instruction': 'Choose the correct answer.',
                         'options': ['Indai', 'Anak', 'Kaban', 'Makai'],
                         'correctIndex': 0,
                         'hint': 'The correct word begins with the letter I.',
                         'correctFeedback': 'Correct. "Indai" means "Mother."',
                         'wrongFeedback': 'Not quite. The correct answer is "Indai."'}]},
          3: {'steps': [{'type': 'vocabulary',
                         'title': 'Where are you going?',
                         'instruction': 'Study this useful everyday question.',
                         'word': 'Kini ke nuan?',
                         'meaning': 'Where are you going?',
                         'note': 'A useful question for everyday conversation.'},
                        {'type': 'vocabulary',
                         'title': 'Where are you from?',
                         'instruction': 'Learn how to ask where someone comes from.',
                         'word': 'Ari ni penatai nuan?',
                         'meaning': 'Where are you from?',
                         'note': 'Use this when getting to know someone.'},
                        {'type': 'vocabulary',
                         'title': 'Who is with you?',
                         'instruction': 'Study this simple question.',
                         'word': 'Sapa enggau nuan?',
                         'meaning': 'Who is with you?',
                         'note': 'Study the full expression before continuing.'},
                        {'type': 'vocabulary',
                         'title': 'I am with...',
                         'instruction': 'Learn a simple sentence pattern.',
                         'word': 'Aku enggau ...',
                         'meaning': 'I am with ...',
                         'note': 'Add a person after the expression.'},
                        {'type': 'vocabulary',
                         'title': 'Please wait',
                         'instruction': 'Learn a useful short expression.',
                         'word': 'Anang guai',
                         'meaning': 'Wait a second',
                         'note': 'A useful expression when asking someone to wait.'},
                        {'type': 'quiz',
                         'question': 'Which expression means "Who is with you?"',
                         'instruction': 'Choose the correct Iban expression.',
                         'options': ['Kini ke nuan?',
                                     'Anang guai',
                                     'Sapa enggau nuan?',
                                     'Aku enggau ...'],
                         'correctIndex': 2,
                         'hint': 'Look for the expression beginning with "Sapa".',
                         'correctFeedback': 'Correct. "Sapa enggau nuan?" means "Who is with you?"',
                         'wrongFeedback': 'Not quite. The correct expression is "Sapa enggau '
                                          'nuan?"'},
                        {'type': 'quiz',
                         'question': 'What does "Anang guai" mean?',
                         'instruction': 'Choose the correct answer.',
                         'options': ['Where are you going?',
                                     'Wait a second',
                                     'Who is with you?',
                                     'Where are you from?'],
                         'correctIndex': 1,
                         'hint': 'Think of something you say when you need someone to stop '
                                 'briefly.',
                         'correctFeedback': 'Correct. "Anang guai" means "Wait a second."',
                         'wrongFeedback': 'Not quite. "Anang guai" means "Wait a second."'},
                        {'type': 'quiz',
                         'question': 'How do you ask "Where are you going?"',
                         'instruction': 'Choose the correct Iban expression.',
                         'options': ['Aku enggau ...',
                                     'Ari ni penatai nuan?',
                                     'Kini ke nuan?',
                                     'Sapa enggau nuan?'],
                         'correctIndex': 2,
                         'hint': 'The correct expression begins with "Kini".',
                         'correctFeedback': 'Correct. "Kini ke nuan?" means "Where are you going?"',
                         'wrongFeedback': 'Not quite. The correct expression is "Kini ke nuan?"'},
                        {'type': 'quiz',
                         'question': 'Which expression can begin the sentence "I am with ..."?',
                         'instruction': 'Choose the correct answer.',
                         'options': ['Anang guai',
                                     'Aku enggau ...',
                                     'Kini ke nuan?',
                                     'Ari ni penatai nuan?'],
                         'correctIndex': 1,
                         'hint': 'Look for the expression beginning with "Aku".',
                         'correctFeedback': 'Correct. "Aku enggau ..." means "I am with ..."',
                         'wrongFeedback': 'Not quite. The correct expression is "Aku enggau ..."'},
                        {'type': 'quiz',
                         'question': 'What does "Ari ni penatai nuan?" mean?',
                         'instruction': 'Choose the correct answer.',
                         'options': ['Where are you from?',
                                     'Where are you going?',
                                     'Who is with you?',
                                     'Wait a second'],
                         'correctIndex': 0,
                         'hint': "Think about asking about someone's place of origin.",
                         'correctFeedback': 'Correct. It means "Where are you from?"',
                         'wrongFeedback': 'Not quite. It means "Where are you from?"'}]}},
 'kadazan-dusun': {1: {'steps': [{'type': 'vocabulary',
                                  'title': 'First Meeting',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Kopivosian',
                                  'meaning': 'Greetings / hello',
                                  'note': 'A widely used Kadazan-Dusun greeting.'},
                                 {'type': 'vocabulary',
                                  'title': 'First Meeting',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Kotohuadan',
                                  'meaning': 'Thank you',
                                  'note': 'A common expression of thanks.'},
                                 {'type': 'vocabulary',
                                  'title': 'First Meeting',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Oho',
                                  'meaning': 'Yes',
                                  'note': 'A short affirmative response.'},
                                 {'type': 'vocabulary',
                                  'title': 'First Meeting',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Au',
                                  'meaning': 'No / not',
                                  'note': 'A short negative response.'},
                                 {'type': 'vocabulary',
                                  'title': 'First Meeting',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Isai ngaran nu?',
                                  'meaning': 'What is your name?',
                                  'note': 'Used when asking someone their name.'},
                                 {'type': 'vocabulary',
                                  'title': 'First Meeting',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Ngaran ku ...',
                                  'meaning': 'My name is ...',
                                  'note': 'Used to introduce yourself.'},
                                 {'type': 'quiz',
                                  'question': 'What does "Kopivosian" mean?',
                                  'instruction': 'Choose the correct meaning.',
                                  'options': ['Greetings / hello', 'Thank you', 'Yes', 'No / not'],
                                  'correctIndex': 0,
                                  'hint': 'Remember the expression "Kopivosian" from this level.',
                                  'correctFeedback': 'Correct. "Kopivosian" means "Greetings / '
                                                     'hello".',
                                  'wrongFeedback': 'Not quite. "Kopivosian" means "Greetings / '
                                                   'hello".'},
                                 {'type': 'quiz',
                                  'question': 'Which expression means "Thank you"?',
                                  'instruction': 'Choose the correct expression.',
                                  'options': ['Kopivosian', 'Oho', 'Kotohuadan', 'Au'],
                                  'correctIndex': 2,
                                  'hint': 'Think back to the expression paired with "Thank you".',
                                  'correctFeedback': 'Correct. "Kotohuadan" means "Thank you".',
                                  'wrongFeedback': 'Not quite. The correct answer is '
                                                   '"Kotohuadan".'},
                                 {'type': 'quiz',
                                  'question': 'What does "Oho" mean?',
                                  'instruction': 'Choose the correct meaning.',
                                  'options': ['Greetings / hello', 'Thank you', 'Yes', 'No / not'],
                                  'correctIndex': 2,
                                  'hint': 'Remember the expression "Oho" from this level.',
                                  'correctFeedback': 'Correct. "Oho" means "Yes".',
                                  'wrongFeedback': 'Not quite. "Oho" means "Yes".'},
                                 {'type': 'quiz',
                                  'question': 'Which expression means "No / not"?',
                                  'instruction': 'Choose the correct expression.',
                                  'options': ['Au', 'Kopivosian', 'Kotohuadan', 'Oho'],
                                  'correctIndex': 0,
                                  'hint': 'Think back to the expression paired with "No / not".',
                                  'correctFeedback': 'Correct. "Au" means "No / not".',
                                  'wrongFeedback': 'Not quite. The correct answer is "Au".'},
                                 {'type': 'quiz',
                                  'question': 'What does "Isai ngaran nu?" mean?',
                                  'instruction': 'Choose the correct meaning.',
                                  'options': ['What is your name?',
                                              'Greetings / hello',
                                              'Thank you',
                                              'Yes'],
                                  'correctIndex': 0,
                                  'hint': 'Remember the expression "Isai ngaran nu?" from this '
                                          'level.',
                                  'correctFeedback': 'Correct. "Isai ngaran nu?" means "What is '
                                                     'your name?".',
                                  'wrongFeedback': 'Not quite. "Isai ngaran nu?" means "What is '
                                                   'your name?".'},
                                 {'type': 'quiz',
                                  'question': 'Which expression means "My name is ..."?',
                                  'instruction': 'Choose the correct expression.',
                                  'options': ['Kopivosian', 'Kotohuadan', 'Ngaran ku ...', 'Oho'],
                                  'correctIndex': 2,
                                  'hint': 'Think back to the expression paired with "My name is '
                                          '...".',
                                  'correctFeedback': 'Correct. "Ngaran ku ..." means "My name is '
                                                     '...".',
                                  'wrongFeedback': 'Not quite. The correct answer is "Ngaran ku '
                                                   '...".'}]},
                   2: {'steps': [{'type': 'vocabulary',
                                  'title': 'People Around You',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'tama',
                                  'meaning': 'father',
                                  'note': 'A family word.'},
                                 {'type': 'vocabulary',
                                  'title': 'People Around You',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'tina',
                                  'meaning': 'mother',
                                  'note': 'A family word.'},
                                 {'type': 'vocabulary',
                                  'title': 'People Around You',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'tanak',
                                  'meaning': 'child',
                                  'note': 'A family word.'},
                                 {'type': 'vocabulary',
                                  'title': 'People Around You',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'tobpinai',
                                  'meaning': 'sibling / relative',
                                  'note': 'A relationship word.'},
                                 {'type': 'vocabulary',
                                  'title': 'People Around You',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'tulun',
                                  'meaning': 'person / people',
                                  'note': 'A useful people word.'},
                                 {'type': 'vocabulary',
                                  'title': 'People Around You',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'tasu',
                                  'meaning': 'dog',
                                  'note': 'A common everyday noun.'},
                                 {'type': 'quiz',
                                  'question': 'What does "tama" mean?',
                                  'instruction': 'Choose the correct meaning.',
                                  'options': ['father', 'mother', 'child', 'sibling / relative'],
                                  'correctIndex': 0,
                                  'hint': 'Remember the expression "tama" from this level.',
                                  'correctFeedback': 'Correct. "tama" means "father".',
                                  'wrongFeedback': 'Not quite. "tama" means "father".'},
                                 {'type': 'quiz',
                                  'question': 'Which expression means "mother"?',
                                  'instruction': 'Choose the correct expression.',
                                  'options': ['tama', 'tanak', 'tina', 'tobpinai'],
                                  'correctIndex': 2,
                                  'hint': 'Think back to the expression paired with "mother".',
                                  'correctFeedback': 'Correct. "tina" means "mother".',
                                  'wrongFeedback': 'Not quite. The correct answer is "tina".'},
                                 {'type': 'quiz',
                                  'question': 'What does "tanak" mean?',
                                  'instruction': 'Choose the correct meaning.',
                                  'options': ['father', 'mother', 'child', 'sibling / relative'],
                                  'correctIndex': 2,
                                  'hint': 'Remember the expression "tanak" from this level.',
                                  'correctFeedback': 'Correct. "tanak" means "child".',
                                  'wrongFeedback': 'Not quite. "tanak" means "child".'},
                                 {'type': 'quiz',
                                  'question': 'Which expression means "sibling / relative"?',
                                  'instruction': 'Choose the correct expression.',
                                  'options': ['tobpinai', 'tama', 'tina', 'tanak'],
                                  'correctIndex': 0,
                                  'hint': 'Think back to the expression paired with "sibling / '
                                          'relative".',
                                  'correctFeedback': 'Correct. "tobpinai" means "sibling / '
                                                     'relative".',
                                  'wrongFeedback': 'Not quite. The correct answer is "tobpinai".'},
                                 {'type': 'quiz',
                                  'question': 'What does "tulun" mean?',
                                  'instruction': 'Choose the correct meaning.',
                                  'options': ['person / people', 'father', 'mother', 'child'],
                                  'correctIndex': 0,
                                  'hint': 'Remember the expression "tulun" from this level.',
                                  'correctFeedback': 'Correct. "tulun" means "person / people".',
                                  'wrongFeedback': 'Not quite. "tulun" means "person / people".'},
                                 {'type': 'quiz',
                                  'question': 'Which expression means "dog"?',
                                  'instruction': 'Choose the correct expression.',
                                  'options': ['tama', 'tina', 'tasu', 'tanak'],
                                  'correctIndex': 2,
                                  'hint': 'Think back to the expression paired with "dog".',
                                  'correctFeedback': 'Correct. "tasu" means "dog".',
                                  'wrongFeedback': 'Not quite. The correct answer is "tasu".'}]},
                   3: {'steps': [{'type': 'vocabulary',
                                  'title': 'Everyday Encounters',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Nunu?',
                                  'meaning': 'What?',
                                  'note': 'A basic question word.'},
                                 {'type': 'vocabulary',
                                  'title': 'Everyday Encounters',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Isai?',
                                  'meaning': 'Who?',
                                  'note': 'Used when asking about a person.'},
                                 {'type': 'vocabulary',
                                  'title': 'Everyday Encounters',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Hinonggo?',
                                  'meaning': 'Where?',
                                  'note': 'Used when asking about a place.'},
                                 {'type': 'vocabulary',
                                  'title': 'Everyday Encounters',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Oho, kotohuadan.',
                                  'meaning': 'Yes, thank you.',
                                  'note': 'A short polite response.'},
                                 {'type': 'vocabulary',
                                  'title': 'Everyday Encounters',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Au, kotohuadan.',
                                  'meaning': 'No, thank you.',
                                  'note': 'A short polite response.'},
                                 {'type': 'vocabulary',
                                  'title': 'Everyday Encounters',
                                  'instruction': 'Study this expression and its meaning.',
                                  'word': 'Kopivosian.',
                                  'meaning': 'Greetings.',
                                  'note': 'A familiar greeting returning in context.'},
                                 {'type': 'quiz',
                                  'question': 'What does "Nunu?" mean?',
                                  'instruction': 'Choose the correct meaning.',
                                  'options': ['What?', 'Who?', 'Where?', 'Yes, thank you.'],
                                  'correctIndex': 0,
                                  'hint': 'Remember the expression "Nunu?" from this level.',
                                  'correctFeedback': 'Correct. "Nunu?" means "What?".',
                                  'wrongFeedback': 'Not quite. "Nunu?" means "What?".'},
                                 {'type': 'quiz',
                                  'question': 'Which expression means "Who?"?',
                                  'instruction': 'Choose the correct expression.',
                                  'options': ['Nunu?', 'Hinonggo?', 'Isai?', 'Oho, kotohuadan.'],
                                  'correctIndex': 2,
                                  'hint': 'Think back to the expression paired with "Who?".',
                                  'correctFeedback': 'Correct. "Isai?" means "Who?".',
                                  'wrongFeedback': 'Not quite. The correct answer is "Isai?".'},
                                 {'type': 'quiz',
                                  'question': 'What does "Hinonggo?" mean?',
                                  'instruction': 'Choose the correct meaning.',
                                  'options': ['What?', 'Who?', 'Where?', 'Yes, thank you.'],
                                  'correctIndex': 2,
                                  'hint': 'Remember the expression "Hinonggo?" from this level.',
                                  'correctFeedback': 'Correct. "Hinonggo?" means "Where?".',
                                  'wrongFeedback': 'Not quite. "Hinonggo?" means "Where?".'},
                                 {'type': 'quiz',
                                  'question': 'Which expression means "Yes, thank you."?',
                                  'instruction': 'Choose the correct expression.',
                                  'options': ['Oho, kotohuadan.', 'Nunu?', 'Isai?', 'Hinonggo?'],
                                  'correctIndex': 0,
                                  'hint': 'Think back to the expression paired with "Yes, thank '
                                          'you.".',
                                  'correctFeedback': 'Correct. "Oho, kotohuadan." means "Yes, '
                                                     'thank you.".',
                                  'wrongFeedback': 'Not quite. The correct answer is "Oho, '
                                                   'kotohuadan.".'},
                                 {'type': 'quiz',
                                  'question': 'What does "Au, kotohuadan." mean?',
                                  'instruction': 'Choose the correct meaning.',
                                  'options': ['No, thank you.', 'What?', 'Who?', 'Where?'],
                                  'correctIndex': 0,
                                  'hint': 'Remember the expression "Au, kotohuadan." from this '
                                          'level.',
                                  'correctFeedback': 'Correct. "Au, kotohuadan." means "No, thank '
                                                     'you.".',
                                  'wrongFeedback': 'Not quite. "Au, kotohuadan." means "No, thank '
                                                   'you.".'},
                                 {'type': 'quiz',
                                  'question': 'Which expression means "Greetings."?',
                                  'instruction': 'Choose the correct expression.',
                                  'options': ['Nunu?', 'Isai?', 'Kopivosian.', 'Hinonggo?'],
                                  'correctIndex': 2,
                                  'hint': 'Think back to the expression paired with "Greetings.".',
                                  'correctFeedback': 'Correct. "Kopivosian." means "Greetings.".',
                                  'wrongFeedback': 'Not quite. The correct answer is '
                                                   '"Kopivosian.".'}]}},
 'bidayuh': {1: {'steps': [{'type': 'vocabulary',
                            'title': 'First Meeting',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Siroi',
                            'meaning': 'Hello / greeting',
                            'note': 'An introductory recognition expression.'},
                           {'type': 'vocabulary',
                            'title': 'First Meeting',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Iyo',
                            'meaning': 'Yes',
                            'note': 'A short affirmative response.'},
                           {'type': 'vocabulary',
                            'title': 'First Meeting',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Indo',
                            'meaning': 'No',
                            'note': 'A short negative response.'},
                           {'type': 'vocabulary',
                            'title': 'First Meeting',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Terima kasih',
                            'meaning': 'Thank you',
                            'note': 'A polite expression common in multilingual settings.'},
                           {'type': 'vocabulary',
                            'title': 'First Meeting',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Sima ngaran mu?',
                            'meaning': 'What is your name?',
                            'note': 'An introductory question used in this course.'},
                           {'type': 'vocabulary',
                            'title': 'First Meeting',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Ngaran ku ...',
                            'meaning': 'My name is ...',
                            'note': 'An introductory response used in this course.'},
                           {'type': 'quiz',
                            'question': 'What does "Siroi" mean?',
                            'instruction': 'Choose the correct meaning.',
                            'options': ['Hello / greeting', 'Yes', 'No', 'Thank you'],
                            'correctIndex': 0,
                            'hint': 'Remember the expression "Siroi" from this level.',
                            'correctFeedback': 'Correct. "Siroi" means "Hello / greeting".',
                            'wrongFeedback': 'Not quite. "Siroi" means "Hello / greeting".'},
                           {'type': 'quiz',
                            'question': 'Which expression means "Yes"?',
                            'instruction': 'Choose the correct expression.',
                            'options': ['Siroi', 'Indo', 'Iyo', 'Terima kasih'],
                            'correctIndex': 2,
                            'hint': 'Think back to the expression paired with "Yes".',
                            'correctFeedback': 'Correct. "Iyo" means "Yes".',
                            'wrongFeedback': 'Not quite. The correct answer is "Iyo".'},
                           {'type': 'quiz',
                            'question': 'What does "Indo" mean?',
                            'instruction': 'Choose the correct meaning.',
                            'options': ['Hello / greeting', 'Yes', 'No', 'Thank you'],
                            'correctIndex': 2,
                            'hint': 'Remember the expression "Indo" from this level.',
                            'correctFeedback': 'Correct. "Indo" means "No".',
                            'wrongFeedback': 'Not quite. "Indo" means "No".'},
                           {'type': 'quiz',
                            'question': 'Which expression means "Thank you"?',
                            'instruction': 'Choose the correct expression.',
                            'options': ['Terima kasih', 'Siroi', 'Iyo', 'Indo'],
                            'correctIndex': 0,
                            'hint': 'Think back to the expression paired with "Thank you".',
                            'correctFeedback': 'Correct. "Terima kasih" means "Thank you".',
                            'wrongFeedback': 'Not quite. The correct answer is "Terima kasih".'},
                           {'type': 'quiz',
                            'question': 'What does "Sima ngaran mu?" mean?',
                            'instruction': 'Choose the correct meaning.',
                            'options': ['What is your name?', 'Hello / greeting', 'Yes', 'No'],
                            'correctIndex': 0,
                            'hint': 'Remember the expression "Sima ngaran mu?" from this level.',
                            'correctFeedback': 'Correct. "Sima ngaran mu?" means "What is your '
                                               'name?".',
                            'wrongFeedback': 'Not quite. "Sima ngaran mu?" means "What is your '
                                             'name?".'},
                           {'type': 'quiz',
                            'question': 'Which expression means "My name is ..."?',
                            'instruction': 'Choose the correct expression.',
                            'options': ['Siroi', 'Iyo', 'Ngaran ku ...', 'Indo'],
                            'correctIndex': 2,
                            'hint': 'Think back to the expression paired with "My name is ...".',
                            'correctFeedback': 'Correct. "Ngaran ku ..." means "My name is ...".',
                            'wrongFeedback': 'Not quite. The correct answer is "Ngaran ku ...".'}]},
             2: {'steps': [{'type': 'vocabulary',
                            'title': 'People Around You',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'sama',
                            'meaning': 'father',
                            'note': 'A family relationship word.'},
                           {'type': 'vocabulary',
                            'title': 'People Around You',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'sino',
                            'meaning': 'mother',
                            'note': 'A family relationship word.'},
                           {'type': 'vocabulary',
                            'title': 'People Around You',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'anak',
                            'meaning': 'child',
                            'note': 'A family word.'},
                           {'type': 'vocabulary',
                            'title': 'People Around You',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'sodara',
                            'meaning': 'relative / sibling',
                            'note': 'A relationship word.'},
                           {'type': 'vocabulary',
                            'title': 'People Around You',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'dayung',
                            'meaning': 'woman / female',
                            'note': 'A people word used in Bidayuh contexts.'},
                           {'type': 'vocabulary',
                            'title': 'People Around You',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'darud',
                            'meaning': 'friend',
                            'note': 'A relationship word used in this course.'},
                           {'type': 'quiz',
                            'question': 'What does "sama" mean?',
                            'instruction': 'Choose the correct meaning.',
                            'options': ['father', 'mother', 'child', 'relative / sibling'],
                            'correctIndex': 0,
                            'hint': 'Remember the expression "sama" from this level.',
                            'correctFeedback': 'Correct. "sama" means "father".',
                            'wrongFeedback': 'Not quite. "sama" means "father".'},
                           {'type': 'quiz',
                            'question': 'Which expression means "mother"?',
                            'instruction': 'Choose the correct expression.',
                            'options': ['sama', 'anak', 'sino', 'sodara'],
                            'correctIndex': 2,
                            'hint': 'Think back to the expression paired with "mother".',
                            'correctFeedback': 'Correct. "sino" means "mother".',
                            'wrongFeedback': 'Not quite. The correct answer is "sino".'},
                           {'type': 'quiz',
                            'question': 'What does "anak" mean?',
                            'instruction': 'Choose the correct meaning.',
                            'options': ['father', 'mother', 'child', 'relative / sibling'],
                            'correctIndex': 2,
                            'hint': 'Remember the expression "anak" from this level.',
                            'correctFeedback': 'Correct. "anak" means "child".',
                            'wrongFeedback': 'Not quite. "anak" means "child".'},
                           {'type': 'quiz',
                            'question': 'Which expression means "relative / sibling"?',
                            'instruction': 'Choose the correct expression.',
                            'options': ['sodara', 'sama', 'sino', 'anak'],
                            'correctIndex': 0,
                            'hint': 'Think back to the expression paired with "relative / '
                                    'sibling".',
                            'correctFeedback': 'Correct. "sodara" means "relative / sibling".',
                            'wrongFeedback': 'Not quite. The correct answer is "sodara".'},
                           {'type': 'quiz',
                            'question': 'What does "dayung" mean?',
                            'instruction': 'Choose the correct meaning.',
                            'options': ['woman / female', 'father', 'mother', 'child'],
                            'correctIndex': 0,
                            'hint': 'Remember the expression "dayung" from this level.',
                            'correctFeedback': 'Correct. "dayung" means "woman / female".',
                            'wrongFeedback': 'Not quite. "dayung" means "woman / female".'},
                           {'type': 'quiz',
                            'question': 'Which expression means "friend"?',
                            'instruction': 'Choose the correct expression.',
                            'options': ['sama', 'sino', 'darud', 'anak'],
                            'correctIndex': 2,
                            'hint': 'Think back to the expression paired with "friend".',
                            'correctFeedback': 'Correct. "darud" means "friend".',
                            'wrongFeedback': 'Not quite. The correct answer is "darud".'}]},
             3: {'steps': [{'type': 'vocabulary',
                            'title': 'Everyday Encounters',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Onu?',
                            'meaning': 'What?',
                            'note': 'A basic question word.'},
                           {'type': 'vocabulary',
                            'title': 'Everyday Encounters',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Sima?',
                            'meaning': 'Who?',
                            'note': 'Used when asking about a person.'},
                           {'type': 'vocabulary',
                            'title': 'Everyday Encounters',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Dinu?',
                            'meaning': 'Where?',
                            'note': 'Used when asking about a place.'},
                           {'type': 'vocabulary',
                            'title': 'Everyday Encounters',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Iyo.',
                            'meaning': 'Yes.',
                            'note': 'A short affirmative answer.'},
                           {'type': 'vocabulary',
                            'title': 'Everyday Encounters',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Indo.',
                            'meaning': 'No.',
                            'note': 'A short negative answer.'},
                           {'type': 'vocabulary',
                            'title': 'Everyday Encounters',
                            'instruction': 'Study this expression and its meaning.',
                            'word': 'Terima kasih.',
                            'meaning': 'Thank you.',
                            'note': 'A polite response.'},
                           {'type': 'quiz',
                            'question': 'What does "Onu?" mean?',
                            'instruction': 'Choose the correct meaning.',
                            'options': ['What?', 'Who?', 'Where?', 'Yes.'],
                            'correctIndex': 0,
                            'hint': 'Remember the expression "Onu?" from this level.',
                            'correctFeedback': 'Correct. "Onu?" means "What?".',
                            'wrongFeedback': 'Not quite. "Onu?" means "What?".'},
                           {'type': 'quiz',
                            'question': 'Which expression means "Who?"?',
                            'instruction': 'Choose the correct expression.',
                            'options': ['Onu?', 'Dinu?', 'Sima?', 'Iyo.'],
                            'correctIndex': 2,
                            'hint': 'Think back to the expression paired with "Who?".',
                            'correctFeedback': 'Correct. "Sima?" means "Who?".',
                            'wrongFeedback': 'Not quite. The correct answer is "Sima?".'},
                           {'type': 'quiz',
                            'question': 'What does "Dinu?" mean?',
                            'instruction': 'Choose the correct meaning.',
                            'options': ['What?', 'Who?', 'Where?', 'Yes.'],
                            'correctIndex': 2,
                            'hint': 'Remember the expression "Dinu?" from this level.',
                            'correctFeedback': 'Correct. "Dinu?" means "Where?".',
                            'wrongFeedback': 'Not quite. "Dinu?" means "Where?".'},
                           {'type': 'quiz',
                            'question': 'Which expression means "Yes."?',
                            'instruction': 'Choose the correct expression.',
                            'options': ['Iyo.', 'Onu?', 'Sima?', 'Dinu?'],
                            'correctIndex': 0,
                            'hint': 'Think back to the expression paired with "Yes.".',
                            'correctFeedback': 'Correct. "Iyo." means "Yes.".',
                            'wrongFeedback': 'Not quite. The correct answer is "Iyo.".'},
                           {'type': 'quiz',
                            'question': 'What does "Indo." mean?',
                            'instruction': 'Choose the correct meaning.',
                            'options': ['No.', 'What?', 'Who?', 'Where?'],
                            'correctIndex': 0,
                            'hint': 'Remember the expression "Indo." from this level.',
                            'correctFeedback': 'Correct. "Indo." means "No.".',
                            'wrongFeedback': 'Not quite. "Indo." means "No.".'},
                           {'type': 'quiz',
                            'question': 'Which expression means "Thank you."?',
                            'instruction': 'Choose the correct expression.',
                            'options': ['Onu?', 'Sima?', 'Terima kasih.', 'Dinu?'],
                            'correctIndex': 2,
                            'hint': 'Think back to the expression paired with "Thank you.".',
                            'correctFeedback': 'Correct. "Terima kasih." means "Thank you.".',
                            'wrongFeedback': 'Not quite. The correct answer is "Terima '
                                             'kasih.".'}]}},
 'mah-meri': {1: {'steps': [{'type': 'vocabulary',
                             'title': 'First Meeting',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Selamat',
                             'meaning': 'Greeting / well-being',
                             'note': 'A recognition-focused bridge greeting.'},
                            {'type': 'vocabulary',
                             'title': 'First Meeting',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Terima kasih',
                             'meaning': 'Thank you',
                             'note': 'A polite bridge expression used in multilingual settings.'},
                            {'type': 'vocabulary',
                             'title': 'First Meeting',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Ya',
                             'meaning': 'Yes',
                             'note': 'A short affirmative response.'},
                            {'type': 'vocabulary',
                             'title': 'First Meeting',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Tak',
                             'meaning': 'No / not',
                             'note': 'A short negative response.'},
                            {'type': 'vocabulary',
                             'title': 'First Meeting',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Nama?',
                             'meaning': 'Name?',
                             'note': 'A recognition prompt connected with introductions.'},
                            {'type': 'vocabulary',
                             'title': 'First Meeting',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Nama saya ...',
                             'meaning': 'My name is ...',
                             'note': 'A bridge expression for beginning an introduction.'},
                            {'type': 'quiz',
                             'question': 'What does "Selamat" mean?',
                             'instruction': 'Choose the correct meaning.',
                             'options': ['Greeting / well-being', 'Thank you', 'Yes', 'No / not'],
                             'correctIndex': 0,
                             'hint': 'Remember the expression "Selamat" from this level.',
                             'correctFeedback': 'Correct. "Selamat" means "Greeting / well-being".',
                             'wrongFeedback': 'Not quite. "Selamat" means "Greeting / '
                                              'well-being".'},
                            {'type': 'quiz',
                             'question': 'Which expression means "Thank you"?',
                             'instruction': 'Choose the correct expression.',
                             'options': ['Selamat', 'Ya', 'Terima kasih', 'Tak'],
                             'correctIndex': 2,
                             'hint': 'Think back to the expression paired with "Thank you".',
                             'correctFeedback': 'Correct. "Terima kasih" means "Thank you".',
                             'wrongFeedback': 'Not quite. The correct answer is "Terima kasih".'},
                            {'type': 'quiz',
                             'question': 'What does "Ya" mean?',
                             'instruction': 'Choose the correct meaning.',
                             'options': ['Greeting / well-being', 'Thank you', 'Yes', 'No / not'],
                             'correctIndex': 2,
                             'hint': 'Remember the expression "Ya" from this level.',
                             'correctFeedback': 'Correct. "Ya" means "Yes".',
                             'wrongFeedback': 'Not quite. "Ya" means "Yes".'},
                            {'type': 'quiz',
                             'question': 'Which expression means "No / not"?',
                             'instruction': 'Choose the correct expression.',
                             'options': ['Tak', 'Selamat', 'Terima kasih', 'Ya'],
                             'correctIndex': 0,
                             'hint': 'Think back to the expression paired with "No / not".',
                             'correctFeedback': 'Correct. "Tak" means "No / not".',
                             'wrongFeedback': 'Not quite. The correct answer is "Tak".'},
                            {'type': 'quiz',
                             'question': 'What does "Nama?" mean?',
                             'instruction': 'Choose the correct meaning.',
                             'options': ['Name?', 'Greeting / well-being', 'Thank you', 'Yes'],
                             'correctIndex': 0,
                             'hint': 'Remember the expression "Nama?" from this level.',
                             'correctFeedback': 'Correct. "Nama?" means "Name?".',
                             'wrongFeedback': 'Not quite. "Nama?" means "Name?".'},
                            {'type': 'quiz',
                             'question': 'Which expression means "My name is ..."?',
                             'instruction': 'Choose the correct expression.',
                             'options': ['Selamat', 'Terima kasih', 'Nama saya ...', 'Ya'],
                             'correctIndex': 2,
                             'hint': 'Think back to the expression paired with "My name is ...".',
                             'correctFeedback': 'Correct. "Nama saya ..." means "My name is ...".',
                             'wrongFeedback': 'Not quite. The correct answer is "Nama saya '
                                              '...".'}]},
              2: {'steps': [{'type': 'vocabulary',
                             'title': 'People Around You',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'orang',
                             'meaning': 'person / people',
                             'note': 'A useful community bridge word.'},
                            {'type': 'vocabulary',
                             'title': 'People Around You',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'anak',
                             'meaning': 'child',
                             'note': 'A family and community bridge word.'},
                            {'type': 'vocabulary',
                             'title': 'People Around You',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'ibu',
                             'meaning': 'mother',
                             'note': 'A family relationship bridge word.'},
                            {'type': 'vocabulary',
                             'title': 'People Around You',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'bapa',
                             'meaning': 'father',
                             'note': 'A family relationship bridge word.'},
                            {'type': 'vocabulary',
                             'title': 'People Around You',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'kawan',
                             'meaning': 'friend',
                             'note': 'A relationship bridge word.'},
                            {'type': 'vocabulary',
                             'title': 'People Around You',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'keluarga',
                             'meaning': 'family',
                             'note': 'A bridge word for family and relationships.'},
                            {'type': 'quiz',
                             'question': 'What does "orang" mean?',
                             'instruction': 'Choose the correct meaning.',
                             'options': ['person / people', 'child', 'mother', 'father'],
                             'correctIndex': 0,
                             'hint': 'Remember the expression "orang" from this level.',
                             'correctFeedback': 'Correct. "orang" means "person / people".',
                             'wrongFeedback': 'Not quite. "orang" means "person / people".'},
                            {'type': 'quiz',
                             'question': 'Which expression means "child"?',
                             'instruction': 'Choose the correct expression.',
                             'options': ['orang', 'ibu', 'anak', 'bapa'],
                             'correctIndex': 2,
                             'hint': 'Think back to the expression paired with "child".',
                             'correctFeedback': 'Correct. "anak" means "child".',
                             'wrongFeedback': 'Not quite. The correct answer is "anak".'},
                            {'type': 'quiz',
                             'question': 'What does "ibu" mean?',
                             'instruction': 'Choose the correct meaning.',
                             'options': ['person / people', 'child', 'mother', 'father'],
                             'correctIndex': 2,
                             'hint': 'Remember the expression "ibu" from this level.',
                             'correctFeedback': 'Correct. "ibu" means "mother".',
                             'wrongFeedback': 'Not quite. "ibu" means "mother".'},
                            {'type': 'quiz',
                             'question': 'Which expression means "father"?',
                             'instruction': 'Choose the correct expression.',
                             'options': ['bapa', 'orang', 'anak', 'ibu'],
                             'correctIndex': 0,
                             'hint': 'Think back to the expression paired with "father".',
                             'correctFeedback': 'Correct. "bapa" means "father".',
                             'wrongFeedback': 'Not quite. The correct answer is "bapa".'},
                            {'type': 'quiz',
                             'question': 'What does "kawan" mean?',
                             'instruction': 'Choose the correct meaning.',
                             'options': ['friend', 'person / people', 'child', 'mother'],
                             'correctIndex': 0,
                             'hint': 'Remember the expression "kawan" from this level.',
                             'correctFeedback': 'Correct. "kawan" means "friend".',
                             'wrongFeedback': 'Not quite. "kawan" means "friend".'},
                            {'type': 'quiz',
                             'question': 'Which expression means "family"?',
                             'instruction': 'Choose the correct expression.',
                             'options': ['orang', 'anak', 'keluarga', 'ibu'],
                             'correctIndex': 2,
                             'hint': 'Think back to the expression paired with "family".',
                             'correctFeedback': 'Correct. "keluarga" means "family".',
                             'wrongFeedback': 'Not quite. The correct answer is "keluarga".'}]},
              3: {'steps': [{'type': 'vocabulary',
                             'title': 'Everyday Encounters',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Apa?',
                             'meaning': 'What?',
                             'note': 'A basic bridge question.'},
                            {'type': 'vocabulary',
                             'title': 'Everyday Encounters',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Siapa?',
                             'meaning': 'Who?',
                             'note': 'A basic bridge question about a person.'},
                            {'type': 'vocabulary',
                             'title': 'Everyday Encounters',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Di mana?',
                             'meaning': 'Where?',
                             'note': 'A basic bridge question about a place.'},
                            {'type': 'vocabulary',
                             'title': 'Everyday Encounters',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Ya, terima kasih.',
                             'meaning': 'Yes, thank you.',
                             'note': 'A short polite response.'},
                            {'type': 'vocabulary',
                             'title': 'Everyday Encounters',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Tak, terima kasih.',
                             'meaning': 'No, thank you.',
                             'note': 'A short polite response.'},
                            {'type': 'vocabulary',
                             'title': 'Everyday Encounters',
                             'instruction': 'Study this expression and its meaning.',
                             'word': 'Selamat datang.',
                             'meaning': 'Welcome.',
                             'note': 'A welcoming bridge expression.'},
                            {'type': 'quiz',
                             'question': 'What does "Apa?" mean?',
                             'instruction': 'Choose the correct meaning.',
                             'options': ['What?', 'Who?', 'Where?', 'Yes, thank you.'],
                             'correctIndex': 0,
                             'hint': 'Remember the expression "Apa?" from this level.',
                             'correctFeedback': 'Correct. "Apa?" means "What?".',
                             'wrongFeedback': 'Not quite. "Apa?" means "What?".'},
                            {'type': 'quiz',
                             'question': 'Which expression means "Who?"?',
                             'instruction': 'Choose the correct expression.',
                             'options': ['Apa?', 'Di mana?', 'Siapa?', 'Ya, terima kasih.'],
                             'correctIndex': 2,
                             'hint': 'Think back to the expression paired with "Who?".',
                             'correctFeedback': 'Correct. "Siapa?" means "Who?".',
                             'wrongFeedback': 'Not quite. The correct answer is "Siapa?".'},
                            {'type': 'quiz',
                             'question': 'What does "Di mana?" mean?',
                             'instruction': 'Choose the correct meaning.',
                             'options': ['What?', 'Who?', 'Where?', 'Yes, thank you.'],
                             'correctIndex': 2,
                             'hint': 'Remember the expression "Di mana?" from this level.',
                             'correctFeedback': 'Correct. "Di mana?" means "Where?".',
                             'wrongFeedback': 'Not quite. "Di mana?" means "Where?".'},
                            {'type': 'quiz',
                             'question': 'Which expression means "Yes, thank you."?',
                             'instruction': 'Choose the correct expression.',
                             'options': ['Ya, terima kasih.', 'Apa?', 'Siapa?', 'Di mana?'],
                             'correctIndex': 0,
                             'hint': 'Think back to the expression paired with "Yes, thank you.".',
                             'correctFeedback': 'Correct. "Ya, terima kasih." means "Yes, thank '
                                                'you.".',
                             'wrongFeedback': 'Not quite. The correct answer is "Ya, terima '
                                              'kasih.".'},
                            {'type': 'quiz',
                             'question': 'What does "Tak, terima kasih." mean?',
                             'instruction': 'Choose the correct meaning.',
                             'options': ['No, thank you.', 'What?', 'Who?', 'Where?'],
                             'correctIndex': 0,
                             'hint': 'Remember the expression "Tak, terima kasih." from this '
                                     'level.',
                             'correctFeedback': 'Correct. "Tak, terima kasih." means "No, thank '
                                                'you.".',
                             'wrongFeedback': 'Not quite. "Tak, terima kasih." means "No, thank '
                                              'you.".'},
                            {'type': 'quiz',
                             'question': 'Which expression means "Welcome."?',
                             'instruction': 'Choose the correct expression.',
                             'options': ['Apa?', 'Siapa?', 'Selamat datang.', 'Di mana?'],
                             'correctIndex': 2,
                             'hint': 'Think back to the expression paired with "Welcome.".',
                             'correctFeedback': 'Correct. "Selamat datang." means "Welcome.".',
                             'wrongFeedback': 'Not quite. The correct answer is "Selamat '
                                              'datang.".'}]}}}


# ================= PROGRESS HELPERS =================

def get_completed_levels(user_id, lang_key):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT level_num
        FROM progress
        WHERE user_id = ?
          AND lang_key = ?
          AND completed = 1
        """,
        (user_id, lang_key)
    ).fetchall()

    conn.close()

    return {
        row["level_num"]
        for row in rows
    }


def get_saved_step(user_id, lang_key, level_num):
    conn = get_db()

    row = conn.execute(
        """
        SELECT current_step
        FROM lesson_progress
        WHERE user_id = ?
          AND lang_key = ?
          AND level_num = ?
        """,
        (
            user_id,
            lang_key,
            level_num
        )
    ).fetchone()

    conn.close()

    if not row:
        return 0

    return row["current_step"]


def get_levels(user_id, lang_key):
    completed_levels = get_completed_levels(
        user_id,
        lang_key
    )

    levels = []

    for level_num, title in LEVEL_TITLES.items():

        completed = (
            level_num in completed_levels
        )

        if level_num == 1:
            unlocked = True
        else:
            unlocked = (
                level_num - 1
                in completed_levels
            )

        course = COURSE_DATA.get(
            lang_key,
            {}
        ).get(
            level_num,
            {}
        )

        total_steps = len(
            course.get("steps", [])
        )

        saved_step = get_saved_step(
            user_id,
            lang_key,
            level_num
        )

        if total_steps > 0:

            saved_step = min(
                saved_step,
                total_steps
            )

            percentage = round(
                (
                    saved_step /
                    total_steps
                ) * 100
            )

        else:
            saved_step = 0
            percentage = 0

        if completed:
            saved_step = total_steps
            percentage = 100

        levels.append({
            "number": level_num,
            "title": title,
            "unlocked": unlocked,
            "completed": completed,
            "current_step": saved_step,
            "total_steps": total_steps,
            "percentage": percentage
        })

    return levels


def get_language_learning_summary(user_id, lang_key):
    levels = get_levels(
        user_id,
        lang_key
    )

    completed_count = sum(
        1
        for level in levels
        if level["completed"]
    )

    total_levels = len(levels)

    active_level = None

    for level in levels:

        if (
            level["unlocked"]
            and not level["completed"]
        ):
            active_level = level
            break

    if active_level is None and levels:
        active_level = levels[-1]

    return {
        "levels": levels,
        "completed_count": completed_count,
        "total_levels": total_levels,
        "active_level": active_level
    }


# ================= LANGUAGE COMPARISON HELPERS =================

def get_language_greeting(lang_key):
    steps = (
        COURSE_DATA.get(lang_key, {})
        .get(1, {})
        .get("steps", [])
    )

    for step in steps:
        meaning = step.get("meaning", "")

        if not meaning:
            continue

        lowered = meaning.lower()

        if (
            "greet" in lowered or
            "welcome" in lowered or
            "hello" in lowered
        ):
            word = (
                step.get("word") or
                step.get("expression")
            )

            if word:
                return {
                    "word": word,
                    "meaning": meaning
                }

    return None


def get_language_number_system(lang_key):
    steps = (
        COURSE_DATA.get(lang_key, {})
        .get(1, {})
        .get("steps", [])
    )

    number_keywords = (
        "one", "two", "three", "four", "five",
        "number", "numbers", "count"
    )

    for step in steps:
        meaning = step.get(
            "meaning",
            ""
        ).lower()

        if any(
            keyword in meaning
            for keyword in number_keywords
        ):
            return {
                "word": (
                    step.get("word") or
                    step.get("expression")
                ),
                "meaning": step.get("meaning")
            }

    return None


def get_language_comparison_data(lang_key):
    language = LANGUAGES.get(lang_key)

    if not language:
        return None

    greeting = get_language_greeting(lang_key)
    number_system = get_language_number_system(lang_key)

    speakers_text = language.get("speakers", "")
    speakers_summary = speakers_text.split(".")[0].strip()

    if speakers_summary:
        speakers_summary += "."

    vitality_status = language.get(
        "verification_status",
        "Under Review"
    )

    return {
        "lang_key": lang_key,
        "display_name": language.get(
            "display_name",
            lang_key
        ),
        "region": language.get(
            "region",
            "Not specified"
        ),
        "family": LANGUAGE_FAMILY.get(
            lang_key,
            "Documentation pending"
        ),
        "speakers_estimate": (
            speakers_summary or
            "Documentation pending"
        ),
        "vitality_status": vitality_status,
        "vitality_note": language.get(
            "verification_note",
            ""
        ),
        "vitality_meter": get_vitality_meter(
            vitality_status
        ),
        "writing_system": LANGUAGE_WRITING_SYSTEM,
        "greeting": greeting,
        "number_system": number_system,
        "levels": list(LEVEL_TITLES.values())
    }


def compute_language_comparison_summary(comparison_a, comparison_b):
    if not comparison_a or not comparison_b:
        return None

    attributes = [
        {
            "key": "family",
            "label": "Language Family",
            "same": (
                comparison_a["family"] ==
                comparison_b["family"]
            )
        },
        {
            "key": "region",
            "label": "Region",
            "same": (
                comparison_a["region"] ==
                comparison_b["region"]
            )
        },
        {
            "key": "writing_system",
            "label": "Writing System",
            "same": (
                comparison_a["writing_system"] ==
                comparison_b["writing_system"]
            )
        },
        {
            "key": "vitality_status",
            "label": "UNESCO Status",
            "same": (
                comparison_a["vitality_status"] ==
                comparison_b["vitality_status"]
            )
        },
        {
            "key": "levels",
            "label": "Learning Levels",
            "same": (
                comparison_a["levels"] ==
                comparison_b["levels"]
            )
        }
    ]

    total = len(attributes)

    matches = sum(
        1
        for attribute in attributes
        if attribute["same"]
    )

    percentage = (
        round((matches / total) * 100)
        if total
        else 0
    )

    return {
        "percentage": percentage,
        "matches": matches,
        "total": total,
        "attributes": attributes,
        "by_key": {
            attribute["key"]: attribute["same"]
            for attribute in attributes
        }
    }


# ================= AI TUTOR PROMPT BUILDER =================
#
# These helpers never call an AI API and never generate a reply.
# They only read LANGUAGES / COURSE_DATA (already defined above) and
# shape that data into a grounded context and a system prompt string.
# This keeps the AI Tutor scoped to the four supported languages and
# reduces hallucination by only ever offering the AI real course data.

TUTOR_MAX_VOCABULARY_ITEMS = 8

TUTOR_MAX_MISTAKE_ITEMS = 5

TUTOR_MAX_HISTORY_TURNS = 12

TUTOR_MAX_HISTORY_CHARS = 2000


# ================= AI TUTOR DOMAIN RESTRICTION =================
#
# The tutor is a LANGUAGE & LINGUISTICS tutor. It is not limited to the
# four supported course languages - it may discuss any language, and
# any linguistics topic (phonetics, grammar, writing systems, language
# families, etymology, etc). It must still refuse anything that is not
# language-related at all (math, politics, coding, medicine, sports,
# celebrities, ...). That refusal must happen WITHOUT calling the AI
# provider, so this check runs purely on the server using plain
# keyword/pattern matching - no external calls, no ambiguity. The
# default (when a message matches neither list) is to ALLOW the
# message through, since Priority 2 deliberately opens the door to any
# language/linguistics question the keyword lists don't happen to
# anticipate.

TUTOR_OFFTOPIC_REFUSAL = (
    "I'm your Language AI Tutor.\n\n"
    "I can help with languages, linguistics, pronunciation, grammar, "
    "vocabulary, writing systems, translation, language learning and "
    "the lessons inside this website.\n\n"
    "Please ask me anything language-related."
)

TUTOR_DOMAIN_KEYWORD_PATTERN = re.compile(
    r"\b("
    # ---------- this website's four languages & their context ----------
    r"iban|kadazan|dusun|kadazandusun|bidayuh|mah\s*meri|"
    r"malaysia\w*|sarawak|sabah|borneo|longhouse|indigenous|orang\s*asli|"
    r"heritage|folklore|festival|ritual|custom\w*|tradition\w*|"
    r"cultur\w*|community|preserv\w*|endanger\w*|"
    # ---------- language / linguistics (any language, not just ours) ----------
    r"pronoun[ce]e?|pronunciation|pronounced|vocabular\w*|\bvocab\b|"
    r"grammar|translat\w*|meaning|greet\w*|\bphrase\b|dialect\w*|"
    r"\blesson\w*|\bcourse\w*|\bquiz\w*|\blevel\b|\bword\w*|\bsentence\w*|"
    r"\bspeak\w*|\bsay\b|\blanguage\w*|\btutor\b|\bexplain\b|\bexample\w*|"
    r"\bcompar\w*|native\s*speaker|dialogue|conversation|"
    r"linguist\w*|phonet\w*|phonolog\w*|morpholog\w*|\bsyntax\w*|semantic\w*|"
    r"etymolog\w*|orthograph\w*|\bscript\b|alphabet\w*|writing\s*system\w*|"
    r"\bipa\b|agglutinat\w*|\bvowel\w*|\bconsonant\w*|\bsyllable\w*|"
    r"\bphoneme\w*|\bmorpheme\w*|\btonal\b|\btone\b|conjugat\w*|declens\w*|"
    r"loanword\w*|\bcognate\w*|\bcreole\w*|\bpidgin\b|biling\w*|multiling\w*|"
    r"sign\s*language|language\s*famil\w*|austronesian|malayo-polynesian|"
    r"mother\s*tongue|second\s*language|"
    # ---------- common world language names (not exhaustive by design) ----------
    r"\benglish\b|\bmalay\b|bahasa|mandarin|cantonese|\bchinese\b|japanese|"
    r"korean|\btamil\b|\bhindi\b|\barabic\b|\bspanish\b|\bfrench\b|german|"
    r"tagalog|filipino|\bthai\b|vietnamese|indonesian|javanese|sundanese|"
    r"punjabi|bengali|portuguese|italian|russian|\burdu\b|burmese|khmer|"
    r"\blao\b|mongolian|turkish|persian|\bfarsi\b|swahili|hawaiian|maori|"
    r"\blatin\b"
    r")\b",
    re.IGNORECASE
)

TUTOR_OFFTOPIC_KEYWORD_PATTERN = re.compile(
    r"\b("
    r"solve|equation|integral|derivative|algebra|geometry|trigonometry|"
    r"calculate|calculus|\bmath\w*|"
    r"python|javascript|typescript|\bjava\b|c\+\+|\bhtml\b|\bcss\b|\bsql\b|"
    r"programming|source\s*code|algorithm|\bdebug\w*|compile|"
    r"president|prime\s*minister|election\w*|government|politic\w*|"
    r"senator|parliament|\bminister\b|congress|"
    r"symptom\w*|diagnos\w*|treatment|medication|prescri\w*|surgery|"
    r"\bmedicine\b|\bdisease\w*|\bcancer\b|\bvirus\b|\bcovid\b|\bdoctor\b|"
    r"celebrit\w*|\bactor\b|\bactress\b|\bsinger\b|footballer|kpop|"
    r"movie\s*star|stock\s*market|bitcoin|cryptocurrency|share\s*price|"
    r"\bweather\b|"
    r"write\s*(a|me)?\s*(poem|essay|story|code|program)|"
    r"\bfootball\b|\bsoccer\b|basketball|\bcricket\b|\bnba\b|\bfifa\b|"
    r"olympics|\bcars?\b|vehicle\w*|automobile\w*|"
    r"\bwho\s+is\b|\bwho\s+was\b|\bnet\s*worth\b"
    r")\b",
    re.IGNORECASE
)

TUTOR_MATH_EXPRESSION_PATTERN = re.compile(
    r"\d+\s*[\+\-\*/^]\s*\d+"
)


def is_tutor_message_in_domain(message):
    """
    Returns True when a free-form message is allowed to reach the AI
    provider. Empty messages (used by quick actions) are always in
    domain. Any message containing a language/linguistics keyword is
    always in domain, even if it also mentions an off-topic word.
    Otherwise, a message that matches an obvious off-topic pattern
    (maths, politics, programming, medicine, sports, celebrities, ...)
    is rejected before any API call is made. Anything that matches
    NEITHER list defaults to allowed - this is intentional, since the
    tutor is now allowed to discuss any language/linguistics topic,
    which is impossible to enumerate exhaustively as a keyword list.
    """

    text = (message or "").strip()

    if not text:
        return True

    if TUTOR_DOMAIN_KEYWORD_PATTERN.search(text):
        return True

    if (
        TUTOR_OFFTOPIC_KEYWORD_PATTERN.search(text)
        or TUTOR_MATH_EXPRESSION_PATTERN.search(text)
    ):
        return False

    return True


def get_tutor_language_facts(lang_key):
    """
    Returns the subset of LANGUAGES[lang_key] relevant for tutoring
    (cultural context), or None if lang_key is not one of the four
    supported languages.
    """

    language = LANGUAGES.get(lang_key)

    if not language:
        return None

    return {
        "display_name": language.get("display_name", lang_key),
        "about": language.get("about", ""),
        "speakers": language.get("speakers", ""),
        "location": language.get("location", ""),
        "preservation": language.get("preservation", ""),
        "verification_status": language.get(
            "verification_status",
            "Under Review"
        )
    }


def build_general_tutor_context():
    """
    Builds a grounded context covering ALL four supported languages at
    once, sourced only from LANGUAGES / COURSE_DATA. Used for Free Chat
    when no specific course/lesson is open, so general questions and
    comparisons between the supported languages can still be answered
    without ever inventing facts.
    """

    all_language_facts = []
    sample_vocabulary = []

    for known_lang_key in LANGUAGES.keys():

        facts = get_tutor_language_facts(known_lang_key)

        if facts:
            facts = dict(facts)
            facts["lang_key"] = known_lang_key
            all_language_facts.append(facts)

        for level_data in COURSE_DATA.get(known_lang_key, {}).values():

            for step in level_data.get("steps", []):

                term = step.get("word") or step.get("expression")
                meaning = step.get("meaning")

                if term and meaning:
                    sample_vocabulary.append({
                        "lang_key": known_lang_key,
                        "term": term,
                        "meaning": meaning,
                        "note": step.get("note") or step.get("context") or ""
                    })
                    break

    return {
        "lang_key": None,
        "level_num": None,
        "general_mode": True,
        "all_language_facts": all_language_facts,
        "vocabulary": sample_vocabulary[:TUTOR_MAX_VOCABULARY_ITEMS],
        "common_mistakes": []
    }


def extract_lesson_vocabulary(lang_key, level_num):
    """
    Shared vocabulary extraction used by both the grounded prompt
    builder and the quiz generator, so both always see the exact same
    real course data. Returns a flat list of {term, meaning, note}.
    """

    if level_num is not None:
        levels_to_scan = [level_num]
    else:
        levels_to_scan = list(
            COURSE_DATA.get(lang_key, {}).keys()
        )

    vocabulary = []

    for scanned_level in levels_to_scan:

        steps = (
            COURSE_DATA.get(lang_key, {})
            .get(scanned_level, {})
            .get("steps", [])
        )

        for step in steps:

            term = step.get("word") or step.get("expression")
            meaning = step.get("meaning")

            if term and meaning:
                vocabulary.append({
                    "term": term,
                    "meaning": meaning,
                    "note": step.get("note") or step.get("context") or ""
                })

    return vocabulary


def build_tutor_grounded_context(lang_key, level_num, user_message, mode=None):
    """
    Builds the "ground truth" material the AI Tutor is allowed to use:
    language facts, relevant vocabulary, and common learner mistakes -
    all sourced directly from LANGUAGES / COURSE_DATA. Returns None if
    lang_key is not one of the four supported languages and the mode
    is not a general Free Chat request (Explain/Example/Quiz/Culture
    still require a specific lesson to stay tightly grounded).
    """

    language_facts = get_tutor_language_facts(lang_key)

    if not language_facts:

        normalized_mode = (mode or "").strip().lower()

        if normalized_mode in ("", "chat"):
            return build_general_tutor_context()

        return None

    lowered_message = (user_message or "").lower()

    if level_num is not None:
        levels_to_scan = [level_num]
    else:
        levels_to_scan = list(
            COURSE_DATA.get(lang_key, {}).keys()
        )

    all_vocabulary = extract_lesson_vocabulary(lang_key, level_num)
    all_mistakes = []

    for scanned_level in levels_to_scan:

        steps = (
            COURSE_DATA.get(lang_key, {})
            .get(scanned_level, {})
            .get("steps", [])
        )

        for step in steps:

            # ---------- COMMON MISTAKE EXTRACTION ----------

            wrong_feedback = step.get("wrongFeedback")
            correct_feedback = step.get("correctFeedback")

            if wrong_feedback:
                all_mistakes.append({
                    "question": step.get("question") or step.get("prompt") or "",
                    "wrong_feedback": wrong_feedback,
                    "correct_feedback": correct_feedback or ""
                })

            for turn in step.get("turns", []):

                turn_wrong_feedback = turn.get("wrongFeedback")

                if turn_wrong_feedback:
                    all_mistakes.append({
                        "question": turn.get("prompt", ""),
                        "wrong_feedback": turn_wrong_feedback,
                        "correct_feedback": turn.get("correctFeedback", "")
                    })

    matched_vocabulary = [
        item
        for item in all_vocabulary
        if item["term"].lower() in lowered_message
        or item["meaning"].lower() in lowered_message
    ]

    if matched_vocabulary:
        vocabulary = matched_vocabulary[:TUTOR_MAX_VOCABULARY_ITEMS]
    else:
        vocabulary = all_vocabulary[:TUTOR_MAX_VOCABULARY_ITEMS]

    return {
        "lang_key": lang_key,
        "level_num": level_num,
        "language_facts": language_facts,
        "vocabulary": vocabulary,
        "common_mistakes": all_mistakes[:TUTOR_MAX_MISTAKE_ITEMS]
    }


def build_general_tutor_system_prompt(grounded_context):
    """
    Renders a system prompt covering all four supported languages at
    once, for Free Chat requests made without a specific lesson open.
    """

    language_summaries = "\n\n".join(
        f"{facts['display_name']} ({facts['lang_key']}):\n"
        f"- About: {facts['about']}\n"
        f"- Speakers: {facts['speakers']}\n"
        f"- Location: {facts['location']}"
        for facts in grounded_context["all_language_facts"]
    ) or "No language facts available yet."

    vocabulary_lines = "\n".join(
        f"- [{item['lang_key']}] {item['term']} = {item['meaning']} "
        f"({item['note']})".strip()
        for item in grounded_context["vocabulary"]
    ) or "No sample vocabulary available yet."

    return (
        "You are the AI Tutor inside Malaysian Linguistics Lab - "
        "a knowledgeable, friendly LANGUAGE AND LINGUISTICS "
        "tutor. This website's four focus languages are Iban, "
        "Kadazan-Dusun, Bidayuh, and Mah Meri, but as a linguistics "
        "tutor you can also discuss any other language in the world "
        "and any linguistics topic.\n\n"

        "No specific lesson is currently open, so this is a Free Chat "
        "conversation. Here is background on the site's four "
        "languages, for reference and comparisons:\n\n"

        f"{language_summaries}\n\n"

        "Sample ground truth vocabulary you may use for these four "
        "languages:\n"
        f"{vocabulary_lines}\n\n"

        "HOW TO ANSWER - priority order:\n"
        "1. FIRST, check if the facts/vocabulary above answer the "
        "question. If so, answer using that verified data, and make "
        "clear it comes from this course.\n"
        "2. IF the question is about a language or linguistics topic "
        "NOT covered above (any language in the world, phonetics, "
        "grammar, morphology, syntax, etymology, writing systems, "
        "language families, dialects, endangered languages, "
        "orthography, comparative linguistics, language learning, "
        "language history or culture), you MAY answer using your own "
        "general knowledge. Say plainly when you're using general "
        "knowledge rather than this course's verified data, and be "
        "honest about uncertainty for obscure or hard-to-verify "
        "claims (e.g. exact \"longest/shortest word\" records) rather "
        "than confidently inventing specifics.\n"
        "3. IF the question is not about language/linguistics at all "
        "(e.g. maths, politics, programming, medicine, sports, "
        "celebrities, general trivia), reply with EXACTLY this "
        f"refusal and nothing else: \"{TUTOR_OFFTOPIC_REFUSAL}\" Do "
        "not answer the off-topic question, even partially.\n\n"

        "Be warm, natural, and conversational, like a helpful tutor "
        "chatting with a student, and remember what was said earlier "
        "in this same conversation.\n\n"

        "Formatting style:\n"
        "- Use Markdown: **bold** for key vocabulary/terms, bullet "
        "or numbered lists, and a small table when comparing two "
        "languages side by side.\n"
        "- Keep replies concise and easy to read in a chat bubble - "
        "avoid huge walls of text."
    )


def build_tutor_system_prompt(lang_key, level_num, user_message, mode=None):
    """
    Renders the final system prompt string from the grounded context.
    Returns None if lang_key is not one of the four supported languages
    and the request is not a general Free Chat request, so the caller
    can short-circuit with a canned redirection reply instead of
    calling the AI at all.
    """

    grounded_context = build_tutor_grounded_context(
        lang_key,
        level_num,
        user_message,
        mode
    )

    if not grounded_context:
        return None

    if grounded_context.get("general_mode"):
        return build_general_tutor_system_prompt(grounded_context)

    language_facts = grounded_context["language_facts"]

    vocabulary_lines = "\n".join(
        f"- {item['term']} = {item['meaning']} ({item['note']})".strip()
        for item in grounded_context["vocabulary"]
    ) or "No vocabulary matched this question yet."

    mistake_lines = "\n".join(
        f"- Common mistake: {item['wrong_feedback']} "
        f"(Correct: {item['correct_feedback']})"
        for item in grounded_context["common_mistakes"]
    ) or "No recorded common mistakes for this level yet."

    return (
        "You are the AI Tutor inside Malaysian Linguistics Lab - "
        "a knowledgeable, friendly LANGUAGE AND LINGUISTICS "
        "tutor, not just a narrow course chatbot.\n\n"

        f"Currently open lesson: {language_facts['display_name']}\n"
        f"Content status: {language_facts['verification_status']}\n"
        f"About: {language_facts['about']}\n"
        f"Speakers: {language_facts['speakers']}\n"
        f"Location: {language_facts['location']}\n"
        f"Preservation notes: {language_facts['preservation']}\n\n"

        "Verified lesson vocabulary (ground truth for this lesson):\n"
        f"{vocabulary_lines}\n\n"

        "Verified common learner mistakes for this lesson:\n"
        f"{mistake_lines}\n\n"

        "HOW TO ANSWER - priority order:\n"
        "1. FIRST, check whether the lesson vocabulary/facts above "
        "answer the question (for example \"What does Selamat datai "
        "mean?\"). If so, answer using ONLY that verified data, and "
        "make clear the answer comes from this lesson.\n"
        "2. IF the lesson does not cover it, you MAY answer using "
        "your own general knowledge of linguistics and world "
        "languages - this is not limited to Iban/Kadazan-Dusun/"
        "Bidayuh/Mah Meri. Allowed general-knowledge topics include: "
        "any language in the world, linguistics, phonetics, "
        "phonology, grammar, morphology, syntax, vocabulary, "
        "etymology, writing systems, language families, dialects, "
        "endangered languages, orthography, comparative linguistics, "
        "language learning, language history, and language culture. "
        "Clearly say when you're drawing on general knowledge rather "
        "than this lesson's verified data, and be honest about "
        "uncertainty for obscure or hard-to-verify claims (e.g. exact "
        "\"longest/shortest word\" records) instead of confidently "
        "inventing specifics.\n"
        "3. IF a question is not about language/linguistics at all "
        "(e.g. maths, politics, programming, medicine, sports, "
        "celebrities, general trivia), reply with EXACTLY this "
        f"refusal and nothing else: \"{TUTOR_OFFTOPIC_REFUSAL}\" Do "
        "not answer the off-topic question, even partially.\n\n"

        "Formatting style:\n"
        "- Use Markdown: **bold** for key vocabulary/terms, bullet "
        "or numbered lists, and a small table when comparing two "
        "languages or forms side by side.\n"
        "- Keep replies concise and easy to read in a chat bubble - "
        "avoid huge walls of text."
    )


def sanitize_tutor_history(raw_history):
    """
    Validates and trims client-supplied conversation history so it can
    be safely forwarded to the AI provider. Only "user"/"assistant"
    roles with short string content are kept, capped to the most
    recent TUTOR_MAX_HISTORY_TURNS entries.
    """

    if not isinstance(raw_history, list):
        return []

    cleaned = []

    for entry in raw_history:

        if not isinstance(entry, dict):
            continue

        role = entry.get("role")
        content = entry.get("content")

        if role not in ("user", "assistant"):
            continue

        if not isinstance(content, str) or not content.strip():
            continue

        cleaned.append({
            "role": role,
            "content": content.strip()[:TUTOR_MAX_HISTORY_CHARS]
        })

    return cleaned[-TUTOR_MAX_HISTORY_TURNS:]


def call_openai(system_prompt, user_message, history=None):
    """
    Calls the OpenAI Responses API. Always returns either the parsed
    JSON response (dict, on success) or a friendly plain-string error
    message (on any failure) - never raises outside this function.
    """

    conversation_input = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    for turn in sanitize_tutor_history(history):
        conversation_input.append(turn)

    conversation_input.append({
        "role": "user",
        "content": user_message
    })

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",

            headers={
                "Authorization": f"Bearer {AI_TUTOR_API_KEY}",
                "Content-Type": "application/json"
            },

            json={
                "model": AI_TUTOR_MODEL,
                "input": conversation_input
            },

            timeout=30
        )

    except requests.exceptions.Timeout:
        return "The tutor took too long to respond."

    except requests.exceptions.RequestException:
        return "Unable to reach the AI service."

    except Exception:
        return "Unable to reach the AI service."

    if response.status_code == 401:
        return "AI Tutor is not configured correctly."

    if response.status_code == 429:
        return "The tutor is busy. Please try again shortly."

    if response.status_code >= 500:
        return "The tutor is temporarily unavailable."

    if response.status_code != 200:
        return "The tutor could not generate a valid response."

    try:
        return response.json()

    except ValueError:
        return "The tutor could not generate a valid response."


def extract_reply(response_json):
    """
    Extracts only the assistant's plain text from a Responses API
    payload. Always returns a string, never raises.
    """

    try:
        output_text = response_json.get("output_text")

        if output_text:
            return output_text

        for output_item in response_json.get("output", []):

            for content_piece in output_item.get("content", []):

                text = content_piece.get("text")

                if text:
                    return text

        return "The tutor could not generate a valid response."

    except Exception:
        return "The tutor could not generate a valid response."


def get_tutor_quiz_steps(lang_key, level_num):
    steps = []

    if level_num is not None:
        levels_to_scan = [level_num]
    else:
        levels_to_scan = list(
            COURSE_DATA.get(lang_key, {}).keys()
        )

    for scanned_level in levels_to_scan:
        for step in (
            COURSE_DATA.get(lang_key, {})
            .get(scanned_level, {})
            .get("steps", [])
        ):
            def append_quiz_candidate(candidate_step, prompt_text=None):
                if (
                    not isinstance(candidate_step.get("options"), list)
                    or not candidate_step.get("options")
                    or not isinstance(candidate_step.get("correctIndex"), int)
                ):
                    return

                question_text = (
                    prompt_text
                    or candidate_step.get("question")
                    or candidate_step.get("prompt")
                    or candidate_step.get("expression")
                    or "Choose the correct answer."
                )

                steps.append({
                    "question": question_text,
                    "options": candidate_step.get("options", []),
                    "correctIndex": candidate_step.get("correctIndex", 0),
                    "correctFeedback": candidate_step.get("correctFeedback", ""),
                    "wrongFeedback": candidate_step.get("wrongFeedback", "")
                })

            if (
                step.get("type") == "quiz"
            ):
                append_quiz_candidate(step)

            if step.get("type") in {"discover", "respond"}:
                append_quiz_candidate(step)

            if step.get("type") == "conversation":
                for turn in step.get("turns", []):
                    append_quiz_candidate(turn)

    return steps


TUTOR_QUIZ_MAX_DISTRACTORS = 3


def generate_vocabulary_quiz_candidates(lang_key, level_num):
    """
    Generates extra multiple-choice quiz questions directly from the
    lesson's real vocabulary (word/meaning pairs), in BOTH directions
    ("what does X mean?" and "which word means Y?"). This is still
    100% grounded in real COURSE_DATA - nothing is invented - but adds
    quiz variety beyond only the hand-authored quiz/discover/respond
    steps, and gives Quiz something to draw on even for lessons that
    have no explicitly authored quiz question.
    """

    vocabulary = extract_lesson_vocabulary(lang_key, level_num)

    seen_terms = set()
    unique_vocabulary = []

    for item in vocabulary:

        key = item["term"].strip().lower()

        if key in seen_terms:
            continue

        seen_terms.add(key)
        unique_vocabulary.append(item)

    if len(unique_vocabulary) < 4:
        return []

    candidates = []

    for item in unique_vocabulary:

        distractor_pool = [
            other for other in unique_vocabulary
            if other["term"] != item["term"]
        ]

        distractors = random.sample(
            distractor_pool,
            min(TUTOR_QUIZ_MAX_DISTRACTORS, len(distractor_pool))
        )

        note_suffix = f" {item['note']}".rstrip() if item.get("note") else ""

        # ---------- word -> meaning ----------

        options_forward = [item["meaning"]] + [
            other["meaning"] for other in distractors
        ]
        random.shuffle(options_forward)

        candidates.append({
            "question": f"What does \u201c{item['term']}\u201d mean?",
            "options": options_forward,
            "correctIndex": options_forward.index(item["meaning"]),
            "correctFeedback": (
                f"\u201c{item['term']}\u201d means "
                f"\u201c{item['meaning']}\u201d.{note_suffix}"
            ),
            "wrongFeedback": (
                f"\u201c{item['term']}\u201d actually means "
                f"\u201c{item['meaning']}\u201d.{note_suffix}"
            )
        })

        # ---------- meaning -> word ----------

        options_backward = [item["term"]] + [
            other["term"] for other in distractors
        ]
        random.shuffle(options_backward)

        candidates.append({
            "question": f"Which word means \u201c{item['meaning']}\u201d?",
            "options": options_backward,
            "correctIndex": options_backward.index(item["term"]),
            "correctFeedback": (
                f"\u201c{item['term']}\u201d means "
                f"\u201c{item['meaning']}\u201d.{note_suffix}"
            ),
            "wrongFeedback": (
                f"The correct word is \u201c{item['term']}\u201d "
                f"(\u201c{item['meaning']}\u201d).{note_suffix}"
            )
        })

    return candidates


def get_all_tutor_quiz_candidates(lang_key, level_num):
    """
    Combines hand-authored quiz-eligible steps with generated
    vocabulary flashcard questions (both directions), so Quiz always
    has a varied pool to draw from instead of repeating the same
    handful of authored questions. Falls back to the whole language's
    course data if this specific level has nothing quiz-eligible.
    """

    authored = get_tutor_quiz_steps(lang_key, level_num)
    vocabulary_based = generate_vocabulary_quiz_candidates(lang_key, level_num)

    if not authored and not vocabulary_based and level_num is not None:
        authored = get_tutor_quiz_steps(lang_key, None)
        vocabulary_based = generate_vocabulary_quiz_candidates(lang_key, None)

    return authored + vocabulary_based


def start_tutor_quiz(lang_key, level_num):
    quiz_candidates = get_all_tutor_quiz_candidates(lang_key, level_num)

    if not quiz_candidates:
        return (
            "I could not find a quiz question for this lesson yet. "
            "Try Explain or Example for now."
        )

    score_key = f"{lang_key}|{level_num}"

    # Avoid repeating a question that was just asked, for as long as
    # there is enough variety in the pool to do so. Once the whole
    # pool has been cycled through, it naturally starts reusing
    # questions again (there's no infinite well of course data).
    recent_by_key = session.get("tutor_quiz_recent") or {}
    recently_asked = set(recent_by_key.get(score_key, []))

    fresh_candidates = [
        candidate for candidate in quiz_candidates
        if candidate.get("question") not in recently_asked
    ]

    pool = fresh_candidates if fresh_candidates else quiz_candidates

    selected_step = pool[secrets.randbelow(len(pool))]

    question_text = selected_step.get("question", "")

    recent_list = recent_by_key.get(score_key, [])
    recent_list.append(question_text)

    max_recent = max(1, min(6, len(quiz_candidates) - 1))
    recent_by_key[score_key] = recent_list[-max_recent:]

    session["tutor_quiz_recent"] = recent_by_key

    session["tutor_quiz_state"] = {
        "lang_key": lang_key,
        "level_num": level_num,
        "question": question_text,
        "options": selected_step.get("options", []),
        "correct_index": selected_step.get("correctIndex", 0),
        "correct_feedback": selected_step.get("correctFeedback", ""),
        "wrong_feedback": selected_step.get("wrongFeedback", "")
    }

    option_lines = "\n".join(
        f"{index + 1}. {option}"
        for index, option in enumerate(
            selected_step.get("options", [])
        )
    )

    existing_score = (session.get("tutor_quiz_scores") or {}).get(score_key)

    question_number = (
        existing_score.get("total", 0) + 1 if existing_score else 1
    )

    score_line = ""

    if existing_score and existing_score.get("total"):
        score_line = (
            f"\ud83c\udfc6 Score so far: "
            f"{existing_score['correct']}/{existing_score['total']}\n"
        )

    return (
        f"\ud83e\udde9 Quiz time \u2014 Question {question_number}\n"
        f"{question_text}\n\n"
        f"{option_lines}\n\n"
        f"{score_line}"
        "Reply with the option number (e.g. \"1\") or the full answer text."
    )


TUTOR_QUIZ_CORRECT_ENCOURAGEMENT = [
    "Great job!",
    "Nicely done!",
    "You're getting the hang of this!",
    "Excellent work!",
    "Awesome, keep it up!"
]

TUTOR_QUIZ_WRONG_ENCOURAGEMENT = [
    "No worries, that's how learning works!",
    "Close! Keep going, you'll get the next one.",
    "Don't worry about it, mistakes help you learn.",
    "That's okay, let's keep practicing!"
]


def grade_tutor_quiz_answer(user_message):
    quiz_state = session.get("tutor_quiz_state")

    if not quiz_state:
        return None

    options = quiz_state.get("options", [])

    if not options:
        session.pop("tutor_quiz_state", None)
        return "The tutor could not generate a valid response."

    answer_text = (user_message or "").strip().lower()

    selected_index = None

    if answer_text.isdigit():
        option_number = int(answer_text)

        if 1 <= option_number <= len(options):
            selected_index = option_number - 1

    if selected_index is None:
        for index, option in enumerate(options):
            if answer_text == str(option).strip().lower():
                selected_index = index
                break

    if selected_index is None:
        return (
            "I didn't quite catch that \u2014 please reply with the "
            "option number (e.g. \"1\") or the exact option text."
        )

    correct_index = quiz_state.get("correct_index")

    is_correct = (selected_index == correct_index)

    feedback = (
        quiz_state.get("correct_feedback")
        if is_correct
        else quiz_state.get("wrong_feedback")
    )

    correct_option_text = ""

    if (
        not is_correct
        and isinstance(correct_index, int)
        and 0 <= correct_index < len(options)
    ):
        correct_option_text = str(options[correct_index])

    score_key = (
        f"{quiz_state.get('lang_key')}|{quiz_state.get('level_num')}"
    )

    quiz_scores = session.get("tutor_quiz_scores") or {}

    score = dict(quiz_scores.get(score_key, {"correct": 0, "total": 0}))

    score["total"] += 1

    if is_correct:
        score["correct"] += 1

    quiz_scores[score_key] = score

    session["tutor_quiz_scores"] = quiz_scores

    session.pop("tutor_quiz_state", None)

    if is_correct:
        status_text = "\u2705 Correct!"
        encouragement = TUTOR_QUIZ_CORRECT_ENCOURAGEMENT[
            secrets.randbelow(len(TUTOR_QUIZ_CORRECT_ENCOURAGEMENT))
        ]
        explanation_line = f"{feedback}" if feedback else ""
    else:
        status_text = "\u274c Not quite."
        encouragement = TUTOR_QUIZ_WRONG_ENCOURAGEMENT[
            secrets.randbelow(len(TUTOR_QUIZ_WRONG_ENCOURAGEMENT))
        ]
        correct_line = (
            f"The correct answer was: {correct_option_text}.\n"
            if correct_option_text
            else ""
        )
        explanation_line = f"{correct_line}{feedback}".strip()

    explanation_block = (
        f"\n\n{explanation_line}" if explanation_line else ""
    )

    return (
        f"{status_text} {encouragement}"
        f"{explanation_block}\n\n"
        f"\ud83c\udfc6 Score: {score['correct']}/{score['total']}\n\n"
        "Want another question? Press Quiz again, or ask me anything else."
    )


def get_mode_user_message(mode, user_message):
    normalized_mode = (mode or "").strip().lower()

    cleaned_user_message = (user_message or "").strip()

    if cleaned_user_message:
        return cleaned_user_message

    mode_defaults = {
        "explain": (
            "Explain today's lesson like a teacher would: cover the "
            "meaning, grammar, pronunciation, usage, common learner "
            "mistakes, and any helpful notes, in plain beginner-"
            "friendly language."
        ),
        "example": (
            "Give a short, natural mini dialogue (2-4 lines) using "
            "this lesson's vocabulary in a realistic everyday "
            "situation, with a translation and the important "
            "vocabulary words highlighted in bold."
        ),
        "culture": (
            "Explain the cultural background related to this "
            "language: historical/traditional background, traditions "
            "or customs, an interesting fact, how the language is "
            "used in modern daily life, the community who speaks it, "
            "and its language preservation status."
        )
    }

    return mode_defaults.get(
        normalized_mode,
        "Help me learn this lesson."
    )


def get_mode_system_instruction(mode):
    normalized_mode = (mode or "").strip().lower()

    mode_instructions = {
        "explain": (
            "Current mode is Explain - TEACHER STYLE. Structure your "
            "answer with short labelled sections (use bold labels or "
            "a bullet list) covering, where relevant: **Meaning**, "
            "**Grammar**, **Pronunciation**, **Usage**, **Common "
            "mistakes**, and a closing **Note**. Use the lesson's "
            "verified vocabulary/facts first (priority 1); if the "
            "lesson doesn't cover a part (e.g. pronunciation isn't "
            "recorded), you may use general linguistic knowledge "
            "(priority 2) and say so, rather than skipping it "
            "silently. This mode is about deep, structured "
            "understanding, NOT examples or dialogues."
        ),
        "example": (
            "Current mode is Example - CONVERSATION STYLE. Do NOT "
            "give a structured teacher-style breakdown. Instead, "
            "write ONE short, natural mini dialogue (2-4 lines, "
            "labelled A: / B:) set in a realistic everyday situation "
            "using this lesson's real vocabulary, followed by a "
            "plain-English translation of the dialogue. Bold the "
            "important vocabulary word(s) the first time they appear. "
            "Include pronunciation only if it is available; otherwise "
            "do not guess. Keep it short and vivid, like a scene, not "
            "a lecture."
        ),
        "culture": (
            "Current mode is Culture - CULTURAL BACKGROUND STYLE. "
            "Cover, briefly and only where supported by verified data "
            "or well-established general knowledge: historical/"
            "traditional **Background**, **Traditions** or customs, "
            "an **Interesting fact**, **Modern usage** in daily life "
            "today, the **Community** who speaks it, and its "
            "**Preservation** status. Never invent specific customs, "
            "festivals, or historical claims that are not backed by "
            "the data given to you or solid general knowledge - if "
            "unsure, say the detail isn't verified yet instead of "
            "guessing. Do not teach vocabulary lists here unless a "
            "word is essential to a cultural point."
        ),
        "chat": (
            "Current mode is Free Chat. Have a natural, warm, helpful "
            "conversation, like ChatGPT/Claude, covering any language "
            "or linguistics topic (not just this course's languages). "
            "Remember and refer back to what the learner said earlier "
            "in this same conversation when relevant."
        )
    }

    return mode_instructions.get(normalized_mode, "")


# answer_tutor_query is imported from tutor_service
# (Planner → Retriever → Validator → optional LLM rewrite)


# ================= ROUTES =================

# ================= EXPLORE UNLOCK DATA =================

EXPLORE_UNLOCKS = {

    "iban": {

        1: {
            "journey_number": "Journey 01",
            "journey_title": "A First Meeting",

            "eyebrow": "Language You Now Recognise",
            "title": "The language is beginning to open up",

            "description": (
                "You have completed A First Meeting. "
                "These expressions are no longer unfamiliar — "
                "they are now part of how you understand the Iban world."
            ),

            "world_message": (
                "You arrived as a visitor. "
                "Now, parts of the language can speak back to you."
            ),

            "expressions": [
                {
                    "expression": "Selamat datai",
                    "meaning": "Welcome",
                    "context": "A welcoming expression",
                    "recognition": "You recognise this"
                },
                {
                    "expression": "Nama berita nuan?",
                    "meaning": "How are you?",
                    "context": "A question in conversation",
                    "recognition": "You understand this"
                },
                {
                    "expression": "Manah",
                    "meaning": "Good / Fine",
                    "context": "A simple positive response",
                    "recognition": "You can respond with this"
                },
                {
                    "expression": "Sapa nama nuan?",
                    "meaning": "What is your name?",
                    "context": "A question when meeting someone",
                    "recognition": "You understand this question"
                },
                {
                    "expression": "Nama aku ...",
                    "meaning": "My name is ...",
                    "context": "A way to introduce yourself",
                    "recognition": "You can introduce yourself"
                }
            ],

            "echoes": [
                {
                    "expression": "Selamat datai",
                    "meaning": "Welcome",
                    "label": "You know this now"
                },
                {
                    "expression": "Nama berita nuan?",
                    "meaning": "How are you?",
                    "label": "You have heard this before"
                },
                {
                    "expression": "Manah",
                    "meaning": "Good / Fine",
                    "label": "You can answer with this"
                }
            ]
        }

    },

    # Keys must match LANGUAGES / COURSE_DATA slugs (kadazan-dusun, not kadazan).
    "kadazan-dusun": {},

    "bidayuh": {},

    "mah-meri": {},

}

# Ensure the full app schema exists for WSGI/Gunicorn (e.g. Render).
# `init_db()` is CREATE TABLE IF NOT EXISTS / additive ALTER only — safe for
# existing data. Startup lock reduces duplicate seed races across workers.
try:
    with startup_lock():
        init_db()
        # Seed tutor content tables from course data (no-op if already populated).
        try:
            seed_tutor_content(COURSE_DATA, LANGUAGES, EXPLORE_UNLOCKS)
            sync_missing_vocabulary_from_course(COURSE_DATA)
            import_verified_vocabulary_packs()
        except Exception as _seed_exc:
            print(f"[tutor seed] warning: {_seed_exc}")
except Exception as _init_db_exc:
    print(f"[db init] error: {_init_db_exc}")
    raise

# ================= PASSWORD RESET TOOLS =================

RESET_TOKEN_LIFETIME = 30 * 60


def hash_reset_token(token):

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_reset_token(user_id):

    raw_token = secrets.token_urlsafe(48)

    token_hash = hash_reset_token(
        raw_token
    )

    created_at = int(
        time.time()
    )

    conn = get_db()

    conn.execute(
        """
        UPDATE password_reset_tokens

        SET used = 1

        WHERE user_id = ?
          AND used = 0
        """,
        (user_id,)
    )

    conn.execute(
        """
        INSERT INTO password_reset_tokens (
            user_id,
            token_hash,
            created_at,
            used
        )

        VALUES (?, ?, ?, 0)
        """,
        (
            user_id,
            token_hash,
            created_at
        )
    )

    conn.commit()
    conn.close()

    return raw_token


# ================= FORGOT PASSWORD =================

@app.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
@limiter.limit("5 per minute", methods=["POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form[
            "email"
        ].strip().lower()

        conn = get_db()

        user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(email) = ?
              AND provider = 'local'
            """,
            (email,)
        ).fetchone()

        conn.close()


        if user:

            reset_token = create_reset_token(
                user["id"]
            )

            reset_link = url_for(
                "reset_password",
                token=reset_token,
                _external=True
            )

            # Dev-only console delivery — never emit reset links in production logs.
            if (
                os.getenv("FLASK_DEBUG", "false").lower() == "true"
                or _FLASK_ENV == "development"
            ):
                print("\n")
                print("=" * 70)
                print("PASSWORD RESET LINK")
                print(reset_link)
                print("This link expires in 30 minutes.")
                print("=" * 70)
                print("\n")


        flash(
            "If an account exists for that email, "
            "a password reset link has been created."
        )

        return redirect(
            url_for("forgot_password")
        )


    return render_template(
        "forgot_password.html"
    )

# ================= RESET PASSWORD =================

@app.route(
    "/reset-password/<token>",
    methods=["GET", "POST"]
)
def reset_password(token):

    token_hash = hash_reset_token(
        token
    )

    current_time = int(
        time.time()
    )

    conn = get_db()

    reset_record = conn.execute(
        """
        SELECT
            password_reset_tokens.id,
            password_reset_tokens.user_id,
            password_reset_tokens.created_at,
            password_reset_tokens.used

        FROM password_reset_tokens

        WHERE token_hash = ?
        """,
        (token_hash,)
    ).fetchone()

    conn.close()


    if not reset_record:

        flash(
            "This password reset link is invalid."
        )

        return redirect(
            url_for("forgot_password")
        )


    token_age = (
        current_time
        - reset_record["created_at"]
    )


    if (
        reset_record["used"] == 1
        or token_age > RESET_TOKEN_LIFETIME
        or token_age < 0
    ):

        flash(
            "This password reset link has expired "
            "or has already been used."
        )

        return redirect(
            url_for("forgot_password")
        )


    if request.method == "POST":

        password = request.form[
            "password"
        ]

        confirm_password = request.form[
            "confirm_password"
        ]


        if len(password) < 8:

            flash(
                "Password must be at least 8 characters."
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )


        if password != confirm_password:

            flash(
                "Passwords do not match."
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )


        conn = get_db()

        conn.execute(
            """
            UPDATE users

            SET password = ?

            WHERE id = ?
            """,
            (
                generate_password_hash(
                    password
                ),
                reset_record["user_id"]
            )
        )


        conn.execute(
            """
            UPDATE password_reset_tokens

            SET used = 1

            WHERE id = ?
            """,
            (reset_record["id"],)
        )


        conn.commit()
        conn.close()


        session.clear()


        flash(
            "Your password has been reset. "
            "Please log in with your new password."
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "reset_password.html"
    )

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )




# ================= REGISTER =================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
@limiter.limit("5 per minute", methods=["POST"])
def register():

    if request.method == "POST":

        username = request.form[
            "username"
        ].strip()

        email = request.form[
            "email"
        ].strip().lower()

        password = request.form[
            "password"
        ]

        confirm_password = request.form[
            "confirm_password"
        ]


        # ---------- USERNAME CHECK ----------

        if len(username) < 3:

            flash(
                "Username must be at least 3 characters."
            )

            return redirect(
                url_for("register")
            )


        if len(username) > 30:

            flash(
                "Username must not exceed 30 characters."
            )

            return redirect(
                url_for("register")
            )


        # ---------- EMAIL CHECK ----------

        if (
            not email
            or "@" not in email
        ):

            flash(
                "Please enter a valid email address."
            )

            return redirect(
                url_for("register")
            )


        # ---------- PASSWORD CHECK ----------

        if len(password) < 8:

            flash(
                "Password must be at least 8 characters."
            )

            return redirect(
                url_for("register")
            )


        if len(password) > 128:

            flash(
                "Password is too long."
            )

            return redirect(
                url_for("register")
            )


        if password != confirm_password:

            flash(
                "Passwords do not match."
            )

            return redirect(
                url_for("register")
            )


        # ---------- DUPLICATE CHECK ----------

        conn = get_db()


        existing_username = conn.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (
                username,
            )
        ).fetchone()


        if existing_username:

            conn.close()

            flash(
                "Username already exists."
            )

            return redirect(
                url_for("register")
            )


        existing_email = conn.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(email) = ?
            """,
            (
                email,
            )
        ).fetchone()


        if existing_email:

            conn.close()

            flash(
                "An account with this email already exists."
            )

            return redirect(
                url_for("register")
            )


        # ---------- CREATE ACCOUNT ----------

        conn.execute(
            """
            INSERT INTO users (
                username,
                password,
                provider,
                provider_user_id,
                email
            )

            VALUES (
                ?,
                ?,
                'local',
                NULL,
                ?
            )
            """,
            (
                username,

                generate_password_hash(
                    password
                ),

                email
            )
        )


        conn.commit()

        conn.close()


        flash(
            "Account created! Please log in."
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )

# ================= LOGIN =================

@app.route(
    "/login",
    methods=["GET", "POST"]
)

@limiter.limit("5 per minute", methods=["POST"])

def login():

    if request.method == "POST":

        username = request.form[
            "username"
        ].strip()

        password = request.form[
            "password"
        ]

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            _establish_login_session(
                user["id"],
                user["username"],
            )

            _achievement_hook(user["id"], "first_login")

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid username or password"
        )

    return render_template(
        "login.html"
    )

# ================= GOOGLE LOGIN =================

@app.route("/login/google")
def google_login():

    if "google" not in oauth._clients:

        flash(
            "Google login is not available."
        )

        return redirect(
            url_for("login")
        )

    redirect_uri = url_for(
        "google_callback",
        _external=True
    )

    return oauth.google.authorize_redirect(
        redirect_uri
    )


# ================= GOOGLE CALLBACK =================

@app.route("/login/google/callback")
def google_callback():

    try:

        token = (
            oauth.google.authorize_access_token()
        )

        user_info = token.get(
            "userinfo"
        )

        if not user_info:

            user_info = (
                oauth.google.userinfo()
            )

    except Exception as error:

        print(
            "Google login error:",
            error
        )

        flash(
            "Google login could not be completed."
        )

        return redirect(
            url_for("login")
        )


    google_user_id = user_info.get(
        "sub"
    )

    email = user_info.get(
        "email"
    )

    email_verified = user_info.get(
        "email_verified",
        False
    )


    if (
        not google_user_id
        or not email
        or not email_verified
    ):

        flash(
            "A verified Google account is required."
        )

        return redirect(
            url_for("login")
        )


    conn = get_db()


    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE provider = ?
          AND provider_user_id = ?
        """,
        (
            "google",
            google_user_id
        )
    ).fetchone()


    if not user:

        existing_email_user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        if existing_email_user:

            conn.close()

            flash(
                "An account with this email already exists. "
                "Please use your original sign-in method."
            )

            return redirect(
                url_for("login")
            )


        base_username = (
            email.split("@")[0]
        )


        safe_username = "".join(
            character
            for character in base_username
            if (
                character.isalnum()
                or character in "_-"
            )
        )


        if len(safe_username) < 3:

            safe_username = "google_user"


        username = safe_username

        suffix = 1


        while conn.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone():

            username = (
                f"{safe_username}_{suffix}"
            )

            suffix += 1


        random_password = (
            secrets.token_urlsafe(32)
        )


        cursor = conn.execute(
            """
            INSERT INTO users (
                username,
                password,
                provider,
                provider_user_id,
                email
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                generate_password_hash(
                    random_password
                ),
                "google",
                google_user_id,
                email
            )
        )


        conn.commit()


        user_id = cursor.lastrowid


    else:

        user_id = user["id"]

        username = user["username"]


    conn.close()


    _establish_login_session(user_id, username)

    _achievement_hook(user_id, "first_login")

    return redirect(
        url_for("dashboard")
    )

# ================= DASHBOARD =================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    language_progress = {}

    for lang_key in LANGUAGES:

        completed_levels = (
            get_completed_levels(
                user_id,
                lang_key
            )
        )

        completed_count = len(
            completed_levels
        )

        total_levels = len(
            LEVEL_TITLES
        )

        # Clamp to 0–100 so orphan progress rows never produce >100% in the UI.
        percentage = max(
            0,
            min(
                100,
                round(
                    (
                        completed_count /
                        total_levels
                    ) * 100
                ) if total_levels else 0
            )
        )

        language_progress[
            lang_key
        ] = {
            "completed": min(completed_count, total_levels),
            "total": total_levels,
            "percentage": percentage
        }

    # Real vocabulary / lesson / quiz counts + deep links for the World
    # Explorer / Language Universe — never fabricated linguistic facts.
    conn = get_db()
    language_explorer_meta = {}
    for lang_key, lang_info in LANGUAGES.items():
        vocab_row = conn.execute(
            "SELECT COUNT(*) AS c FROM vocabulary WHERE language = ?",
            (lang_key,),
        ).fetchone()
        quiz_row = conn.execute(
            "SELECT COUNT(*) AS c FROM quiz WHERE language = ?",
            (lang_key,),
        ).fetchone()
        sample = conn.execute(
            """
            SELECT word, meaning_en
            FROM vocabulary
            WHERE language = ?
              AND word IS NOT NULL AND TRIM(word) != ''
            ORDER BY RANDOM()
            LIMIT 1
            """,
            (lang_key,),
        ).fetchone()
        lesson_count = len(COURSE_DATA.get(lang_key, {}) or {})
        sample_word = None
        if sample and sample["word"]:
            sample_word = {
                "word": sample["word"],
                "meaning": sample["meaning_en"] if sample["meaning_en"] else None,
            }
        language_explorer_meta[lang_key] = {
            "key": lang_key,
            "display_name": lang_info.get("display_name", lang_key),
            "region": lang_info.get("region"),
            "blurb": lang_info.get("blurb"),
            "vocab_count": vocab_row["c"] if vocab_row else 0,
            "lesson_count": lesson_count,
            "quiz_count": quiz_row["c"] if quiz_row else 0,
            "sample_word": sample_word,
            "dictionary_url": url_for("dictionary_page", lang=lang_key),
            "compare_url": url_for("compare_languages", a=lang_key),
            "learn_url": url_for("language_page", lang_key=lang_key),
            "quiz_url": url_for("quiz_page", lang=lang_key),
        }
    conn.close()

    daily_status = daily_quiz_status(session["user_id"])

    # Compact explorer stats derived only from real lesson + quiz progress.
    mastery_summary = get_user_mastery_summary(user_id)
    lessons_done = sum(int(p.get("completed") or 0) for p in language_progress.values())
    overall_lesson_pct = 0
    if language_progress:
        overall_lesson_pct = int(
            round(
                sum(int(p.get("percentage") or 0) for p in language_progress.values())
                / len(language_progress)
            )
        )
    quiz_correct = int(mastery_summary.get("correct") or 0)
    xp = lessons_done * 100 + quiz_correct * 25
    level = max(1, 1 + (xp // 300))
    xp_into_level = xp % 300
    xp_next = 300
    explorer_stats = {
        "level": level,
        "xp": xp,
        "xp_current": xp_into_level,
        "xp_next": xp_next,
        "xp_pct": int(round((xp_into_level / xp_next) * 100)) if xp_next else 0,
        # Canonical streak = consecutive active days (not quiz-answer streak).
        "streak": get_activity_streak(user_id),
        "points": xp,
        "lesson_pct": overall_lesson_pct,
        "quiz_mastery_pct": int(mastery_summary.get("mastery_pct") or 0),
    }

    heritage_passport = get_heritage_passport(user_id)
    gallery = get_achievements_gallery(user_id)
    collection_teaser = {
        "earned": int(gallery.get("earned") or 0),
        "total": int(gallery.get("total") or 0),
        "percent": int(
            round(
                100
                * int(gallery.get("earned") or 0)
                / max(1, int(gallery.get("total") or 1))
            )
        ),
        "streak": explorer_stats["streak"],
    }

    return render_template(
        "dashboard.html",
        username=session["username"],
        language_progress=language_progress,
        language_explorer_meta=language_explorer_meta,
        daily_quiz=daily_status,
        explorer_stats=explorer_stats,
        heritage_passport=heritage_passport,
        collection_teaser=collection_teaser,
    )


# ================= LANGUAGE COMPARISON =================

@app.route("/compare")
def compare_languages():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    lang_keys = list(LANGUAGES.keys())

    default_a = lang_keys[0]

    default_b = (
        lang_keys[1]
        if len(lang_keys) > 1
        else lang_keys[0]
    )

    lang_a = request.args.get(
        "a",
        default_a
    )

    lang_b = request.args.get(
        "b",
        default_b
    )

    if lang_a not in LANGUAGES:
        lang_a = default_a

    if lang_b not in LANGUAGES:
        lang_b = default_b

    language_options = [
        {
            "lang_key": key,
            "display_name": LANGUAGES[key]["display_name"]
        }
        for key in lang_keys
    ]

    comparison_a = get_language_comparison_data(lang_a)
    comparison_b = get_language_comparison_data(lang_b)

    comparison_summary = compute_language_comparison_summary(
        comparison_a,
        comparison_b
    )

    return render_template(
        "compare.html",
        language_options=language_options,
        lang_a=lang_a,
        lang_b=lang_b,
        comparison_a=comparison_a,
        comparison_b=comparison_b,
        comparison_summary=comparison_summary
    )


@app.route("/api/compare/<lang_a>/<lang_b>")
def api_compare_languages(lang_a, lang_b):

    if "user_id" not in session:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    comparison_a = get_language_comparison_data(lang_a)
    comparison_b = get_language_comparison_data(lang_b)

    if not comparison_a or not comparison_b:
        return jsonify({
            "error": "Language not found"
        }), 404

    comparison_summary = compute_language_comparison_summary(
        comparison_a,
        comparison_b
    )

    return jsonify({
        "a": comparison_a,
        "b": comparison_b,
        "summary": comparison_summary
    })


# ================= DICTIONARY / VOCABULARY LIBRARY =================

_DICTIONARY_POS_OPTIONS = [
    "greeting", "noun", "verb", "adjective", "animal", "food",
    "number", "phrase", "expression",
]
_DICTIONARY_DIFFICULTY_OPTIONS = ["easy", "medium", "hard"]
_DICTIONARY_SORT_OPTIONS = [
    ("alpha", "A → Z"),
    ("alpha_desc", "Z → A"),
    ("length_desc", "Longest first"),
    ("length_asc", "Shortest first"),
    ("difficulty", "Difficulty"),
]


@app.route("/dictionary")
def dictionary_page():

    if "user_id" not in session:
        return redirect(url_for("login"))

    lang_keys = get_language_keys() or list(LANGUAGES.keys())
    vocab_counts = vocabulary_counts_by_language()
    language_options = [
        {
            "lang_key": key,
            "display_name": LANGUAGES.get(key, {}).get("display_name") or display_name(key),
            "vocab_count": int(vocab_counts.get(key, 0)),
        }
        for key in lang_keys
    ]
    default_lang = request.args.get("lang") or (lang_keys[0] if lang_keys else "")
    if default_lang not in lang_keys:
        default_lang = lang_keys[0] if lang_keys else ""

    return render_template(
        "dictionary.html",
        language_options=language_options,
        default_lang=default_lang,
        pos_options=_DICTIONARY_POS_OPTIONS,
        difficulty_options=_DICTIONARY_DIFFICULTY_OPTIONS,
        sort_options=_DICTIONARY_SORT_OPTIONS,
        vocab_target=TARGET_VOCAB_PER_LANGUAGE,
        vocab_coverage=vocabulary_coverage_report(),
    )


@app.route("/api/dictionary/search")
def api_dictionary_search():

    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    raw_lang = (request.args.get("language") or "").strip()
    language = resolve_language(raw_lang) or (raw_lang if raw_lang in get_language_keys() else None)
    if not language:
        return jsonify({
            "error": "unknown_language",
            "message": f"'{raw_lang}' is not a language in this course database.",
            "available_languages": list(get_language_keys()),
        }), 400

    query = (request.args.get("q") or "").strip()
    pos = (request.args.get("pos") or "").strip() or None
    difficulty = (request.args.get("difficulty") or "").strip() or None
    sort = (request.args.get("sort") or "alpha").strip()
    try:
        limit = max(1, min(100, int(request.args.get("limit", 30))))
    except (TypeError, ValueError):
        limit = 30
    try:
        offset = max(0, int(request.args.get("offset", 0)))
    except (TypeError, ValueError):
        offset = 0

    try:
        result = dictionary_search(
            language=language,
            query=query,
            part_of_speech=pos,
            difficulty=difficulty,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    except RetrievalError:
        return jsonify({
            "error": "retrieval_error",
            "message": "Could not search the dictionary right now.",
        }), 400

    result["language_display"] = display_name(language)
    rows = result.get("rows") or []
    saved_ids = get_saved_word_ids(session["user_id"], [r.get("id") for r in rows])
    for r in rows:
        r["is_saved"] = r.get("id") in saved_ids
    return jsonify(result)


@app.route("/api/dictionary/word/<int:word_id>")
def api_dictionary_word(word_id):

    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    raw_lang = (request.args.get("language") or "").strip()
    language = resolve_language(raw_lang) or (raw_lang if raw_lang in get_language_keys() else None)
    if not language:
        return jsonify({
            "error": "unknown_language",
            "message": f"'{raw_lang}' is not a language in this course database.",
            "available_languages": list(get_language_keys()),
        }), 400

    try:
        row = dictionary_word_by_id(language, word_id)
    except RetrievalError:
        return jsonify({
            "error": "retrieval_error",
            "message": "Could not load this word right now.",
        }), 400

    if not row:
        return jsonify({
            "error": "not_found",
            "message": "No word with this id exists for this language.",
        }), 404

    row["language_display"] = display_name(language)
    row["source"] = (row.get("source_ref") or "").strip() or "course_database"
    row["is_saved"] = bool(get_saved_word_ids(session["user_id"], [row.get("id")]))

    lesson_id = row.get("lesson_id")
    if lesson_id in LEVEL_TITLES:
        row["lesson_url"] = url_for("level_page", lang_key=language, level_num=lesson_id)
        row["lesson_title"] = LEVEL_TITLES[lesson_id]

    word_id = row.get("id")
    row["new_achievements"] = []
    row["view_recorded"] = False
    if isinstance(word_id, int):
        # Record only — do NOT run evaluate_achievements here.
        # The full sweep takes locks on users.db and was blocking Dictionary
        # search/pagination after vocabulary expansion (multi-click modal bug).
        row["view_recorded"] = bool(
            record_dictionary_view(session["user_id"], word_id, language)
        )

    return jsonify(row)


@app.route("/api/dictionary/random")
def api_dictionary_random():
    """Return one real vocabulary row (never fabricated)."""
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    raw_lang = (request.args.get("language") or "").strip()
    language = None
    if raw_lang:
        language = resolve_language(raw_lang) or (
            raw_lang if raw_lang in get_language_keys() else None
        )
        if not language:
            return jsonify({
                "error": "unknown_language",
                "message": f"'{raw_lang}' is not a language in this course database.",
                "available_languages": list(get_language_keys()),
            }), 400

    pos = (request.args.get("pos") or "").strip() or None
    difficulty = (request.args.get("difficulty") or "").strip() or None
    daily = (request.args.get("daily") or "").strip().lower() in ("1", "true", "yes")
    seed = None
    if daily:
        from datetime import datetime, timezone
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        seed = f"word|{day}|{session['user_id']}|{language or 'all'}"

    exclude_ids = []
    raw_exclude = (request.args.get("exclude") or "").strip()
    if raw_exclude:
        for part in raw_exclude.split(","):
            part = part.strip()
            if part.isdigit():
                exclude_ids.append(int(part))

    try:
        row = dictionary_random_word(
            language=language,
            part_of_speech=pos,
            difficulty=difficulty,
            seed=seed,
            exclude_ids=exclude_ids,
        )
    except RetrievalError:
        return jsonify({
            "error": "retrieval_error",
            "message": "Could not load a random word right now.",
        }), 400

    if not row:
        return jsonify({
            "ok": False,
            "reason": "empty",
            "message": "No vocabulary is available for this filter yet.",
        }), 200

    lang_key = row.get("language") or language
    row["language_display"] = display_name(lang_key) if lang_key else None
    row["source"] = "course_database"
    row["is_saved"] = bool(get_saved_word_ids(session["user_id"], [row.get("id")]))
    row["learn_url"] = url_for("language_page", lang_key=lang_key) if lang_key else None
    row["dictionary_url"] = (
        url_for("dictionary_page", lang=lang_key, q=row.get("word") or "")
        if lang_key
        else url_for("dictionary_page")
    )
    word_id = row.get("id")
    if isinstance(word_id, int) and lang_key:
        record_dictionary_view(session["user_id"], word_id, lang_key)
        row["new_achievements"] = evaluate_achievements(session["user_id"])
    return jsonify({"ok": True, "word": row})


# ================= SAVED WORDS (FAVORITES) =================

def get_saved_word_ids(user_id, vocabulary_ids):
    """Which of these vocabulary ids does this user currently have saved."""
    vocabulary_ids = [v for v in (vocabulary_ids or []) if isinstance(v, int)]
    if not vocabulary_ids:
        return set()

    conn = get_db()
    placeholders = ",".join("?" for _ in vocabulary_ids)
    rows = conn.execute(
        f"""
        SELECT vocabulary_id FROM saved_words
        WHERE user_id = ? AND vocabulary_id IN ({placeholders})
        """,
        [user_id, *vocabulary_ids],
    ).fetchall()
    conn.close()
    return {row["vocabulary_id"] for row in rows}


def add_saved_word(user_id, vocabulary_id, lang_key):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO saved_words (user_id, vocabulary_id, lang_key, created_at)
        VALUES (?, ?, ?, strftime('%s','now'))
        ON CONFLICT(user_id, vocabulary_id) DO NOTHING
        """,
        (user_id, vocabulary_id, lang_key),
    )
    conn.commit()
    conn.close()


def remove_saved_word(user_id, vocabulary_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM saved_words WHERE user_id = ? AND vocabulary_id = ?",
        (user_id, vocabulary_id),
    )
    conn.commit()
    conn.close()


def list_saved_words(user_id, lang_key=None):
    conn = get_db()
    if lang_key:
        rows = conn.execute(
            """
            SELECT v.*, sw.created_at AS saved_at, sw.lang_key AS saved_lang_key
            FROM saved_words sw
            JOIN vocabulary v ON v.id = sw.vocabulary_id
            WHERE sw.user_id = ? AND sw.lang_key = ?
            ORDER BY sw.created_at DESC
            """,
            (user_id, lang_key),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT v.*, sw.created_at AS saved_at, sw.lang_key AS saved_lang_key
            FROM saved_words sw
            JOIN vocabulary v ON v.id = sw.vocabulary_id
            WHERE sw.user_id = ?
            ORDER BY sw.created_at DESC
            """,
            (user_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


HERITAGE_PASSPORT_IMAGES = {
    "iban": "iban_bg.png",
    "kadazan-dusun": "kadazan_dusun_bg.png",
    "bidayuh": "bidayuh_bg.png",
    "mah-meri": "mah_meri_card_bg.png",
}


def get_heritage_passport(user_id):
    """Build passport cards from existing LANGUAGES + discovered rows only."""
    init_achievement_tables()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT lang_key, discovered_at
        FROM heritage_passport
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()
    discovered = {row["lang_key"]: int(row["discovered_at"]) for row in rows}

    cards = []
    for lang_key, lang_info in LANGUAGES.items():
        completed_levels = conn.execute(
            """
            SELECT COUNT(*) AS c FROM progress
            WHERE user_id = ? AND lang_key = ? AND completed = 1
            """,
            (user_id, lang_key),
        ).fetchone()["c"]
        try:
            vocab_explored = conn.execute(
                """
                SELECT COUNT(*) AS c FROM dictionary_views
                WHERE user_id = ? AND lang_key = ?
                """,
                (user_id, lang_key),
            ).fetchone()["c"]
        except Exception:
            vocab_explored = 0
        saved_count = conn.execute(
            """
            SELECT COUNT(*) AS c FROM saved_words
            WHERE user_id = ? AND lang_key = ?
            """,
            (user_id, lang_key),
        ).fetchone()["c"]
        vocab_total_row = conn.execute(
            "SELECT COUNT(*) AS c FROM vocabulary WHERE language = ?",
            (lang_key,),
        ).fetchone()
        vocab_total = int(vocab_total_row["c"]) if vocab_total_row else 0
        lesson_total = len(COURSE_DATA.get(lang_key, {}) or {})
        cards.append({
            "key": lang_key,
            "display_name": lang_info.get("display_name", lang_key),
            "region": lang_info.get("region") or "",
            "blurb": lang_info.get("blurb") or "",
            "image": HERITAGE_PASSPORT_IMAGES.get(lang_key),
            "discovered": lang_key in discovered,
            "discovered_at": discovered.get(lang_key),
            "lessons_completed": int(completed_levels),
            "lessons_total": int(lesson_total),
            "words_explored": int(vocab_explored),
            "words_saved": int(saved_count),
            "vocab_total": vocab_total,
            "learn_url": url_for("language_page", lang_key=lang_key),
            "dictionary_url": url_for("dictionary_page", lang=lang_key),
        })
    conn.close()
    discovered_count = sum(1 for card in cards if card["discovered"])
    return {
        "cards": cards,
        "discovered_count": discovered_count,
        "total": len(cards),
        "complete": bool(cards) and discovered_count >= len(cards),
        "journey_path": [
            "World",
            "Malaysia",
            "Place",
            "Language",
            "Words / Lessons",
            "Heritage Discovered",
        ],
    }


def mark_heritage_passport_discovery(user_id, lang_key):
    if lang_key not in LANGUAGES:
        return None
    now = int(time.time())
    conn = get_db()
    existing = conn.execute(
        """
        SELECT discovered_at FROM heritage_passport
        WHERE user_id = ? AND lang_key = ?
        """,
        (user_id, lang_key),
    ).fetchone()
    if existing:
        conn.close()
        passport = get_heritage_passport(user_id)
        passport["newly_discovered"] = False
        passport["language"] = lang_key
        return passport
    conn.execute(
        """
        INSERT INTO heritage_passport (user_id, lang_key, discovered_at)
        VALUES (?, ?, ?)
        """,
        (user_id, lang_key, now),
    )
    conn.commit()
    conn.close()
    passport = get_heritage_passport(user_id)
    passport["newly_discovered"] = True
    passport["language"] = lang_key
    return passport


@app.route("/api/passport/discover", methods=["POST"])
def api_passport_discover():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    raw_lang = (data.get("language") or "").strip()
    language = resolve_language(raw_lang) or (
        raw_lang if raw_lang in LANGUAGES else None
    )
    if not language or language not in LANGUAGES:
        return jsonify({
            "error": "unknown_language",
            "message": "Language is not part of this course.",
            "available_languages": list(LANGUAGES.keys()),
        }), 400

    user_id = session["user_id"]
    passport = mark_heritage_passport_discovery(user_id, language)
    if passport and passport.get("newly_discovered"):
        set_explorer_milestone(user_id, "beacon_discovery")
    record_activity_day(user_id)
    new_achievements = evaluate_achievements(user_id)
    payload = {"success": True, **passport, "new_achievements": new_achievements}
    return jsonify(payload)


def _achievement_hook(user_id, milestone_key=None):
    """Record optional milestone, activity day, then evaluate unlocks."""
    if milestone_key:
        set_explorer_milestone(user_id, milestone_key)
    record_activity_day(user_id)
    return evaluate_achievements(user_id)


@app.route("/achievements")
def achievements_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    gallery = get_achievements_gallery(user_id)
    stats = collect_user_stats(user_id)
    points = int(stats.get("points") or 0)
    total = int(gallery.get("total") or 0)
    earned = int(gallery.get("earned") or 0)
    collection = {
        "earned": earned,
        "total": total,
        "percent": int(round((100 * earned / total))) if total else 0,
        "streak": int(stats.get("streak") or 0),
        "points": points,
        "level": max(1, 1 + (points // 300)),
    }
    return render_template(
        "achievements.html",
        gallery=gallery,
        collection=collection,
        username=session.get("username"),
    )


@app.route("/settings")
def settings_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    prefs = get_mascot_preferences(session["user_id"])
    return render_template(
        "settings.html",
        mascot_prefs=prefs,
        username=session.get("username"),
    )


@app.route("/api/achievements")
def api_achievements_list():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_achievements_gallery(session["user_id"]))


@app.route("/api/achievements/pending")
def api_achievements_pending():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    pending = pop_pending_achievement_notifications(session["user_id"])
    return jsonify({"pending": pending})


@app.route("/api/achievements/ack", methods=["POST"])
def api_achievements_ack():
    """Mark achievement notifications as shown (prevents duplicate plaques)."""
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    keys = data.get("keys") or []
    if not isinstance(keys, list):
        return jsonify({"error": "invalid_request"}), 400
    mark_achievements_notified(session["user_id"], [str(k) for k in keys])
    return jsonify({"success": True})


@app.route("/api/achievements/evaluate", methods=["POST"])
def api_achievements_evaluate():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    milestone = (data.get("milestone") or "").strip() or None
    allowed = {
        None,
        "first_login",
        "world_explorer_visit",
        "malaysia_arrived",
        "beacon_discovery",
    }
    if milestone not in allowed:
        return jsonify({"error": "invalid_milestone"}), 400
    newly = _achievement_hook(session["user_id"], milestone)
    return jsonify({"success": True, "new_achievements": newly})


@app.route("/api/mascot/preferences", methods=["GET", "POST"])
def api_mascot_preferences():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if request.method == "GET":
        return jsonify(get_mascot_preferences(session["user_id"]))
    data = request.get_json(silent=True) or {}
    prefs = update_mascot_preferences(session["user_id"], data)
    return jsonify({"success": True, "preferences": prefs})


@app.route("/api/mascot/fact")
def api_mascot_fact():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    prefs = get_mascot_preferences(session["user_id"])
    if not prefs.get("enabled") or not prefs.get("facts_enabled"):
        return jsonify({"ok": False, "reason": "disabled"})
    lang = (request.args.get("lang") or "").strip() or None
    seed = f"{session['user_id']}:{int(time.time()) // 3600}:{lang or 'any'}"
    fact = pick_heritage_fact(seed=seed, language=lang)
    return jsonify({"ok": True, "fact": fact})


@app.route("/favorites")
def favorites_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    lang_keys = get_language_keys() or list(LANGUAGES.keys())
    language_options = [
        {"lang_key": key, "display_name": LANGUAGES.get(key, {}).get("display_name") or display_name(key)}
        for key in lang_keys
    ]
    return render_template("favorites.html", language_options=language_options)


@app.route("/api/favorites")
def api_favorites_list():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    raw_lang = (request.args.get("language") or "").strip()
    language = None
    if raw_lang:
        language = resolve_language(raw_lang) or (raw_lang if raw_lang in get_language_keys() else None)
        if not language:
            return jsonify({
                "error": "unknown_language",
                "message": f"'{raw_lang}' is not a language in this course database.",
                "available_languages": list(get_language_keys()),
            }), 400

    rows = list_saved_words(session["user_id"], language)
    for row in rows:
        # vocabulary.language + saved_words.lang_key both exist after JOIN;
        # normalize to a single client-facing lang_key so favorites JS never
        # depends on which column SQLite returned first.
        row["lang_key"] = row.get("saved_lang_key") or row.get("language") or ""
        row["language_display"] = display_name(row["lang_key"])
        row["is_saved"] = True
    return jsonify({"rows": rows, "total": len(rows)})


@app.route("/api/favorites/toggle", methods=["POST"])
def api_favorites_toggle():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    vocabulary_id = data.get("vocabulary_id")
    raw_lang = (data.get("language") or "").strip()

    if not isinstance(vocabulary_id, int):
        return jsonify({
            "error": "invalid_request",
            "message": "vocabulary_id must be an integer.",
        }), 400

    language = resolve_language(raw_lang) or (raw_lang if raw_lang in get_language_keys() else None)
    if not language:
        return jsonify({
            "error": "unknown_language",
            "message": f"'{raw_lang}' is not a language in this course database.",
            "available_languages": list(get_language_keys()),
        }), 400

    # Re-verify the word actually belongs to this language before saving —
    # never let a client save an id/language pair that doesn't exist.
    try:
        word_row = dictionary_word_by_id(language, vocabulary_id)
    except RetrievalError:
        return jsonify({
            "error": "retrieval_error",
            "message": "Could not verify this word right now.",
        }), 400

    if not word_row:
        return jsonify({
            "error": "not_found",
            "message": "No word with this id exists for this language.",
        }), 404

    user_id = session["user_id"]
    already_saved = bool(get_saved_word_ids(user_id, [vocabulary_id]))
    if already_saved:
        remove_saved_word(user_id, vocabulary_id)
        return jsonify({"success": True, "saved": False})

    add_saved_word(user_id, vocabulary_id, language)
    record_activity_day(user_id)
    newly = evaluate_achievements(user_id)
    return jsonify({"success": True, "saved": True, "new_achievements": newly})


# ================= STANDALONE QUIZ (non-AI, database-backed) =================
#
# This is a self-contained multi-question quiz product, deliberately
# independent of the AI Tutor chat widget and of composer.py/GPT. It only
# ever reads from the `quiz` table (via retrieval.get_quiz_questions) and
# writes deterministic results to `user_progress` (via learning_memory).
# It works identically whether or not an OpenAI API key is configured.

_QUIZ_COUNT_OPTIONS = [5, 10]
_QUIZ_DIFFICULTY_OPTIONS = [
    ("", "Adaptive (recommended)"),
    ("easy", "Easy"),
    ("medium", "Medium"),
    ("hard", "Hard"),
]


@app.route("/quiz")
def quiz_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    lang_keys = get_language_keys() or list(LANGUAGES.keys())

    languages = []
    for key in lang_keys:
        levels = get_levels(user_id, key)
        languages.append({
            "lang_key": key,
            "display_name": LANGUAGES.get(key, {}).get("display_name") or display_name(key),
            "levels": [
                {"number": lvl["number"], "title": lvl["title"], "unlocked": lvl["unlocked"]}
                for lvl in levels
            ],
        })

    return render_template(
        "quiz.html",
        languages=languages,
        count_options=_QUIZ_COUNT_OPTIONS,
        difficulty_options=_QUIZ_DIFFICULTY_OPTIONS,
    )


def _quiz_level_is_unlocked(user_id, lang_key, level_num):
    levels = get_levels(user_id, lang_key)
    match = next((lvl for lvl in levels if lvl["number"] == level_num), None)
    return bool(match and match["unlocked"])


@app.route("/api/quiz/start", methods=["POST"])
def api_quiz_start():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    mode = (data.get("mode") or "").strip().lower()
    user_id = session["user_id"]

    if mode == "daily":
        unlocked = {}
        for key in get_language_keys() or list(LANGUAGES.keys()):
            unlocked[key] = [
                lvl["number"]
                for lvl in get_levels(user_id, key)
                if lvl.get("unlocked")
            ]
        result = start_daily_quiz_session(
            user_id=user_id,
            unlocked_levels=unlocked,
            count=5,
        )
        if not result.get("ok"):
            return jsonify({
                "ok": False,
                "reason": result.get("reason", "no_questions"),
                "message": "No verified quiz questions are available for today's challenge yet.",
            }), 200
        if result.get("lang_key"):
            result["language_display"] = display_name(result["lang_key"])
        return jsonify(result)

    raw_lang = (data.get("lang_key") or "").strip()
    language = resolve_language(raw_lang) or (raw_lang if raw_lang in get_language_keys() else None)
    if not language:
        return jsonify({
            "error": "unknown_language",
            "message": f"'{raw_lang}' is not a language in this course database.",
            "available_languages": list(get_language_keys()),
        }), 400

    try:
        level_num = int(data.get("level_num"))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_request", "message": "level_num is required."}), 400

    if level_num not in LEVEL_TITLES:
        return jsonify({"error": "invalid_request", "message": "Unknown level."}), 400

    if not _quiz_level_is_unlocked(user_id, language, level_num):
        return jsonify({"error": "locked", "message": "Complete the previous level to unlock this quiz."}), 403

    difficulty = (data.get("difficulty") or "").strip() or None
    try:
        count = int(data.get("count") or 5)
    except (TypeError, ValueError):
        count = 5

    result = start_quiz_session(
        lang_key=language,
        level_num=level_num,
        user_id=user_id,
        count=count,
        difficulty=difficulty,
    )
    if not result.get("ok"):
        return jsonify({
            "ok": False,
            "reason": result.get("reason", "no_questions"),
            "message": "This lesson does not have verified quiz questions in the course database yet.",
        }), 200

    result["language_display"] = display_name(language)
    return jsonify(result)


@app.route("/api/quiz/daily/status")
def api_quiz_daily_status():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    result = daily_quiz_status(session["user_id"])
    if result.get("lang_key"):
        result["language_display"] = display_name(result["lang_key"])
    return jsonify(result)


@app.route("/api/quiz/state")
def api_quiz_state():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    result = quiz_session_state()
    if result.get("ok") and result.get("lang_key"):
        result["language_display"] = display_name(result["lang_key"])
    return jsonify(result)


@app.route("/api/quiz/answer", methods=["POST"])
def api_quiz_answer():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    answer_index = data.get("answer_index")
    if not isinstance(answer_index, int):
        return jsonify({"error": "invalid_request", "message": "answer_index must be an integer."}), 400

    result = submit_quiz_session_answer(answer_index, user_id=session["user_id"])
    if not result.get("ok"):
        return jsonify(result), 409
    record_activity_day(session["user_id"])
    result["new_achievements"] = evaluate_achievements(session["user_id"])
    return jsonify(result)


@app.route("/api/quiz/results")
def api_quiz_results():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    result = quiz_session_results()
    if not result.get("ok"):
        return jsonify(result), 404
    if result.get("lang_key"):
        result["language_display"] = display_name(result["lang_key"])
    return jsonify(result)


@app.route("/api/quiz/restart", methods=["POST"])
def api_quiz_restart():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    result = restart_quiz_session(user_id=session["user_id"])
    if not result.get("ok"):
        return jsonify(result), 404
    result["language_display"] = display_name(result["lang_key"]) if result.get("lang_key") else None
    return jsonify(result)


@app.route("/api/quiz/end", methods=["POST"])
def api_quiz_end():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    clear_quiz_session()
    return jsonify({"ok": True})


# ================= AI TUTOR CHAT API =================

@app.route("/api/tutor/chat", methods=["POST"])
def tutor_chat():

    if "user_id" not in session:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "")

    if not isinstance(user_message, str):
        user_message = ""

    lang_key = data.get("lang_key")

    if not isinstance(lang_key, str) or not lang_key.strip():
        lang_key = None

    level_num_raw = data.get("level_num")

    mode = data.get("mode")

    if not isinstance(mode, str):
        mode = None

    level_num = None

    if isinstance(level_num_raw, int):
        level_num = level_num_raw

    elif isinstance(level_num_raw, str):
        stripped_level_num = level_num_raw.strip()

        if stripped_level_num.isdigit():
            level_num = int(stripped_level_num)

    history = sanitize_tutor_history(data.get("history"))
    quiz_continue = bool(data.get("quiz_continue"))

    debug_on = is_debug_enabled(request)

    # Defense in depth: no matter what goes wrong below, the user must
    # always receive a friendly reply instead of a raw 500 with no body.
    audit = None
    no_evidence = None
    status = "ok"
    debug_trace = None
    try:
        result = answer_tutor_query(
            lang_key=lang_key,
            level_num=level_num,
            user_message=user_message,
            mode=mode,
            history=history,
            user_id=session.get("user_id"),
            debug=debug_on,
            quiz_continue=quiz_continue,
        )
        reply = result.get("reply") or ""
        audit = result.get("audit")
        no_evidence = result.get("no_evidence")
        status = result.get("status") or "ok"
        debug_trace = result.get("debug_trace")
        quiz_card = result.get("quiz")
        quiz_result = result.get("quiz_result")

    except Exception:
        reply = (
            "Something went wrong on my end. Please try again, or use "
            "Explain, Example, Quiz, or Culture."
        )
        status = "error"
        quiz_card = None
        quiz_result = None

    if not reply and not quiz_card:
        reply = (
            "I could not generate a response just now. Please try again."
        )

    payload = {
        "success": True,
        "reply": reply,
        "mode": "live",
        "language": lang_key,
        "level": level_num,
        "status": status,
        "retrieval": audit,
    }
    if no_evidence:
        payload["no_evidence"] = no_evidence
    if quiz_card:
        payload["quiz"] = quiz_card
    if quiz_result:
        payload["quiz_result"] = quiz_result

    # Developer-only debug envelope — does not alter the normal reply pipeline.
    if debug_on:
        payload["answer"] = reply
        if debug_trace:
            payload["debug"] = debug_trace
        else:
            payload["debug"] = {
                "planner": {},
                "retrieval": [],
                "validator": {},
                "composer": {},
                "warnings": ["debug_trace_unavailable"],
            }

    return jsonify(payload)


# ================= AI TUTOR DEBUG APIs (developer-only) =================

@app.route("/api/tutor/debug/database", methods=["GET"])
def tutor_debug_database():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if not is_debug_enabled(request):
        return jsonify({
            "error": "Debug mode disabled. Set DEBUG_TUTOR=true on the server (and stay logged in)."
        }), 403
    return jsonify(database_diagnostics())


@app.route("/api/tutor/debug/duplicates", methods=["GET"])
def tutor_debug_duplicates():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if not is_debug_enabled(request):
        return jsonify({
            "error": "Debug mode disabled. Set DEBUG_TUTOR=true on the server (and stay logged in)."
        }), 403
    return jsonify(find_duplicates())


@app.route("/api/tutor/debug/selfcheck", methods=["GET"])
def tutor_debug_selfcheck():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if not is_debug_enabled(request):
        return jsonify({
            "error": "Debug mode disabled. Set DEBUG_TUTOR=true on the server (and stay logged in)."
        }), 403

    def _answer(message, lang_key=None):
        return answer_tutor_query(
            lang_key=lang_key,
            level_num=None,
            user_message=message,
            mode=None,
            history=None,
            user_id=session.get("user_id"),
            debug=True,
        )

    return jsonify(run_selfcheck(_answer))


# ================= LANGUAGE EXPLORE PAGE =================

@app.route("/language/<lang_key>")
def language_page(lang_key):

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    language = LANGUAGES.get(
        lang_key
    )

    if not language:
        abort(404)

    learning_summary = (
        get_language_learning_summary(
            session["user_id"],
            lang_key
        )
    )

    completed_levels = {
        level["number"]
        for level in learning_summary["levels"]
        if level["completed"]
    }

    language_unlock_data = (
        EXPLORE_UNLOCKS.get(
            lang_key,
            {}
        )
    )

    explore_unlocks = []

    for level_num in sorted(
        completed_levels
    ):

        unlock = (
            language_unlock_data.get(
                level_num
            )
        )

        if unlock:

            explore_unlocks.append({
                "level_num": level_num,
                **unlock
            })

    return render_template(
        "language.html",
        language=language,
        lang_key=lang_key,
        learning_summary=learning_summary,
        levels_info=learning_summary["levels"],
        explore_unlocks=explore_unlocks,
        family_tree=get_language_family_tree(lang_key)
    )


# ================= LANGUAGE LEARNING PATH =================

# ================= LANGUAGE LEARNING PATH =================

@app.route("/language/<lang_key>/learn")
def learn_page(lang_key):

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    language = LANGUAGES.get(
        lang_key
    )

    if not language:
        abort(404)

    levels_info = get_levels(
        session["user_id"],
        lang_key
    )

    return render_template(
        "learn.html",
        language=language,
        levels_info=levels_info,
        lang_key=lang_key
    )


# ================= LEVEL PAGE =================

@app.route(
    "/level/<lang_key>/<int:level_num>"
)
def level_page(lang_key, level_num):

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    language = LANGUAGES.get(
        lang_key
    )

    if not language:
        abort(404)

    if level_num not in LEVEL_TITLES:
        abort(404)

    course = COURSE_DATA.get(
        lang_key,
        {}
    ).get(
        level_num
    )

    if not course:
        abort(404)

    levels_info = get_levels(
        session["user_id"],
        lang_key
    )

    requested_level = next(
        (
            level
            for level in levels_info
            if level["number"] == level_num
        ),
        None
    )

    if not requested_level:
        abort(404)

    if not requested_level["unlocked"]:

        flash(
            "Complete the previous level to unlock this level."
        )

        return redirect(
            url_for(
                "learn_page",
                lang_key=lang_key
            )
        )

    total_steps = len(
        course["steps"]
    )

    replay_mode = str(
        request.args.get("replay", "")
    ).lower() in ("1", "true", "yes")

    level_completed = bool(
        requested_level["completed"]
    )

    saved_step = get_saved_step(
        session["user_id"],
        lang_key,
        level_num
    )

    saved_step = min(
        saved_step,
        total_steps
    )

    # Completed = still openable. Review lands on the completion screen;
    # Replay starts from step 0 without clearing historical completion.
    if level_completed and replay_mode:
        saved_step = 0
    elif level_completed:
        saved_step = total_steps

    return render_template(
        "level.html",
        language=language,
        lang_key=lang_key,
        level_num=level_num,
        level_title=LEVEL_TITLES[
            level_num
        ],
        course_steps=course["steps"],
        saved_step=saved_step,
        level_completed=level_completed,
        replay_mode=replay_mode,
    )


# ================= SAVE STEP PROGRESS =================

@app.route(
    "/save-step/<lang_key>/<int:level_num>",
    methods=["POST"]
)
def save_step(lang_key, level_num):

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Login required"
        }), 401

    course = COURSE_DATA.get(
        lang_key,
        {}
    ).get(
        level_num
    )

    if not course:
        return jsonify({
            "success": False,
            "message": "Course not found"
        }), 404

    # A user must not be able to write step progress for a level they have
    # not unlocked yet (e.g. by POSTing directly to this endpoint) — mirror
    # the same guard used by level_page/complete_level.
    levels_info = get_levels(
        session["user_id"],
        lang_key
    )

    requested_level = next(
        (
            level
            for level in levels_info
            if level["number"] == level_num
        ),
        None
    )

    if not requested_level or not requested_level["unlocked"]:
        return jsonify({
            "success": False,
            "message": "Level is locked"
        }), 403

    data = request.get_json(
        silent=True
    ) or {}

    current_step = data.get(
        "currentStep"
    )

    if not isinstance(
        current_step,
        int
    ):
        return jsonify({
            "success": False,
            "message": "Invalid step"
        }), 400

    total_steps = len(
        course["steps"]
    )

    current_step = max(
        0,
        min(
            current_step,
            total_steps
        )
    )

    conn = get_db()

    conn.execute(
        """
        INSERT INTO lesson_progress (
            user_id,
            lang_key,
            level_num,
            current_step
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(
            user_id,
            lang_key,
            level_num
        )
        DO UPDATE SET
            current_step = excluded.current_step
        """,
        (
            session["user_id"],
            lang_key,
            level_num,
            current_step
        )
    )

    
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "currentStep": current_step
    })


# ================= COMPLETE LEVEL =================

@app.route(
    "/complete-level/<lang_key>/<int:level_num>",
    methods=["POST"]
)
def complete_level(lang_key, level_num):

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Login required"
        }), 401

    if lang_key not in LANGUAGES:
        return jsonify({
            "success": False,
            "message": "Language not found"
        }), 404

    course = COURSE_DATA.get(
        lang_key,
        {}
    ).get(
        level_num
    )

    if not course:
        return jsonify({
            "success": False,
            "message": "Level not found"
        }), 404

    levels_info = get_levels(
        session["user_id"],
        lang_key
    )

    requested_level = next(
        (
            level
            for level in levels_info
            if level["number"] == level_num
        ),
        None
    )

    if not requested_level:
        return jsonify({
            "success": False,
            "message": "Level not found"
        }), 404

    if not requested_level["unlocked"]:
        return jsonify({
            "success": False,
            "message": "Level is locked"
        }), 403

    total_steps = len(
        course["steps"]
    )

    # Require the learner to have actually advanced through the lesson
    # steps before marking the level complete (prevents a bare POST from
    # unlocking the next level without studying). Idempotent re-complete
    # of an already-completed level is still allowed.
    if total_steps > 0 and not requested_level["completed"]:
        saved_step = get_saved_step(
            session["user_id"],
            lang_key,
            level_num
        )
        if saved_step < total_steps:
            return jsonify({
                "success": False,
                "message": "Finish the lesson steps before marking this level complete."
            }), 400

    conn = get_db()

    conn.execute(
        """
        INSERT INTO progress (
            user_id,
            lang_key,
            level_num,
            completed
        )
        VALUES (?, ?, ?, 1)

        ON CONFLICT(
            user_id,
            lang_key,
            level_num
        )
        DO UPDATE SET
            completed = 1
        """,
        (
            session["user_id"],
            lang_key,
            level_num
        )
    )

    conn.execute(
        """
        INSERT INTO lesson_progress (
            user_id,
            lang_key,
            level_num,
            current_step
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(
            user_id,
            lang_key,
            level_num
        )
        DO UPDATE SET
            current_step = excluded.current_step
        """,
        (
            session["user_id"],
            lang_key,
            level_num,
            total_steps
        )
    )

    conn.commit()
    conn.close()

    record_activity_day(session["user_id"])
    newly = evaluate_achievements(session["user_id"])
    return jsonify({
        "success": True,
        "message": "Progress saved",
        "new_achievements": newly,
    })

# ================= PERSONAL PROFILE =================

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    user = conn.execute(
        """
        SELECT
            id,
            username,
            email,
            provider
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    if not user:

        session.clear()

        return redirect(
            url_for("login")
        )

    language_progress = {}

    completed_levels = 0
    total_levels = 0
    active_languages = 0

    for lang_key, language in LANGUAGES.items():

        levels = get_levels(
            user_id,
            lang_key
        )

        completed_count = sum(
            1
            for level in levels
            if level["completed"]
        )

        language_total = len(levels)

        percentage = 0

        if language_total > 0:

            percentage = round(
                (
                    completed_count
                    / language_total
                )
                * 100
            )

        has_progress = any(
            level["completed"]
            or level["current_step"] > 0
            for level in levels
        )

        if has_progress:
            active_languages += 1

        completed_levels += completed_count
        total_levels += language_total

        language_progress[lang_key] = {

            "display_name":
                language["display_name"],

            "region":
                language.get(
                    "region",
                    "Malaysia"
                ),

            "completed":
                completed_count,

            "total":
                language_total,

            "percentage":
                percentage
        }

    overall_percentage = 0

    if total_levels > 0:

        overall_percentage = max(
            0,
            min(
                100,
                round(
                    (
                        completed_levels
                        / total_levels
                    )
                    * 100
                ),
            ),
        )

    # Quiz mastery is intentionally separate from course-level completion.
    mastery_summary = get_user_mastery_summary(user_id)
    quiz_history = get_quiz_history(user_id, limit=8)
    for entry in quiz_history:
        entry["language_display"] = display_name(entry.get("lang_key"))
        entry["level_title"] = LEVEL_TITLES.get(entry.get("level_num"), f"Level {entry.get('level_num')}")

    saved_count = len(list_saved_words(user_id))

    return render_template(
        "profile.html",

        user=user,

        language_progress=
            language_progress,

        completed_levels=
            completed_levels,

        total_levels=
            total_levels,

        active_languages=
            active_languages,

        overall_percentage=
            overall_percentage,

        mastery_summary=mastery_summary,

        quiz_history=quiz_history,

        saved_words_count=saved_count,
    )

# ================= ABOUT THE PROJECT =================

@app.route("/about")
def about_project():

    return render_template(
        "about.html"
    )

# ================ SAFETY & SOURCES ================

@app.route("/safety")
def safety():

    return render_template(
        "safety.html"
    )

# ================= CORRECTION PAGE =================

@app.route(
    "/language/<lang_key>/suggest-correction"
)
def suggest_correction(lang_key):

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    language = LANGUAGES.get(
        lang_key
    )

    if not language:
        abort(404)

    return render_template(
        "correction.html",
        language=language,
        lang_key=lang_key
    )


# ================= SOURCES PAGE =================

@app.route(
    "/language/<lang_key>/sources"
)
def language_sources(lang_key):

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    language = LANGUAGES.get(
        lang_key
    )

    if not language:
        abort(404)

    return render_template(
        "sources.html",
        language=language,
        lang_key=lang_key
    )


# ================= SECURITY HEADERS / HTTPS =================

@app.before_request
def _enforce_https_when_configured():
    """Optional HTTP→HTTPS redirect for reverse-proxy production deploys.

    Enabled only when FORCE_HTTPS=true. Relies on ProxyFix (TRUST_PROXY)
    so the check uses the original client scheme and does not loop.
    Skipped for local-looking hosts even if misconfigured.
    """
    if not _FORCE_HTTPS:
        return None
    host = (request.host or "").split(":")[0].lower()
    if host in {"127.0.0.1", "localhost", "::1"}:
        return None
    if request.is_secure:
        return None
    url = request.url
    if url.startswith("http://"):
        return redirect("https://" + url[len("http://"):], code=301)
    return None


@app.after_request
def add_security_headers(response):

    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    response.headers[
        "X-Frame-Options"
    ] = "SAMEORIGIN"

    response.headers[
        "Referrer-Policy"
    ] = "strict-origin-when-cross-origin"

    response.headers[
        "Permissions-Policy"
    ] = (
        "camera=(), microphone=(), geolocation=()"
    )

    # CSP tuned for existing dashboard globe (Three.js CDN + inline boot
    # scripts), YouTube iframe API, marked/DOMPurify, and SVG <object> map.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'self'; "
        "frame-ancestors 'self'; "
        "form-action 'self'; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
        "https://cdnjs.cloudflare.com https://www.youtube.com https://www.youtube-nocookie.com; "
        "connect-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
        "https://www.youtube.com; "
        "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com; "
        "worker-src 'self' blob:; "
        "media-src 'self' blob:;"
    )

    # HSTS only when the request is already HTTPS (or FORCE_HTTPS is on and
    # the connection is secure via proxy). Never set on plain local HTTP.
    if request.is_secure and (_FORCE_HTTPS or _FLASK_ENV == "production"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


# ================= LOGOUT =================

@app.route("/logout", methods=["GET", "POST"])
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ================= ERROR PAGES =================
# Friendly, on-brand error pages instead of raw tracebacks/blank responses.
# JSON API requests (paths under /api/) keep returning JSON so existing
# fetch()-based error handling in the frontend is unaffected.

@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "not_found", "message": "This endpoint does not exist."}), 404
    return render_template(
        "error.html",
        status_code=404,
        heading="Page not found",
        message="The page you're looking for doesn't exist or may have moved.",
    ), 404


@app.errorhandler(403)
def handle_forbidden(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "forbidden", "message": "You don't have access to this."}), 403
    return render_template(
        "error.html",
        status_code=403,
        heading="Access denied",
        message="You don't have permission to view this page.",
    ), 403


@app.errorhandler(500)
def handle_server_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "server_error", "message": "Something went wrong on our end."}), 500
    return render_template(
        "error.html",
        status_code=500,
        heading="Something went wrong",
        message="An unexpected error occurred. Please try again in a moment.",
    ), 500


# ================= START =================

if __name__ == "__main__":

    init_db()
    seed_tutor_content(COURSE_DATA, LANGUAGES, EXPLORE_UNLOCKS)
    sync_missing_vocabulary_from_course(COURSE_DATA)
    import_verified_vocabulary_packs()

    refresh_composer_enabled()
    # Status/health already printed on import for flask run; print again for python app.py
    os.environ.pop("_MMLE_COMPOSER_STARTUP_DONE", None)
    _report_composer_on_startup()

    debug_mode = (
        os.getenv(
            "FLASK_DEBUG",
            "false"
        ).lower()
        == "true"
    )

    # Never expose the interactive debugger on a production-labelled deploy.
    if _FLASK_ENV == "production":
        debug_mode = False

    app.run(
        debug=debug_mode,
        threaded=True,
        # Bind loopback by default; production should use a reverse proxy + WSGI.
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
    )
