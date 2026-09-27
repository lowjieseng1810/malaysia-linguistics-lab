"""Course steps for extended languages: language/community knowledge, not catalog IDs.

Lexical teaching is included only when a clean learner-facing orthography is
already in a verified pack (Kristang Wikikamus / Baxter 2004). ASJP encodings
are never shown as ordinary vocabulary.
"""

from __future__ import annotations

from typing import Any

LEVEL_TITLES = {
    1: "Community and Place",
    2: "Status and Documentation",
    3: "Language in Contact",
}

# Kept for tests that still import the name; knowledge courses are not wordlists.
TEACHING_SETS: dict[str, dict[int, list[str]]] = {}


def _fact_card(title: str, heading: str, statement: str, note: str) -> dict[str, Any]:
    return {
        "type": "vocabulary",
        "title": title,
        "instruction": "Study this source-backed fact about the language and its community.",
        "word": heading,
        "meaning": statement,
        "note": note,
        "exclude_from_dictionary": True,
    }


def _quiz(
    question: str,
    options: list[str],
    correct_index: int,
    hint: str,
    explanation: str,
) -> dict[str, Any]:
    return {
        "type": "quiz",
        "question": question,
        "instruction": "Choose the statement supported by the sources used in this course.",
        "options": options,
        "correctIndex": correct_index,
        "hint": hint,
        "correctFeedback": explanation,
        "wrongFeedback": explanation,
        "difficulty": "medium",
    }


def _level(title: str, cards: list[dict[str, Any]], quizzes: list[dict[str, Any]]) -> dict[str, Any]:
    steps = list(cards)
    steps.extend(quizzes)
    return {"steps": steps}


def _kristang_lex_card(word: str, meaning: str) -> dict[str, Any]:
    return {
        "type": "vocabulary",
        "title": LEVEL_TITLES[3],
        "instruction": "This form is from the Wikikamus Swadesh appendix compiled from Baxter (2004).",
        "word": word,
        "meaning": meaning,
        "note": (
            "Wikikamus: Lampiran Senarai Swadesh bahasa Kristang (CC BY-SA), "
            "compiled from Baxter & de Silva 2004. Malacca Kristang orthography."
        ),
    }


def bookan_course() -> dict[int, dict[str, Any]]:
    t1, t2, t3 = LEVEL_TITLES[1], LEVEL_TITLES[2], LEVEL_TITLES[3]
    return {
        1: _level(
            t1,
            [
                _fact_card(
                    t1,
                    "Where Bookan is spoken",
                    "Bookan is a Murutic language of interior Sabah, associated with Keningau District.",
                    "Kluge & Choi (2017) situate Bookan in Keningau District, southwestern Sabah. "
                    "ELAR collection notes also name Keningau, Sook, Tulid, and Lanas.",
                ),
                _fact_card(
                    t1,
                    "Community names",
                    "Published sources list the language as Bookan and also as Baukan Murut.",
                    "Catalog identifiers exist for archival lookup; they are references, not what this lesson asks you to memorise.",
                ),
                _fact_card(
                    t1,
                    "Language family",
                    "Bookan is described as Austronesian, in the Murutic group of Sabah.",
                    "This follows published survey and catalog classification, not a new fieldwork claim.",
                ),
                _fact_card(
                    t1,
                    "Speaker figures in documentation",
                    "Public documentation pages cite on the order of 2,400 speakers or fewer — a documentation estimate, not a census.",
                    "ELAR / Culture in Crisis project pages; treat the figure as reported, not independently recounted here.",
                ),
            ],
            [
                _quiz(
                    "Which Malaysian state and district are associated with Bookan in the 2017 SIL survey?",
                    [
                        "Keningau District, Sabah",
                        "Kuala Krau, Pahang",
                        "Portuguese Settlement, Melaka",
                        "Carey Island, Selangor",
                    ],
                    0,
                    "Look for the interior Sabah district named in Kluge & Choi (2017), not a Peninsular Orang Asli area.",
                    "Kluge & Choi (2017) locate Bookan in Keningau District, southwestern Sabah.",
                ),
                _quiz(
                    "Which language family do published surveys assign to Bookan?",
                    [
                        "Austronesian (Murutic)",
                        "Austroasiatic (Northern Aslian)",
                        "Portuguese-based creole",
                        "Malay-based Peranakan contact language",
                    ],
                    0,
                    "Bookan is grouped with other Murut varieties of Sabah, not with Aslian or Melaka creoles.",
                    "Bookan is described as an Austronesian Murutic language of Sabah.",
                ),
            ],
        ),
        2: _level(
            t2,
            [
                _fact_card(
                    t2,
                    "Documented vitality (2017)",
                    "A 2017 SIL rapid-appraisal survey classified Bookan as EGIDS 7 Shifting.",
                    "Kluge, A. & Choi, J.-H. 2017. Bookan Language Vitality. SIL Electronic Survey Reports 2017-008. "
                    "This is that survey’s finding, not a new grade assigned by this course.",
                ),
                _fact_card(
                    t2,
                    "Language shift named in the survey",
                    "The same survey reports shift toward Sabah Malay, especially among children.",
                    "Summarised from Kluge & Choi 2017; not a claim about every household.",
                ),
                _fact_card(
                    t2,
                    "Who still uses Bookan (survey finding)",
                    "The survey describes use among the child-bearing generation among themselves, while children often acquire Sabah Malay first.",
                    "Kluge & Choi 2017 rapid appraisal; source-specific.",
                ),
                _fact_card(
                    t2,
                    "Why this course has no Bookan wordlist",
                    "No reusable, openly licensed Bookan lexicon is bundled here, so lessons teach documented facts rather than invented words.",
                    "ELAR deposits include transcription, but this course does not copy those wordlists.",
                ),
            ],
            [
                _quiz(
                    "What vitality grade did Kluge & Choi (2017) report for Bookan?",
                    [
                        "EGIDS 7 Shifting",
                        "EGIDS 1 National",
                        "No published survey exists",
                        "The language is described only as a Portuguese creole",
                    ],
                    0,
                    "The SIL 2017 rapid-appraisal paper uses the EGIDS scale and reports shifting use.",
                    "Kluge & Choi (2017) classified Bookan as EGIDS 7 Shifting.",
                ),
                _quiz(
                    "Toward which language does that 2017 survey report shift?",
                    [
                        "Sabah Malay",
                        "Kristang",
                        "Temoq",
                        "Standard Portuguese",
                    ],
                    0,
                    "The named shift language is the regional Malay of Sabah, not a Melaka heritage variety.",
                    "Kluge & Choi (2017) report shift toward Sabah Malay, especially among children.",
                ),
            ],
        ),
        3: _level(
            t3,
            [
                _fact_card(
                    t3,
                    "Archive documentation",
                    "An ELDP / Universiti Malaya project deposits Bookan recordings in the Endangered Languages Archive.",
                    "Collection pages describe audio, video, transcription, and images. Collection identifiers are source locators, not quiz answers to memorise.",
                ),
                _fact_card(
                    t3,
                    "What the deposit contains",
                    "Public pages describe narratives, daily practices, songs, and music, with Bookan transcription and Malay/English translation.",
                    "Described on the ELAR collection page; this course does not copy those transcripts as learner vocabulary.",
                ),
                _fact_card(
                    t3,
                    "Documentation goal",
                    "Project summaries describe lexicon establishment and morphosyntactic analysis for community and researchers.",
                    "ELDP / Culture in Crisis summary of the documentation project. Work is ongoing; do not treat it as a finished school curriculum.",
                ),
                _fact_card(
                    t3,
                    "Sentence-structure note",
                    "A preliminary public note mentions VSO order; the archive itself flags this as still under discussion.",
                    "Do not upgrade a preliminary archive note into a settled grammar rule.",
                ),
            ],
            [
                _quiz(
                    "What kind of documentation is publicly described for Bookan?",
                    [
                        "An endangered-language archive deposit with audio, video, and transcription",
                        "A complete CC-licensed learner dictionary bundled in this app",
                        "A national-language school syllabus used in every Sabah school",
                        "A Portuguese Settlement parish grammar from Melaka",
                    ],
                    0,
                    "Think of the ELAR / ELDP documentation project, not a Melaka creole grammar.",
                    "ELAR collection pages describe an audio-visual documentation deposit. This course does not bundle a Bookan learner lexicon.",
                ),
                _quiz(
                    "How should a preliminary public note that Bookan may be VSO be treated?",
                    [
                        "As a preliminary archive note, still under discussion",
                        "As a proven universal rule of all Murut languages",
                        "As evidence that Bookan is a Portuguese creole",
                        "As proof that no documentation exists",
                    ],
                    0,
                    "The archive text itself treats the word-order note as preliminary.",
                    "ELAR English collection text flags VSO as preliminary — not a settled grammar rule.",
                ),
            ],
        ),
    }


def chewong_course() -> dict[int, dict[str, Any]]:
    t1, t2, t3 = LEVEL_TITLES[1], LEVEL_TITLES[2], LEVEL_TITLES[3]
    return {
        1: _level(
            t1,
            [
                _fact_card(
                    t1,
                    "Community and names",
                    "Chewong is also listed as Che Wong, Cheq Wong, Ceq Wong, and Siwang.",
                    "These are published name variants, not invented spellings.",
                ),
                _fact_card(
                    t1,
                    "Where it is associated",
                    "The language is associated with Chewong / Cheq Wong communities in Pahang, including the Krau region.",
                    "Krau-region place names used here are landscape context, not household GPS.",
                ),
                _fact_card(
                    t1,
                    "Language family",
                    "Chewong is an Austroasiatic language of the Northern Aslian branch.",
                    "This is the published classification used in this course. It is distinct from Southern Aslian Mah Meri and Temoq.",
                ),
                _fact_card(
                    t1,
                    "Orang Asli context",
                    "Chewong is one of the Aslian languages of Peninsular Malaysia’s Orang Asli communities.",
                    "Aslian is the Austroasiatic subgroup of the peninsula; it is not Austronesian.",
                ),
            ],
            [
                _quiz(
                    "Which Malaysian state is associated with Chewong in this course’s sources?",
                    ["Pahang", "Sabah", "Sarawak", "Melaka"],
                    0,
                    "Chewong / Ceq Wong documentation used here points to the Krau region of central Pahang.",
                    "Published coordinates and community descriptions place Chewong in Pahang, not Borneo or Melaka.",
                ),
                _quiz(
                    "Which classification does this course use for Chewong?",
                    [
                        "Austroasiatic, Northern Aslian",
                        "Austronesian, Murutic",
                        "Portuguese-based creole",
                        "Malay-based Peranakan contact language",
                    ],
                    0,
                    "Chewong is grouped with other Aslian languages of the peninsula, not with Murut or Melaka creoles.",
                    "Chewong is Northern Aslian (Austroasiatic), distinct from Murutic Bookan and from Kristang.",
                ),
            ],
        ),
        2: _level(
            t2,
            [
                _fact_card(
                    t2,
                    "Krau region",
                    "Chewong / Cheq Wong documentation used here is associated with the Krau region of central Pahang, including Kuala Krau.",
                    "Place photographs of Kuala Krau and Krau Wildlife Reserve are landscape context, not household GPS.",
                ),
                _fact_card(
                    t2,
                    "Orang Asli Aslian setting",
                    "Chewong is an Orang Asli language of Peninsular Malaysia, in the Aslian (Austroasiatic) group.",
                    "It is not Austronesian and not a Melaka heritage creole.",
                ),
                _fact_card(
                    t2,
                    "Vitality claims this course will not invent",
                    "Published records treat Chewong as a living language. This course does not invent an EGIDS grade for it.",
                    "Absence of a numbered vitality grade is not evidence of safety or of extinction.",
                ),
                _fact_card(
                    t2,
                    "Learner spelling under review",
                    "No community-workshop orthography pack is bundled here, so Chewong vocabulary stays under review rather than being displayed as school spelling.",
                    "Verification status remains Under Review for learner-facing lexicon.",
                ),
            ],
            [
                _quiz(
                    "Which Pahang region is associated with Chewong in the documentation used here?",
                    [
                        "The Krau region, including Kuala Krau",
                        "Keningau District in interior Sabah",
                        "The Portuguese Settlement in Melaka",
                        "The Rajang basin in Sarawak",
                    ],
                    0,
                    "Think of central Pahang wildlife-reserve country, not Borneo or Melaka.",
                    "Chewong / Cheq Wong sources used here point to the Krau region of Pahang.",
                ),
                _quiz(
                    "Which vitality claim does this course refuse to invent for Chewong?",
                    [
                        "An EGIDS number copied from another language’s survey",
                        "That Chewong is associated with Pahang",
                        "That Chewong is Northern Aslian",
                        "That Chewong is an Orang Asli language",
                    ],
                    0,
                    "Bookan has a named 2017 EGIDS finding; that grade must not be copied onto Chewong.",
                    "This course treats Chewong as living in published records but does not assign an EGIDS number.",
                ),
            ],
        ),
        3: _level(
            t3,
            [
                _fact_card(
                    t3,
                    "Aslian neighbours",
                    "On this course’s family tree, Chewong is Northern Aslian, while Mah Meri and Temoq are Southern Aslian.",
                    "Shared Aslian heritage does not mean the languages are interchangeable. Each has its own community and documentation.",
                ),
                _fact_card(
                    t3,
                    "Geography versus Borneo languages",
                    "Chewong is a Peninsular Malaysia language of Pahang, not a Sabah Murutic or Sarawak Malayic language.",
                    "Map beacons for Chewong use Pahang, not Keningau or the Rajang.",
                ),
                _fact_card(
                    t3,
                    "Preservation implication",
                    "Because reusable learner spelling is limited here, preservation in this course means citing documentation honestly rather than filling pages with guessed words.",
                    "Students can still learn community, place, family, and source limits.",
                ),
            ],
            [
                _quiz(
                    "How does this course distinguish Chewong from Temoq?",
                    [
                        "Chewong is Northern Aslian; Temoq is Southern Aslian — both in Pahang",
                        "Chewong is Murutic of Sabah; Temoq is a Melaka creole",
                        "They are two names for Kristang",
                        "Temoq is national Malay and Chewong is Iban",
                    ],
                    0,
                    "Both are Aslian languages of Pahang, but they sit on different Aslian branches in this course’s family tree.",
                    "Chewong is Northern Aslian; Temoq is grouped with Southern Aslian alongside Mah Meri.",
                ),
            ],
        ),
    }


def kristang_course() -> dict[int, dict[str, Any]]:
    t1, t2, t3 = LEVEL_TITLES[1], LEVEL_TITLES[2], LEVEL_TITLES[3]
    return {
        1: _level(
            t1,
            [
                _fact_card(
                    t1,
                    "Community",
                    "Kristang (Papia Kristang) is the Portuguese-based creole associated with the Portuguese-Eurasian community of Melaka.",
                    "Baxter (1988, 2004) describes it as a creole, not as sixteenth-century Portuguese transplanted unchanged.",
                ),
                _fact_card(
                    t1,
                    "Place",
                    "The language is especially associated with the Portuguese Settlement (Kampung Portugis) in Melaka.",
                    "ASJP Papia Kristang coordinates 2.20°N, 102.27°E match that settlement area used on the map.",
                ),
                _fact_card(
                    t1,
                    "What kind of language",
                    "Kristang is a Portuguese-based creole (Malacca Creole Portuguese), not a dialect of modern European Portuguese.",
                    "Creole here means a language that developed in a contact setting, with its own grammar described in Baxter’s reference grammar.",
                ),
            ],
            [
                _quiz(
                    "Which community and city are associated with Kristang in this course?",
                    [
                        "Portuguese-Eurasian community of Melaka",
                        "Murut communities of Keningau",
                        "Chewong communities of Krau, Pahang",
                        "Iban longhouse communities of the Rajang",
                    ],
                    0,
                    "Kristang is the Melaka Portuguese Settlement language, not a Borneo interior language.",
                    "Papia Kristang is tied to Melaka’s Portuguese-Eurasian community.",
                ),
                _quiz(
                    "How does Baxter’s published description treat Kristang?",
                    [
                        "As a Portuguese-based creole with its own grammar",
                        "As unchanged 16th-century court Portuguese",
                        "As a Murutic language of Sabah",
                        "As Southern Aslian Orang Asli speech",
                    ],
                    0,
                    "A creole has developed its own system; Baxter’s grammar is the published reference used here.",
                    "Baxter (1988) is a grammar of Kristang as Malacca Creole Portuguese, not a claim that it is identical to early modern Portuguese.",
                ),
            ],
        ),
        2: _level(
            t2,
            [
                _fact_card(
                    t2,
                    "Speaker figure on one record",
                    "ASJP lists about 300 speakers on the Papia Kristang record — source-specific, not a new census.",
                    "Small published counts describe a small community; they are not upgraded here into an EGIDS grade.",
                ),
                _fact_card(
                    t2,
                    "Revitalisation (publicly documented)",
                    "Community-led classes such as Kodrah Kristang are publicly documented as revitalisation work.",
                    "This app does not claim partnership with those groups.",
                ),
                _fact_card(
                    t2,
                    "Dictionary tradition",
                    "A dictionary (Baxter & de Silva 2004) and a reference grammar (Baxter 1988) anchor the documented lexicon used here.",
                    "Learner forms in this course come from the Wikikamus Swadesh appendix compiled from that dictionary (CC BY-SA).",
                ),
            ],
            [
                _quiz(
                    "What revitalisation work does this course mention without claiming partnership?",
                    [
                        "Publicly documented community classes such as Kodrah Kristang",
                        "A national requirement to teach Kristang in every Malaysian school",
                        "An ELAR Bookan deposit in Keningau",
                        "A Peranakan museum catalogue from Singapore only",
                    ],
                    0,
                    "Look for Melaka Portuguese-Eurasian community classes named in public sources.",
                    "Kodrah Kristang is cited as publicly documented revitalisation, not as an institutional partner of this app.",
                ),
                _quiz(
                    "Where do this course’s Kristang learner spellings come from?",
                    [
                        "Wikikamus Swadesh appendix compiled from Baxter 2004 (CC BY-SA)",
                        "Raw ASJP symbol strings displayed as school spelling",
                        "Invented forms with no source",
                        "The 2017 Bookan SIL survey",
                    ],
                    0,
                    "The bundled Kristang list is a Wikikamus appendix that cites Baxter’s dictionary.",
                    "Clean Malacca Kristang orthography in this course follows that CC BY-SA Swadesh appendix.",
                ),
            ],
        ),
        3: _level(
            t3,
            [
                _kristang_lex_card("yo", "I"),
                _kristang_lex_card("bos", "you (singular)"),
                _kristang_lex_card("mai", "mother"),
                _kristang_lex_card("pai", "father"),
                _kristang_lex_card("ngua", "one"),
                _kristang_lex_card("dos", "two"),
                _fact_card(
                    t3,
                    "Contact setting",
                    "Kristang developed in Melaka’s Portuguese-Eurasian community, in long contact with Malay and other local languages.",
                    "Contact history explains why it is classified as a creole rather than as a regional dialect of European Portuguese.",
                ),
            ],
            [
                _quiz(
                    "Which Kristang form is taught here for “I”, following the Wikikamus / Baxter appendix?",
                    ["yo", "saya", "aku", "nuan"],
                    0,
                    "The Kristang first-person form in that appendix is the short pronoun yo, not Malay saya and not an ASJP Aslian string.",
                    "Wikikamus Swadesh (Baxter 2004 compilation) lists yo = I for Malacca Kristang.",
                ),
                _quiz(
                    "Which Kristang form is taught here for “you (singular)”?",
                    ["bos", "lu", "nuan", "kita"],
                    0,
                    "Kristang uses bos in the bundled Swadesh appendix; lu is associated with Baba Malay in other sources, not this Kristang list.",
                    "Wikikamus / Baxter appendix: bos = you (singular).",
                ),
            ],
        ),
    }


def baba_malay_course() -> dict[int, dict[str, Any]]:
    t1, t2, t3 = LEVEL_TITLES[1], LEVEL_TITLES[2], LEVEL_TITLES[3]
    return {
        1: _level(
            t1,
            [
                _fact_card(
                    t1,
                    "Community",
                    "Baba Malay is a Malay-based contact language associated with Peranakan (Baba Nyonya) communities.",
                    "Academic descriptions note Sinitic substrate influence. This course does not invent a new grammar sketch.",
                ),
                _fact_card(
                    t1,
                    "Place in this course",
                    "This map and course treat Melaka as the Malaysian place associated with Baba Malay here.",
                    "The ASJP Malay Baba record coordinates point to Singapore; this course does not move the map beacon to Singapore.",
                ),
                _fact_card(
                    t1,
                    "Related but distinct",
                    "Baba Malay is not the same language as Kristang, even though both have heritage communities in Melaka.",
                    "Kristang is Portuguese-based; Baba Malay is Malay-based and Peranakan.",
                ),
            ],
            [
                _quiz(
                    "Which community is Baba Malay associated with in this course?",
                    [
                        "Peranakan / Baba Nyonya communities",
                        "Murut Bookan communities of Keningau",
                        "Chewong communities of Krau",
                        "Kadazan ritual specialists of Penampang",
                    ],
                    0,
                    "Peranakan (Baba Nyonya) heritage is the community named in the Baba Malay sources used here.",
                    "Baba Malay is linked with Peranakan communities; Kristang is the Portuguese-Eurasian creole of the same city.",
                ),
                _quiz(
                    "How does this course distinguish Baba Malay from Kristang?",
                    [
                        "Baba Malay is Malay-based and Peranakan; Kristang is Portuguese-based creole",
                        "They are two names for the same Portuguese creole",
                        "Both are Northern Aslian languages of Pahang",
                        "Baba Malay is Murutic and Kristang is Dusunic",
                    ],
                    0,
                    "Family and community differ even though both heritage languages are mapped to Melaka.",
                    "Classification in this course: Malay-based contact language versus Portuguese-based creole.",
                ),
            ],
        ),
        2: _level(
            t2,
            [
                _fact_card(
                    t2,
                    "Contact grammar noted in sources",
                    "Academic descriptions of Baba Malay note Sinitic substrate influence on a Malay-based contact language.",
                    "That is a published contact characterisation, not a full grammar written for this app.",
                ),
                _fact_card(
                    t2,
                    "A documented contact pronoun",
                    "Published descriptions include a distinctive second-person form lu, alongside items that overlap Malay.",
                    "This is a contact feature, not permission to invent a learner wordlist.",
                ),
                _fact_card(
                    t2,
                    "Heritage documentation, not a partnership",
                    "Peranakan heritage in Melaka is publicly documented in museums and published grammars. This course does not claim those institutions endorse the app.",
                    "Learner spelling stays under review because no community orthography pack is bundled here.",
                ),
                _fact_card(
                    t2,
                    "Vitality grade",
                    "This course does not assign an EGIDS number to Baba Malay.",
                    "Bookan’s EGIDS 7 is from a named 2017 SIL survey and must not be copied here.",
                ),
            ],
            [
                _quiz(
                    "Which contact characterisation do academic descriptions used here give for Baba Malay?",
                    [
                        "A Malay-based contact language with Sinitic substrate influence",
                        "A Portuguese-based creole of the Portuguese Settlement",
                        "A Murutic language of interior Sabah",
                        "A Northern Aslian Orang Asli language of Krau",
                    ],
                    0,
                    "Think of Peranakan heritage and Malay plus Chinese-language contact, not Kristang or Bookan.",
                    "Baba Malay is described as Malay-based with Sinitic substrate influence.",
                ),
                _quiz(
                    "Which second-person form do published descriptions note for Baba Malay?",
                    [
                        "lu",
                        "bos",
                        "nuan",
                        "kopi",
                    ],
                    0,
                    "The Peranakan contact pronoun is not the Kristang Swadesh form bos, and not Iban nuan.",
                    "Sources used here note lu as a distinctive Baba Malay second-person form.",
                ),
            ],
        ),
        3: _level(
            t3,
            [
                _fact_card(
                    t3,
                    "Heritage setting",
                    "Peranakan heritage in Melaka includes language alongside other cultural practices; this course teaches language facts, not a museum partnership.",
                    "Gallery photographs of public heritage places are not claims that those institutions endorse this app.",
                ),
                _fact_card(
                    t3,
                    "Contact and shift",
                    "As a Malay-based contact language, Baba Malay sits in a multilingual setting with Malay, Chinese varieties, and English in the Straits region.",
                    "This course does not invent a timeline of shift. It only notes the contact setting described in the sources used.",
                ),
                _fact_card(
                    t3,
                    "Singapore note",
                    "Some published coordinates for Baba Malay point to Singapore; Malaysian Melaka remains the map location used in this course.",
                    "Two historically linked Peranakan centres exist; choosing Melaka for the Malaysian map is a course decision, not a denial of Singapore Peranakan history.",
                ),
            ],
            [
                _quiz(
                    "Which map choice does this Malaysian course make for Baba Malay?",
                    [
                        "Melaka, while noting a historically wider Peranakan network that also includes Singapore",
                        "Keningau, Sabah",
                        "Krau, Pahang",
                        "Kuching, Sarawak",
                    ],
                    0,
                    "This course’s Malaysia map uses Melaka; published Peranakan history is not limited to one city.",
                    "The Melaka beacon is a course mapping choice for Malaysia, not a denial of Singapore Peranakan communities.",
                ),
            ],
        ),
    }


def temoq_course() -> dict[int, dict[str, Any]]:
    t1, t2, t3 = LEVEL_TITLES[1], LEVEL_TITLES[2], LEVEL_TITLES[3]
    return {
        1: _level(
            t1,
            [
                _fact_card(
                    t1,
                    "Community",
                    "Temoq is an Aslian language associated with Orang Asli communities in Pahang.",
                    "It is not a Melaka heritage creole and not a Sabah Murutic language.",
                ),
                _fact_card(
                    t1,
                    "Place",
                    "This course maps Temoq in Pahang. Published descriptions locate settlements on the southern side of Tasik Chini.",
                    "The Pahang map beacon is a state association, kept separate from Chewong in the same state. Lake location is geographic context, not household GPS.",
                ),
                _fact_card(
                    t1,
                    "Language family",
                    "Temoq is classified here as Austroasiatic, Southern Aslian — the same Aslian branch grouping used for Mah Meri.",
                    "Shared branch does not mean Temoq and Mah Meri are the same language or community.",
                ),
            ],
            [
                _quiz(
                    "Which state does this course associate with Temoq?",
                    ["Pahang", "Sabah", "Sarawak", "Melaka"],
                    0,
                    "Look for the Krau / Tasik Chini side of Pahang, not Melaka or Sabah.",
                    "Temoq is mapped to Pahang. Chewong is also Pahang; Bookan is Sabah; Kristang is Melaka.",
                ),
                _quiz(
                    "Which classification does this course use for Temoq?",
                    [
                        "Austroasiatic, Southern Aslian",
                        "Austronesian, Murutic",
                        "Portuguese-based creole",
                        "Malayic Ibanic",
                    ],
                    0,
                    "Temoq is grouped with Southern Aslian, alongside Mah Meri, not with Iban or Bookan.",
                    "Southern Aslian is the branch used here for Temoq.",
                ),
            ],
        ),
        2: _level(
            t2,
            [
                _fact_card(
                    t2,
                    "Tasik Chini area",
                    "Published descriptions locate Temoq settlements on the southern side of Tasik Chini in Pahang.",
                    "Lake photographs are geographic context, not portraits of speakers.",
                ),
                _fact_card(
                    t2,
                    "Orang Asli, Southern Aslian",
                    "Temoq is a Southern Aslian Orang Asli language of Pahang, in the same Aslian branch as Mah Meri but not the same community.",
                    "Mah Meri is associated with coastal Selangor in this course; Temoq is mapped to Pahang.",
                ),
                _fact_card(
                    t2,
                    "What this course will not invent",
                    "No usable published speaker census or EGIDS grade is bundled here, so none is invented.",
                    "Limited documentation is not turned into a claim that the language has only a handful of words.",
                ),
                _fact_card(
                    t2,
                    "Learner spelling under review",
                    "No community orthography pack is bundled, so Temoq vocabulary stays under review.",
                    "Lessons stay with community, geography, and documentation limits.",
                ),
            ],
            [
                _quiz(
                    "Which Pahang landscape is named in published descriptions of Temoq settlement used here?",
                    [
                        "The southern side of Tasik Chini",
                        "Carey Island in Selangor",
                        "Keningau District in Sabah",
                        "The Portuguese Settlement in Melaka",
                    ],
                    0,
                    "Think of a lake in Pahang, not a Melaka settlement or a Sabah district.",
                    "Published descriptions locate Temoq settlements on the southern side of Tasik Chini.",
                ),
                _quiz(
                    "Which vitality statement does this course make about Temoq?",
                    [
                        "It does not invent a speaker census or EGIDS grade from incomplete records",
                        "It copies Bookan’s 2017 EGIDS 7 onto Temoq",
                        "It treats Temoq as Malaysia’s national language",
                        "It treats Temoq as a Portuguese creole",
                    ],
                    0,
                    "Missing counts stay missing; Bookan’s Sabah survey is not reused here.",
                    "No Temoq census or EGIDS grade is bundled, and none is fabricated.",
                ),
            ],
        ),
        3: _level(
            t3,
            [
                _fact_card(
                    t3,
                    "Two Pahang Aslian languages",
                    "Chewong (Northern Aslian) and Temoq (Southern Aslian) are both mapped to Pahang and must not be collapsed into one language.",
                    "Pahang’s two living languages in this course’s map counter are Chewong and Temoq.",
                ),
                _fact_card(
                    t3,
                    "Intergenerational transmission",
                    "This course does not invent a transmission study for Temoq. Where evidence is missing, lessons say so.",
                    "Students should not be asked to guess whether children still speak Temoq as a first language.",
                ),
                _fact_card(
                    t3,
                    "Compared with Mah Meri",
                    "Mah Meri is also Southern Aslian but is associated with coastal Selangor communities, not with the Pahang Temoq mapping used here.",
                    "Same branch, different state association in this course.",
                ),
            ],
            [
                _quiz(
                    "Which two languages make Pahang’s count of two living languages in this course?",
                    [
                        "Chewong and Temoq",
                        "Iban and Bidayuh",
                        "Kristang and Baba Malay",
                        "Bookan and Kadazan-Dusun",
                    ],
                    0,
                    "Pahang on this map is the Orang Asli Aslian pair, not the Melaka pair and not the Sarawak pair.",
                    "Map state_counts: Pahang = Chewong + Temoq.",
                ),
                _quiz(
                    "How does this course treat claims about Temoq children’s first language?",
                    [
                        "It does not invent a transmission study; missing evidence stays missing",
                        "It asserts that all Temoq children are monolingual English speakers",
                        "It asserts that Temoq is the national medium of instruction",
                        "It copies Bookan’s 2017 child-shift finding onto Temoq",
                    ],
                    0,
                    "Bookan’s child-shift finding is from a named Sabah survey and must not be copied onto Temoq.",
                    "No Temoq intergenerational survey is bundled; the course refuses to fabricate one.",
                ),
            ],
        ),
    }


def all_extended_course_data() -> dict[str, dict[int, dict[str, Any]]]:
    return {
        "bookan": bookan_course(),
        "chewong": chewong_course(),
        "kristang": kristang_course(),
        "baba-malay": baba_malay_course(),
        "temoq": temoq_course(),
    }
