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
                    "ISO 639-3 bnb / Glottolog book1241 are catalog codes for this language; "
                    "they are references, not the lesson content.",
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
                    "ASJP Ceq Wong coordinates are 3.23°N, 102.42°E in central Pahang; they are list coordinates, not a household GPS point.",
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
                    "Published basic wordlist",
                    "A basic comparative wordlist for Ceq Wong is published in the ASJP database under a CC BY licence.",
                    "That list uses ASJP transcription symbols. This course does not present those encodings as everyday spelling.",
                ),
                _fact_card(
                    t2,
                    "What this course does not invent",
                    "No community-workshop orthography for Chewong is bundled here, so learner vocabulary stays under review.",
                    "Accuracy is preferred over displaying machine transcription as if it were school spelling.",
                ),
                _fact_card(
                    t2,
                    "Vitality in the ASJP record",
                    "The ASJP Ceq Wong record marks the language as living; it does not publish an EGIDS grade on that record.",
                    "Do not invent an EGIDS label. Absence of a grade is not evidence of safety or of extinction.",
                ),
                _fact_card(
                    t2,
                    "Documentation stance",
                    "Entries used internally for research comparison are source-verified against the ASJP Ceq Wong list, not against a community workshop in this project.",
                    "Verification status remains Under Review for learner-facing lexicon.",
                ),
            ],
            [
                _quiz(
                    "Why does this course not teach raw ASJP strings as ordinary Chewong spelling?",
                    [
                        "ASJP is a comparative transcription, not a community orthography bundled here",
                        "Chewong has no published sources of any kind",
                        "ASJP strings are Portuguese creole spellings",
                        "The language is not associated with Pahang",
                    ],
                    0,
                    "ASJP was designed for cross-language comparison and uses special symbols (for example 7, N, *).",
                    "Without a bundled community/scholarly orthography, raw ASJP codes are not shown as learner vocabulary.",
                ),
                _quiz(
                    "What vitality information does the ASJP Ceq Wong record actually give?",
                    [
                        "A living/alive status field, without an EGIDS grade on that record",
                        "EGIDS 0 International",
                        "Proof that no speakers remain",
                        "A national-language status in Malaysia",
                    ],
                    0,
                    "ASJP’s own status field is not the same as an Ethnologue EGIDS number.",
                    "This course does not invent an EGIDS grade for Chewong from the ASJP record.",
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
                    "ASJP record (source-specific)",
                    "The ASJP Malay Baba list is published under CC BY 4.0 and marks the language as living on that record.",
                    "ASJP also lists a speaker figure of 12,000 on that record. This course does not turn that field into an EGIDS grade.",
                ),
                _fact_card(
                    t2,
                    "Why learner spelling is limited here",
                    "Much of the bundled ASJP Baba Malay list uses comparative transcription symbols, which this course does not display as ordinary dictionary words.",
                    "No guessed respelling is offered. Learner lexicon remains under review except where a clean orthography source is bundled.",
                ),
                _fact_card(
                    t2,
                    "Distinctive pronoun noted in sources",
                    "Published descriptions of Baba Malay include contact features such as a distinctive second-person form lu, alongside Malay-overlapping items.",
                    "This is a documented contact feature, not a licence to dump the whole ASJP list into the learner dictionary.",
                ),
            ],
            [
                _quiz(
                    "Why is Baba Malay’s ASJP wordlist not shown as the main dictionary here?",
                    [
                        "Many items are comparative transcription, not a bundled community orthography",
                        "Baba Malay has no published sources",
                        "The language is not associated with Peranakan heritage",
                        "ASJP forbids citing Malay-based languages",
                    ],
                    0,
                    "ASJP uses special characters for sounds; those strings are not adopted here as school spelling.",
                    "Without a clean bundled orthography pack, Baba Malay vocabulary stays under review in the dictionary.",
                ),
                _quiz(
                    "Does this course assign an EGIDS number to Baba Malay?",
                    [
                        "No — ASJP does not give an EGIDS grade on that record, and none is invented here",
                        "Yes — EGIDS 0",
                        "Yes — EGIDS 9",
                        "Yes — the same EGIDS 7 used for Bookan in 2017",
                    ],
                    0,
                    "Bookan’s EGIDS 7 comes from a named 2017 SIL survey. Baba Malay has no such grade in this course.",
                    "Do not copy Bookan’s survey grade onto Baba Malay.",
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
                        "Melaka, while noting that an ASJP coordinate record points to Singapore",
                        "Keningau, Sabah",
                        "Krau, Pahang",
                        "Kuching, Sarawak",
                    ],
                    0,
                    "The course keeps Baba Malay with Melaka on the Malaysia map and records the Singapore ASJP coordinate as a source note.",
                    "Map beacon: Melaka. Source note: ASJP Malay Baba coordinates include Singapore.",
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
                    "This course maps Temoq in Pahang using published ASJP coordinates 4.00°N, 102.50°E.",
                    "Those coordinates are a list location, not a household GPS point.",
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
                    "Temoq’s published list coordinates used here are in Pahang, like Chewong, but they are not the same language.",
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
                    "Limited reusable lexicon",
                    "A published ASJP Temoq wordlist exists, but it uses comparative transcription rather than a bundled community orthography.",
                    "This course therefore does not display those encodings as ordinary dictionary entries.",
                ),
                _fact_card(
                    t2,
                    "Speaker count on that record",
                    "ASJP does not list a usable speaker count on this Temoq record (the field is 0 / empty).",
                    "Empty count is not a census of zero people, and it is not turned into an EGIDS grade here.",
                ),
                _fact_card(
                    t2,
                    "Documentation implication",
                    "Because public learner-facing spelling is limited, lessons stay with community, geography, and source limits.",
                    "Compiler credit on the ASJP Temoq list includes Julia Bischoffberger; that is source attribution, not a partnership claim.",
                ),
            ],
            [
                _quiz(
                    "What does an empty/zero speaker field on the ASJP Temoq record mean in this course?",
                    [
                        "No usable count is published on that record — not a new census and not an invented EGIDS grade",
                        "Proof that Temoq has millions of speakers",
                        "Proof that Temoq is a national language",
                        "Proof that Temoq is Kristang",
                    ],
                    0,
                    "ASJP leaving a count blank or zero is a database field, not a field survey result invented here.",
                    "This course does not invent a speaker census or vitality grade for Temoq from that empty field.",
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
