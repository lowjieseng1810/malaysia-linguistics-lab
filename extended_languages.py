"""Metadata, media, and course merge for five additional languages."""

from __future__ import annotations

from course_from_dataset import all_extended_course_data
from language_catalog import DISPLAY_NAMES, LANGUAGE_FAMILY as EXTENDED_FAMILY, MAP_COORDS

EXTENDED_LANGUAGE_PROFILES = {
    "bookan": {
        "display_name": "Bookan",
        "aliases": ["Murut Bookan", "Baukan Murut", "Bookan Murut"],
        "blurb": "A Murutic language of interior Sabah with active digital documentation and a published vitality survey.",
        "region": "Keningau District, Sabah, Malaysia",
        "community": "Murut Bookan communities",
        "eyebrow": "Language of interior Sabah",
        "about_title": "The least-documented Murut language in public archives",
        "about": (
            "Bookan, also listed as Baukan Murut, is an Austronesian Murutic language "
            "of Sabah (ISO 639-3 bnb). Public documentation projects describe it as "
            "among the least documented Murut varieties and are building audio-visual "
            "records rather than a large public learner lexicon."
        ),
        "speakers_title": "Murut Bookan community",
        "speakers": (
            "ELAR collection notes locate speakers mainly in interior Sabah, including "
            "Keningau, Sook, Tulid, and Lanas. Reported speaker figures on those pages "
            "are on the order of 2,400 or fewer — a documentation estimate, not a census."
        ),
        "location_title": "Southwestern interior Sabah",
        "location": (
            "A 2017 SIL survey situates Bookan in Keningau District in southwestern Sabah. "
            "The map marker uses that district centre, not a household coordinate."
        ),
        "preservation_title": "Digital documentation while the language is shifting",
        "preservation": (
            "Kluge and Choi (2017) classify Bookan as EGIDS 7 Shifting, with reported "
            "shift toward Sabah Malay. An ELDP/Universiti Malaya project deposits "
            "recordings in the Endangered Languages Archive (DK0743). This course does "
            "not invent Bookan words; vocabulary stays under review until a reusable lexicon is bundled."
        ),
        "verification_status": "Under Review",
        "exclude_dictionary": True,
        "verification_note": (
            "Language facts follow published survey and archive pages. No community-verified "
            "lexicon is claimed here. Do not mark Bookan dictionary rows as community verified."
        ),
        "vitality": {
            "classification": "EGIDS 7 Shifting",
            "system": "EGIDS",
            "year": 2017,
            "source": "Kluge, A. & Choi, J.-H. 2017. Bookan Language Vitality. SIL Electronic Survey Reports 2017-008.",
            "note": "Source-specific 2017 survey finding. Ethnologue Free also describes the language as endangered / adult L1 use; those are separate statements.",
        },
        "gallery": [
            {
                "title": "Keningau District, Sabah",
                "caption": (
                    "Town view of Keningau, southwestern Sabah. Kluge & Choi (2017) "
                    "situate Bookan in this district. Place photograph — not a portrait of speakers."
                ),
                "image_url": "/static/images/bookan_keningau.jpg",
                "source_name": "CEphoto, Uwe Aranas · CC BY-SA 3.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Keningau_Sabah_TownView-fromGuangJiTemple-06.jpg",
            },
            {
                "title": "Murut Cultural Centre, Tenom",
                "caption": (
                    "Pusat Kebudayaan Murut in Tenom, Sabah. This is a public Murutic heritage site "
                    "in the same interior region; it is not a Bookan-only venue and is not a partnership claim."
                ),
                "image_url": "/static/images/bookan_murut_centre.jpg",
                "source_name": "Jjurieee · CC BY-SA 4.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Pusat_Kebudayaan_Murut_Tenom_Sabah.jpg",
            },
        ],
        "videos": [
            {
                "title": "Documentation of Murut Bookan (archive collection)",
                "creator": "Endangered Languages Archive",
                "description": (
                    "Public archive page for audio, video, and transcription deposits. "
                    "Open the original collection rather than a rehosted copy."
                ),
                "embed_url": "",
                "source_url": "https://www.elararchive.org/dk0743/",
            }
        ],
        "sources": [
            {
                "title": "Bookan Language Vitality: A Rapid Appraisal Sociolinguistic Survey",
                "organization": "SIL Electronic Survey Reports 2017-008 (Kluge & Choi)",
                "url": "https://www.sil.org/resources/publications/entry/70481",
            },
            {
                "title": "Documentation of Murut Bookan",
                "organization": "Endangered Languages Archive DK0743",
                "url": "https://www.elararchive.org/dk0743/",
            },
            {
                "title": "Murut, Bookan [bnb]",
                "organization": "Ethnologue Free profile (source-specific web summary)",
                "url": "https://www.ethnologue.com/language/bnb/",
            },
        ],
    },
    "chewong": {
        "display_name": "Chewong",
        "aliases": ["Che Wong", "Cheq Wong", "Ceq Wong", "Siwang"],
        "blurb": "A Northern Aslian language of Pahang, taught from published community and documentation facts rather than invented spellings.",
        "region": "Pahang, Peninsular Malaysia",
        "community": "Chewong / Cheq Wong communities",
        "eyebrow": "Orang Asli language of Pahang",
        "about_title": "A Northern Aslian language with a documented basic lexicon",
        "about": (
            "Chewong (also Cheq Wong) is an Austroasiatic Northern Aslian language "
            "associated with communities in Pahang. Lessons here teach community, place, "
            "and documentation context. Raw comparative transcription is not used as "
            "everyday student spelling."
        ),
        "speakers_title": "Chewong community",
        "speakers": (
            "ASJP records the list as Chewong / Ceq Wong (glottocode chew1245). "
            "Community-verified learner spelling is not claimed; forms are source spellings."
        ),
        "location_title": "Central Pahang",
        "location": (
            "The ASJP wordlist coordinates are 3.23°N, 102.42°E, in central Pahang "
            "(Krau region). The map uses those published coordinates."
        ),
        "preservation_title": "Lexicon from an open comparative wordlist",
        "preservation": (
            "Lessons teach community, place, and documentation limits rather than "
            "displaying comparative transcription as everyday spelling."
        ),
        "verification_status": "Under Review",
        "exclude_dictionary": True,
        "verification_note": (
            "Entries are verified against the ASJP Ceq Wong list, not against a community workshop. "
            "ASJP orthography is not everyday spelling."
        ),
        "vitality": {
            "classification": "Living (ASJP status field: alive)",
            "system": "ASJP status field",
            "year": None,
            "source": "ASJP Database wordlist CEQ_WONG (CLLD)",
            "note": "ASJP does not publish an EGIDS grade on this record. No EGIDS label is invented here.",
        },
        "gallery": [
            {
                "title": "Chewong (Wikimedia Commons)",
                "caption": (
                    "Photograph filed under Cheq Wong / Chewong people on Wikimedia Commons. "
                    "Used as a community-labelled public image, not as workshop verification."
                ),
                "image_url": "/static/images/chewong_community.jpg",
                "source_name": "Son K Lee · CC BY 2.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Chewong_(9005321290).jpg",
            },
            {
                "title": "Kuala Krau, Pahang",
                "caption": (
                    "Kuala Krau in the Krau region of Pahang, matching the published ASJP Ceq Wong "
                    "coordinates used for the map marker."
                ),
                "image_url": "/static/images/chewong_kuala_krau.jpg",
                "source_name": "Slleong · CC0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Kuala_Krau_2.jpg",
            },
            {
                "title": "Krau Wildlife Reserve map",
                "caption": (
                    "Published map of Krau Wildlife Reserve, Pahang — the landscape context "
                    "for Chewong / Ceq Wong documentation, not a language map of households."
                ),
                "image_url": "/static/images/chewong_krau_map.png",
                "source_name": "Mohammad Saiful Mansor · CC BY-SA 4.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Map_of_Krau_Wildlife_Reserve.png",
            },
        ],
        "videos": [],
        "sources": [
            {
                "title": "ASJP wordlist Ceq Wong",
                "organization": "ASJP / CLLD (CC BY 4.0)",
                "url": "https://asjp.clld.org/languages/CEQ_WONG",
            },
            {
                "title": "ISO 639-3 cwg",
                "organization": "SIL ISO 639-3 (Chewong / Cheq Wong)",
                "url": "https://iso639-3.sil.org/code/cwg",
            },
        ],
    },
    "kristang": {
        "display_name": "Kristang",
        "aliases": [
            "Papia Kristang",
            "Malacca Portuguese Creole",
            "Malacca Creole Portuguese",
            "Papia Cristang",
        ],
        "blurb": "The Portuguese-Eurasian creole of Melaka, with community revitalisation and a published dictionary tradition.",
        "region": "Melaka, Malaysia",
        "community": "Kristang / Portuguese-Eurasian community",
        "eyebrow": "Creole of Melaka",
        "about_title": "A Portuguese-based creole still spoken in Melaka",
        "about": (
            "Kristang (Papia Kristang, ISO 639-3 mcm) is a Portuguese-based creole "
            "associated with the Portuguese-Eurasian community of Melaka. Baxter (1988, 2004) "
            "describes it as a creole, not sixteenth-century Portuguese. Lesson forms here "
            "follow the Wikikamus Swadesh appendix compiled from Baxter's dictionary (CC BY-SA)."
        ),
        "speakers_title": "Portuguese-Eurasian / Kristang community",
        "speakers": (
            "ASJP lists about 300 speakers on the Papia Kristang record (source-specific, not a new census). "
            "Community-led classes such as Kodrah Kristang are documented publicly as revitalisation work; "
            "this app does not claim partnership with those groups."
        ),
        "location_title": "Portuguese Settlement, Melaka",
        "location": (
            "The ASJP Papia Kristang coordinates are 2.20°N, 102.27°E, matching the Melaka "
            "Portuguese Settlement area used for the map beacon."
        ),
        "preservation_title": "Dictionary, classes, and heritage revival",
        "preservation": (
            "A dictionary (Baxter & de Silva 2004) and a reference grammar (Baxter 1988) "
            "anchor the documented lexicon. Community revitalisation is widely reported; "
            "this course only teaches forms that appear in the bundled CC BY-SA Swadesh list."
        ),
        "verification_status": "Under Review",
        "verification_note": (
            "Lesson vocabulary is limited to the Wikikamus Swadesh list (CC BY-SA) compiled "
            "from Baxter & de Silva 2004. Not community-workshop verified in this project."
        ),
        "vitality": {
            "classification": "Living; small speaker community (ASJP lists 300 on that record)",
            "system": "ASJP speaker field",
            "year": None,
            "source": "ASJP Database wordlist PAPIA_KRISTANG; Baxter 1988 grammar",
            "note": "No EGIDS grade is asserted here. Speaker counts are source-specific.",
        },
        "gallery": [
            {
                "title": "Portuguese Settlement, Melaka",
                "caption": (
                    "Kampung Portugis / Portuguese Settlement, Melaka — the community area "
                    "associated with Papia Kristang in published descriptions."
                ),
                "image_url": "/static/images/kristang_settlement.jpg",
                "source_name": "Song GK · CC BY 4.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Portuguese_Settlement,_Melaka_-_01_(2026).jpg",
            },
            {
                "title": "Portuguese Settlement streetscape",
                "caption": (
                    "Street view of the Portuguese Settlement in Melaka. Heritage place, "
                    "not a claim of community partnership with this course."
                ),
                "image_url": "/static/images/kristang_settlement_square.jpg",
                "source_name": "Chongkian · CC BY-SA 4.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Portuguese_Settlement.JPG",
            },
            {
                "title": "Chapel, Portuguese Settlement",
                "caption": (
                    "Chapel in the Portuguese Settlement, Melaka (March 2023). "
                    "Portuguese-Eurasian heritage architecture in the same settlement."
                ),
                "image_url": "/static/images/kristang_chapel.jpg",
                "source_name": "Sharon Hahn Darlin · CC BY 2.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Melaka,_Malaysia_Portuguese_Settlement,_March_2023_-_Chapel.jpg",
            },
        ],
        "videos": [],
        "sources": [
            {
                "title": "Lampiran: Senarai Swadesh bahasa Kristang",
                "organization": "Wikikamus (CC BY-SA), citing Baxter 2004",
                "url": "https://ms.wiktionary.org/wiki/Lampiran:Senarai_Swadesh_bahasa_Kristang",
            },
            {
                "title": "ASJP wordlist Papia Kristang",
                "organization": "ASJP / CLLD (CC BY 4.0)",
                "url": "https://asjp.clld.org/languages/PAPIA_KRISTANG",
            },
            {
                "title": "A Grammar of Kristang (Malacca Creole Portuguese)",
                "organization": "Baxter, Alan N. 1988. Pacific Linguistics",
                "url": "https://openresearch-repository.anu.edu.au/handle/1885/145643",
            },
        ],
    },
    "baba-malay": {
        "display_name": "Baba Malay",
        "aliases": ["Peranakan", "Baba", "Straits Malay"],
        "blurb": "The Malay-based contact language of Peranakan communities, documented in Melaka and historically also in Singapore.",
        "region": "Melaka, Malaysia",
        "community": "Peranakan / Baba Nyonya communities",
        "eyebrow": "Peranakan heritage language",
        "about_title": "A Malay-based contact language of the Peranakan world",
        "about": (
            "Baba Malay (ISO 639-3 mbf) is a Malay-based contact language associated with "
            "Peranakan (Baba Nyonya) communities. Academic grammars describe Sinitic "
            "substrate influence. Learner vocabulary stays under review here because the "
            "bundled comparative list is not a community orthography."
        ),
        "speakers_title": "Peranakan communities",
        "speakers": (
            "The language is linked with Peranakan heritage in Melaka and also in Singapore. "
            "The ASJP record coordinates point to Singapore (1.28°N, 103.83°E); this map "
            "places the Melaka beacon in the historic city because this course's regional focus is Melaka."
        ),
        "location_title": "Melaka (with a historically wider Peranakan network)",
        "location": (
            "The Melaka marker is the historic city / Peranakan quarter, kept distinct from "
            "the Portuguese Settlement Kristang beacon. Variety differences between Melaka "
            "and Singapore are noted in published grammars and are not flattened here."
        ),
        "preservation_title": "Heritage, glossary work, and education",
        "preservation": (
            "Published grammars and lexicons document Baba Malay for education and research. "
            "This course does not display raw comparative transcription as ordinary dictionary words."
        ),
        "verification_status": "Under Review",
        "exclude_dictionary": True,
        "verification_note": (
            "ASJP Malay Baba forms are source-verified, not community-workshop verified. "
            "Some items overlap Malay; that overlap is historically expected, not an error."
        ),
        "vitality": {
            "classification": "Living (ASJP status field: alive); speaker figure 12,000 on that record",
            "system": "ASJP status / speaker fields",
            "year": None,
            "source": "ASJP Database wordlist MALAY_BABA",
            "note": "ASJP does not give an EGIDS grade here. Do not upgrade this to ‘endangered’ without a cited survey.",
        },
        "gallery": [
            {
                "title": "Baba Nyonya Heritage Museum, Melaka",
                "caption": (
                    "Exterior of the Baba Nyonya Heritage Museum in Melaka City — a public museum "
                    "documenting Peranakan (Baba Nyonya) domestic heritage."
                ),
                "image_url": "/static/images/baba_museum_exterior.jpg",
                "source_name": "Azuladnan · CC BY-SA 4.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Baba_and_Nyonya_House_Museum_Exterior.jpg",
            },
            {
                "title": "Museum street front, Melaka",
                "caption": (
                    "Baba Nyonya Heritage Museum façade. Used here as a Peranakan heritage landmark, "
                    "not as an official partnership."
                ),
                "image_url": "/static/images/baba_museum.jpg",
                "source_name": "Chongkian · CC BY-SA 4.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Baba_Nyonya_Heritage_Museum.JPG",
            },
            {
                "title": "Museum interior",
                "caption": (
                    "Interior of the Baba and Nyonya Heritage Museum, showing documented Peranakan "
                    "domestic display rather than a language classroom."
                ),
                "image_url": "/static/images/baba_museum_interior.jpg",
                "source_name": "Michael Coghlan · CC BY-SA 2.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Inside_the_Baba_and_Nyonya_Heritage_Museum.jpg",
            },
        ],
        "videos": [],
        "sources": [
            {
                "title": "ASJP wordlist Malay Baba",
                "organization": "ASJP / CLLD (CC BY 4.0)",
                "url": "https://asjp.clld.org/languages/MALAY_BABA",
            },
            {
                "title": "ISO 639-3 mbf Baba Malay",
                "organization": "ISO 639-3",
                "url": "https://iso639-3.sil.org/code/mbf",
            },
        ],
    },
    "temoq": {
        "display_name": "Temoq",
        "aliases": ["Temo'"],
        "blurb": "A Southern Aslian language of Pahang with a small published basic wordlist and limited public documentation.",
        "region": "Pahang, Peninsular Malaysia",
        "community": "Temoq communities",
        "eyebrow": "Orang Asli language of Pahang",
        "about_title": "A Southern Aslian language with sparse public lexicon",
        "about": (
            "Temoq is classified as Southern Aslian (Austroasiatic). "
            "Lessons teach community, geography, and documentation limits. "
            "Comparative transcription is not used as ordinary student spelling."
        ),
        "speakers_title": "Temoq community",
        "speakers": (
            "Public comparative databases treat Temoq as a distinct Southern Aslian language. "
            "ASJP does not list a speaker count on this record (field is 0 / empty). "
            "No population figure is invented here."
        ),
        "location_title": "Pahang (ASJP 4.00°N, 102.50°E)",
        "location": (
            "The map uses the published ASJP coordinates 4.00°N, 102.50°E in Pahang, "
            "kept separate from the Chewong beacon further south in the same state."
        ),
        "preservation_title": "High documentation need, small open wordlist",
        "preservation": (
            "Because reusable learner spelling is limited, lessons stay with documented "
            "community and source facts. That is a documentation constraint, not a claim "
            "that the language only has a handful of words."
        ),
        "verification_status": "Under Review",
        "exclude_dictionary": True,
        "verification_note": (
            "No community orthography pack is bundled; comparative Temoq strings are not "
            "shown as learner dictionary words. No EGIDS grade is assigned in this course."
        ),
        "vitality": {
            "classification": "Living (ASJP status field: alive); speaker count not given on that record",
            "system": "ASJP status field",
            "year": None,
            "source": "ASJP Database wordlist TEMOQ (source note: Benjamin 1976)",
            "note": "Do not convert ‘small documentation’ into a fabricated endangerment grade.",
        },
        "gallery": [
            {
                "title": "Tasik Chini, Pahang",
                "caption": (
                    "Tasik Chini, Pahang. Published descriptions locate Temoq settlements on the "
                    "southern side of this lake. Landscape only — not a photograph of Temoq people."
                ),
                "image_url": "/static/images/temoq_tasik_chini.jpg",
                "source_name": "Rubenjoker · CC BY-SA 4.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Tasik_chini_01.jpg",
            },
            {
                "title": "Tasik Chini shoreline",
                "caption": (
                    "Another view of Tasik Chini, Pahang, included as geographic context for "
                    "Temoq documentation rather than as ethnographic portraiture."
                ),
                "image_url": "/static/images/temoq_tasik_chini_2.jpg",
                "source_name": "Rubenjoker · CC BY-SA 4.0",
                "source_url": "https://commons.wikimedia.org/wiki/File:Tasik_chini_06.JPG",
            },
        ],
        "videos": [],
        "sources": [
            {
                "title": "ASJP wordlist Temoq",
                "organization": "ASJP / CLLD (CC BY 4.0); source Benjamin 1976",
                "url": "https://asjp.clld.org/languages/TEMOQ",
            },
            {
                "title": "ISO 639-3 tmo",
                "organization": "SIL ISO 639-3",
                "url": "https://iso639-3.sil.org/code/tmo",
            },
        ],
    },
}


def apply_extended_languages(languages: dict, course_data: dict, language_family: dict, explore_unlocks: dict) -> None:
    for key, profile in EXTENDED_LANGUAGE_PROFILES.items():
        languages[key] = profile
        language_family[key] = EXTENDED_FAMILY[key]
        explore_unlocks.setdefault(key, {})
    course_data.update(all_extended_course_data())


def map_payload() -> dict:
    states: dict[str, list[str]] = {}
    points = []
    for key, geo in MAP_COORDS.items():
        states.setdefault(geo["state"], []).append(key)
        points.append(
            {
                "key": key,
                "display_name": DISPLAY_NAMES.get(key, key),
                "lat": geo["lat"],
                "lon": geo["lon"],
                "state": geo["state"],
                "frame": geo["frame"],
            }
        )
    return {
        "points": points,
        "state_counts": {state: len(keys) for state, keys in states.items()},
    }
