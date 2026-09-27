"""Course steps derived from verified vocabulary packs (single teaching dataset)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PACK_DIR = Path(__file__).resolve().parent / "data" / "vocabulary"

# Explicit taught sets so Quick Check cannot drift from dictionary packs.
TEACHING_SETS: dict[str, dict[int, list[str]]] = {
    "chewong": {
        1: ["iN", "m3*7", "hE7", "no*i", "ber", "To7"],
        2: ["bri7", "ki37", "E*N", "Tos", "mE*t", "mo*h"],
        3: ["%tom", "os", "tmo*7", "yow", "uh", "t3s"],
    },
    "temoq": {
        1: ["a7oc", "muy", "duwa7", "k3mah", "s3ma7", "cow"],
        2: ["c3rEh", "thih", "mont", "muh", "cih", "maham"],
        3: ["dak", "a7uh", "t3mun", "j37oh", "eleN", "dENEN"],
    },
    "baba-malay": {
        1: ["saya", "lu", "kita", "satu", "dua", "baharu"],
        2: ["oraN", "kau", "pokoh", "mata5a", "hidoN", "taNan"],
        3: ["ayer", "api", "batu", "teNok", "deNar", "dataN"],
    },
    "kristang": {
        1: ["yo", "bos", "eli", "nus", "ngka", "keng"],
        2: ["mai", "pai", "muleh", "maridu", "omi", "krensa"],
        3: ["ngua", "dos", "pesi", "albi", "kachoru", "kumih"],
    },
}

LEVEL_TITLES = {
    1: "First Meeting",
    2: "People Around You",
    3: "Everyday Encounters",
}

ASJP_MEANING = {
    "iN": "I",
    "m3*7": "you",
    "hE7": "we",
    "no*i": "one",
    "ber": "two",
    "To7": "name",
    "bri7": "person",
    "ki37": "fish",
    "E*N": "dog",
    "Tos": "hand",
    "mE*t": "eye",
    "mo*h": "nose",
    "%tom": "water",
    "os": "fire",
    "tmo*7": "stone",
    "yow": "see",
    "uh": "drink",
    "t3s": "come",
    "a7oc": "I",
    "muy": "one",
    "duwa7": "two",
    "k3mah": "name",
    "s3ma7": "person",
    "cih": "louse",
    "maham": "blood",
    "baharu": "new",
    "c3rEh": "fish",
    "cow": "dog",
    "thih": "hand",
    "mont": "eye",
    "muh": "nose",
    "dak": "water",
    "a7uh": "fire",
    "t3mun": "stone",
    "j37oh": "drink",
    "eleN": "see",
    "dENEN": "hear",
    "saya": "I",
    "lu": "you",
    "kita": "we",
    "satu": "one",
    "dua": "two",
    "oraN": "person",
    "kau": "dog",
    "pokoh": "tree",
    "mata5a": "eye",
    "hidoN": "nose",
    "taNan": "hand",
    "ayer": "water",
    "api": "fire",
    "batu": "stone",
    "teNok": "see",
    "deNar": "hear",
    "dataN": "come",
}


def _load_pack_index(lang_key: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in sorted(PACK_DIR.glob("*.json")):
        if path.name.lower() in {"sources.json", "manifest.json"}:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        packs = payload if isinstance(payload, list) else [payload]
        for pack in packs:
            if not isinstance(pack, dict):
                continue
            if (pack.get("language") or "").strip() != lang_key:
                continue
            source = (pack.get("source_ref") or "").strip()
            for entry in pack.get("entries") or []:
                word = (entry.get("word") or "").strip()
                if not word:
                    continue
                index.setdefault(
                    word,
                    {
                        "word": word,
                        "meaning": (entry.get("meaning_en") or "").strip() or ASJP_MEANING.get(word, ""),
                        "note": (entry.get("culture_note") or source).strip(),
                        "source_ref": (entry.get("source_ref") or source).strip(),
                    },
                )
    return index


def _hint(item: dict[str, Any], siblings: list[dict[str, Any]], reverse: bool, title: str) -> str:
    other = siblings[0] if siblings else None
    word = item.get("word") or ""
    asjp_note = ""
    if "7" in word or "N" in word or "*" in word or "3" in word:
        asjp_note = (
            " Source spelling uses ASJP symbols (7 often marks a glottal stop; "
            "N often marks a velar nasal)."
        )
    if reverse:
        contrast = (
            f" Contrast it with the form taught for “{other['meaning']}”, which is a different pairing."
            if other
            else ""
        )
        return (
            f"This English gloss is bound to one documented form in {title}."
            f"{contrast}{asjp_note}"
        )
    contrast = (
        f" It is not the pairing taught for “{other['word']}”."
        if other
        else ""
    )
    return (
        f"“{word}” is taught in {title} as a specific meaning, not as a look-alike neighbour."
        f"{contrast}{asjp_note}"
    )


def _explain(item: dict[str, Any], title: str) -> str:
    note = (item.get("note") or "").strip()
    extra = f" {note}" if note and "ASJP" not in note else ""
    if "ASJP" in (item.get("note") or ""):
        extra = " The spelling follows the ASJP source list used in this course."
    src = (item.get("source_ref") or "").strip()
    src_bit = f" Source: {src}." if src else ""
    return (
        f'In {title}, “{item["word"]}” is taught as “{item["meaning"]}”.'
        f"{extra}{src_bit}"
    )


def _quiz_steps(items: list[dict[str, Any]], title: str) -> list[dict[str, Any]]:
    steps = []
    n = len(items)
    if n < 4:
        return steps
    for i, item in enumerate(items):
        reverse = i % 2 == 1
        others = [x for j, x in enumerate(items) if j != i]
        distractors = others[:3]
        while len(distractors) < 3 and others:
            distractors.append(others[len(distractors) % len(others)])
        if reverse:
            options = [item["word"]] + [d["word"] for d in distractors]
            question = f'Which expression means "{item["meaning"]}"?'
            answer = item["word"]
        else:
            options = [item["meaning"]] + [d["meaning"] for d in distractors]
            question = f'What does "{item["word"]}" mean?'
            answer = item["meaning"]
        # unique options
        seen = set()
        uniq = []
        for opt in options:
            key = opt.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            uniq.append(opt)
        if len(uniq) < 2 or answer not in uniq:
            continue
        idx = uniq.index(answer)
        steps.append(
            {
                "type": "quiz",
                "question": question,
                "instruction": "Choose the form or meaning taught in this level.",
                "options": uniq[:4] if len(uniq) >= 4 else uniq,
                "correctIndex": min(idx, 3),
                "hint": _hint(item, distractors, reverse, title),
                "correctFeedback": _explain(item, title),
                "wrongFeedback": _explain(item, title),
            }
        )
    return steps


def course_from_teaching_set(lang_key: str) -> dict[int, dict[str, Any]]:
    taught = TEACHING_SETS.get(lang_key)
    if not taught:
        return {}
    index = _load_pack_index(lang_key)
    levels: dict[int, dict[str, Any]] = {}
    for level_num, words in taught.items():
        title = LEVEL_TITLES[level_num]
        items = []
        for word in words:
            meta = index.get(word) or {
                "word": word,
                "meaning": ASJP_MEANING.get(word, ""),
                "note": "",
                "source_ref": "",
            }
            if not meta.get("meaning"):
                continue
            items.append(meta)
        steps: list[dict[str, Any]] = []
        for item in items:
            steps.append(
                {
                    "type": "vocabulary",
                    "title": title,
                    "instruction": "Study this documented form and its gloss.",
                    "word": item["word"],
                    "meaning": item["meaning"],
                    "note": item.get("note") or item.get("source_ref") or "",
                }
            )
        steps.extend(_quiz_steps(items, title))
        if steps:
            levels[level_num] = {"steps": steps}
    return levels


def bookan_documentation_course() -> dict[int, dict[str, Any]]:
    """No invented Bookan lexicon — teach sourced documentation facts only."""
    facts = {
        1: [
            ("Bookan / Baukan Murut", "Names used for this Murutic language of Sabah",
             "ISO 639-3 bnb; Glottolog book1241. Wikipedia/Ethnologue list both names."),
            ("ISO 639-3", "bnb",
             "Standard language code for Bookan (Murut Bookan)."),
            ("Language family", "Austronesian, Murutic",
             "Described as a Murutic language of Sabah in published surveys."),
            ("Main district in surveys", "Keningau District, southwestern Sabah",
             "Kluge & Choi (2017) locate Bookan in Keningau District."),
            ("Community areas named in ELAR", "Keningau, Sook, Tulid, and Lanas",
             "ELAR collection DK0743 (Documentation of Murut Bookan)."),
            ("Speaker estimate cited in documentation", "about 2,400 or fewer (documentation reports)",
             "ELAR/Culture in Crisis project pages cite this estimate; treat as reported, not a census."),
        ],
        2: [
            ("SIL survey year", "2017",
             "Kluge & Choi, SIL Electronic Survey Reports 2017-008."),
            ("EGIDS in that survey", "Level 7 Shifting",
             "The 2017 SIL rapid-appraisal survey classified Bookan as EGIDS 7 Shifting."),
            ("Shift language named in the survey", "Sabah Malay",
             "The survey reports shift toward Sabah Malay, especially among children."),
            ("Who still uses Bookan (survey finding)", "The child-bearing generation among themselves; children often acquire Sabah Malay first",
             "Summarised from Kluge & Choi 2017; not a claim about every household."),
            ("Ethnologue free profile (undated web summary)", "Described as endangered; used as a first language by adults only (direct evidence lacking)",
             "Ethnologue Free profile for Murut, Bookan [bnb] — source-specific, not independently re-surveyed here."),
            ("School teaching (Ethnologue Free)", "Not known to be taught in schools",
             "Ethnologue Free profile statement; mark as source-specific."),
        ],
        3: [
            ("ELAR collection", "Documentation of Murut Bookan (DK0743)",
             "Endangered Languages Archive deposit of audio, video, transcription, and images."),
            ("ELDP project partner named in public pages", "Universiti Malaya",
             "Culture in Crisis / ELDP project page for Documentation of Murut, Bookan."),
            ("What the deposit contains", "Narratives, daily practices, songs, instrumental music, with Bookan transcription and Malay/English translation",
             "Described on the ELAR collection page; this course does not copy those wordlists."),
            ("Why lexicon is limited here", "No CC-licensed Bookan wordlist is bundled yet",
             "Dictionary entries are not invented. Review status stays Under Review for vocabulary."),
            ("Documentation goal (project page)", "Lexicon establishment and morphosyntactic analysis for community and researchers",
             "ELDP/Culture in Crisis summary of the 2023 documentation project."),
            ("Sentence-structure note on ELAR", "Preliminary public note mentions VSO; still under discussion",
             "ELAR English collection text flags this as preliminary — do not treat as a settled grammar rule."),
        ],
    }
    titles = {
        1: "First Meeting",
        2: "People Around You",
        3: "Everyday Encounters",
    }
    levels = {}
    for level_num, rows in facts.items():
        title = titles[level_num]
        items = [{"word": a, "meaning": b, "note": c} for a, b, c in rows]
        steps = []
        for item in items:
            steps.append(
                {
                    "type": "vocabulary",
                    "title": title,
                    "instruction": "Study this documented fact. It is not a Bookan lexicon entry.",
                    "word": item["word"],
                    "meaning": item["meaning"],
                    "note": item["note"] + " This lesson teaches documentation facts, not unverified Bookan words.",
                    "exclude_from_dictionary": True,
                }
            )
        # quizzes from facts — same items
        steps.extend(_quiz_steps(items, title))
        levels[level_num] = {"steps": steps}
    return levels


def all_extended_course_data() -> dict[str, dict[int, dict[str, Any]]]:
    data = {}
    for lang in TEACHING_SETS:
        data[lang] = course_from_teaching_set(lang)
    data["bookan"] = bookan_documentation_course()
    return data
