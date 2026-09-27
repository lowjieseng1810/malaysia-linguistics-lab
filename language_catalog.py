"""Canonical language keys, map geography, and family strings.

Coordinates are community/region approximations from published sources
(ASJP CLLD, ELAR/SIL survey districts, well-known settlements). They are
not claimed as household GPS points.
"""

from __future__ import annotations

CORE_LANGUAGES = ("iban", "kadazan-dusun", "bidayuh", "mah-meri")
EXTENDED_LANGUAGES = ("bookan", "chewong", "kristang", "baba-malay", "temoq")
COURSE_LANGUAGES = CORE_LANGUAGES + EXTENDED_LANGUAGES

LANGUAGE_FAMILY = {
    "iban": "Austronesian (Malayo-Polynesian, Malayic)",
    "kadazan-dusun": "Austronesian (Malayo-Polynesian, Dusunic)",
    "bidayuh": "Austronesian (Malayo-Polynesian, Land Dayak)",
    "mah-meri": "Austroasiatic (Aslian, Southern Aslian)",
    "bookan": "Austronesian (Malayo-Polynesian, Murutic)",
    "chewong": "Austroasiatic (Aslian, Northern Aslian)",
    "kristang": "Portuguese-based creole (Malacca Creole Portuguese)",
    "baba-malay": "Malay-based contact language (Peranakan / Baba Malay)",
    "temoq": "Austroasiatic (Aslian, Southern Aslian)",
}

# lat/lon used for map + Language Universe markers.
MAP_COORDS = {
    "iban": {"lat": 2.3, "lon": 113.0, "state": "Sarawak", "frame": "sarawak"},
    "kadazan-dusun": {"lat": 5.9, "lon": 116.2, "state": "Sabah", "frame": "sabah"},
    "bidayuh": {"lat": 1.35, "lon": 110.35, "state": "Sarawak", "frame": "sarawak"},
    "mah-meri": {"lat": 2.86, "lon": 101.35, "state": "Selangor", "frame": "peninsula"},
    # Keningau district (Bookan survey area: Keningau, Sook, Tulid, Lanas).
    "bookan": {"lat": 5.34, "lon": 116.16, "state": "Sabah", "frame": "sabah"},
    # ASJP Ceq Wong: 3.23 N, 102.42 E (Krau / central Pahang).
    "chewong": {"lat": 3.23, "lon": 102.42, "state": "Pahang", "frame": "peninsula"},
    # ASJP Papia Kristang: 2.20 N, 102.27 E (Melaka Portuguese Settlement).
    "kristang": {"lat": 2.20, "lon": 102.27, "state": "Melaka", "frame": "peninsula"},
    # Melaka Peranakan quarter (distinct from Portuguese Settlement).
    "baba-malay": {"lat": 2.195, "lon": 102.249, "state": "Melaka", "frame": "peninsula"},
    # ASJP Temoq: 4.00 N, 102.50 E (Pahang).
    "temoq": {"lat": 4.00, "lon": 102.50, "state": "Pahang", "frame": "peninsula"},
}

DISPLAY_NAMES = {
    "iban": "Iban",
    "kadazan-dusun": "Kadazan-Dusun",
    "bidayuh": "Bidayuh",
    "mah-meri": "Mah Meri",
    "bookan": "Bookan",
    "chewong": "Chewong",
    "kristang": "Kristang",
    "baba-malay": "Baba Malay",
    "temoq": "Temoq",
}

# Extra tutor/dictionary aliases (never treated as invented language names).
LANGUAGE_ALIASES = {
    "bookan": ["murut bookan", "baukan murut", "bookan murut", "bnb"],
    "chewong": ["che wong", "cheq wong", "ceq wong", "siwang", "cwg"],
    "kristang": [
        "papia kristang",
        "papia cristang",
        "malacca portuguese creole",
        "malacca creole portuguese",
        "kristang creole",
        "mcm",
    ],
    "baba-malay": ["baba malay", "peranakan", "straits malay", "mbf"],
    "temoq": ["temo'", "temo", "tmo"],
}
