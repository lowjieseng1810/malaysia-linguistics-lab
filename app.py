from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    flash,
    url_for,
    jsonify
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address



import hashlib
import json
import os
import secrets
import sqlite3
import time



# ================= ENVIRONMENT =================

load_dotenv()


# ================= APP =================

app = Flask(__name__)


secret_key = os.getenv("SECRET_KEY")

if not secret_key:
    raise RuntimeError(
        "SECRET_KEY is missing. "
        "Add it to your .env file."
    )


app.config["SECRET_KEY"] = secret_key


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


# Keep this False for local HTTP development.
# It becomes True only in production.

app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv(
        "FLASK_ENV",
        "development"
    ).lower()
    == "production"
)


# ================= DATABASE =================

DATABASE = "users.db"


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


# ================= DATABASE FUNCTIONS =================

def get_db():

    conn = sqlite3.connect(
        DATABASE
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = sqlite3.connect(
        DATABASE
    )


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


    user_columns = {

        row[1]

        for row in conn.execute(
            "PRAGMA table_info(users)"
        ).fetchall()

    }


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

    "kadazan": {},

    "bidayuh": {}

}

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

            session["user_id"] = (
                user["id"]
            )

            session["username"] = (
                user["username"]
            )

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


    session.clear()

    session["user_id"] = user_id

    session["username"] = username


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

        percentage = round(
            (
                completed_count /
                total_levels
            ) * 100
        )

        language_progress[
            lang_key
        ] = {
            "completed": completed_count,
            "total": total_levels,
            "percentage": percentage
        }

    return render_template(
        "dashboard.html",
        username=session["username"],
        language_progress=language_progress
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
        return (
            "Language not found",
            404
        )

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
        return (
            "Language not found",
            404
        )

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
        return (
            "Language not found",
            404
        )

    if level_num not in LEVEL_TITLES:
        return (
            "Level not found",
            404
        )

    course = COURSE_DATA.get(
        lang_key,
        {}
    ).get(
        level_num
    )

    if not course:
        return (
            "Course content not found",
            404
        )

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
        return (
            "Level not found",
            404
        )

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

    saved_step = get_saved_step(
        session["user_id"],
        lang_key,
        level_num
    )

    total_steps = len(
        course["steps"]
    )

    saved_step = min(
        saved_step,
        total_steps
    )

    return render_template(
        "level.html",
        language=language,
        lang_key=lang_key,
        level_num=level_num,
        level_title=LEVEL_TITLES[
            level_num
        ],
        course_steps=course["steps"],
        saved_step=saved_step
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

    return jsonify({
        "success": True,
        "message": "Progress saved"
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

        overall_percentage = round(
            (
                completed_levels
                / total_levels
            )
            * 100
        )

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
            overall_percentage
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
        return (
            "Language not found",
            404
        )

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
        return (
            "Language not found",
            404
        )

    return render_template(
        "sources.html",
        language=language,
        lang_key=lang_key
    )


# ================= SECURITY HEADERS =================

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

    return response


# ================= LOGOUT =================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ================= START =================

if __name__ == "__main__":

    init_db()

    debug_mode = (
        os.getenv(
            "FLASK_DEBUG",
            "false"
        ).lower()
        == "true"
    )

    app.run(
        debug=debug_mode
    )
