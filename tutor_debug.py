"""
Developer-only Deep RAG debug mode for the AI Tutor.

Does NOT change the normal tutoring pipeline. When enabled, exposes
planner / retrieval / validator / composer internals and diagnostic APIs.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from typing import Any, Optional

from db import get_db
from language_registry import display_name, get_language_keys


# #region agent log
_DEBUG_LOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "debug-31f19e.log"
)


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    try:
        payload = {
            "sessionId": "31f19e",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
            "runId": "debug-mode",
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass
# #endregion


def is_debug_enabled(request=None) -> bool:
    """Enable ONLY when DEBUG_TUTOR=true in the server environment.

    Query-string (?debug=1) and header (X-Debug-Tutor) alone must NOT unlock
    debug endpoints on a publicly reachable server — that was a production
    exposure risk. Callers in app.py must also require a logged-in session.
    """
    env = (os.getenv("DEBUG_TUTOR") or "").strip().lower()
    env_on = env in ("1", "true", "yes", "on")
    # #region agent log
    _agent_log(
        "A",
        "tutor_debug.py:is_debug_enabled",
        "debug_enable_check",
        {"enabled": env_on, "env": env_on, "query": False, "header": False},
    )
    # #endregion
    return env_on


def mask_secrets(value: Any) -> Any:
    """Recursively mask API keys / secrets without hiding prompt structure."""
    secret_re = re.compile(
        r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9_\-\.]+|"
        r"(?:api[_-]?key|openai[_-]?api[_-]?key)\s*[:=]\s*\S+)",
        re.I,
    )

    def _mask_str(s: str) -> str:
        return secret_re.sub("[REDACTED]", s)

    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if re.search(r"(api[_-]?key|secret|token|password|authorization)", str(k), re.I):
                out[k] = "[REDACTED]"
            else:
                out[k] = mask_secrets(v)
        return out
    if isinstance(value, list):
        return [mask_secrets(v) for v in value]
    if isinstance(value, str):
        return _mask_str(value)
    return value


def sql_has_language_filter(sql: str) -> bool:
    """True if SQL constrains by language (parameterized or literal)."""
    if not sql:
        return False
    text = sql.lower()
    patterns = (
        r"\blanguage\s*=\s*\?",
        r"\blanguage\s*=\s*['\"]",
        r"\blanguage\s+in\s*\(",
        r"\blanguage\s+in\s*\?",
        r"params=\[.*['\"]?[a-z\-]+['\"]?",  # coarse: params include lang keys
    )
    # Prefer explicit language column constraint
    if re.search(r"\blanguage\s*=\s*\?", text):
        return True
    if re.search(r"\blanguage\s*=\s*['\"][^'\"]+['\"]", text):
        return True
    if re.search(r"\blanguage\s+in\s*\(", text):
        return True
    # Database-wide analytics intentionally omit language filter
    if "group by language" in text or "count(*)" in text and "from vocabulary" in text:
        # still warn if single-language op expected — caller decides
        pass
    return bool(re.search(r"\blanguage\s*=", text))


def _row_language(row: dict, fallback: Optional[str] = None) -> Optional[str]:
    if not row:
        return fallback
    for key in ("language", "query_language", "lang"):
        val = row.get(key)
        if val:
            return str(val)
    return fallback


def _top_result(row: Optional[dict]) -> dict[str, Any]:
    if not row:
        return {}
    meaning = (
        row.get("meaning_en")
        or row.get("meaning")
        or row.get("title")
        or row.get("content")
        or row.get("explanation")
        or row.get("question")
    )
    return {
        "id": row.get("id"),
        "word": row.get("word"),
        "meaning": meaning,
        "example": row.get("example_sentence") or row.get("examples"),
        "title": row.get("title"),
    }


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def print_retrieval_log(
    language: str,
    table: str,
    sql: str,
    rows: int,
    top_row_id: Any,
) -> None:
    """Console SQL logging for every retrieval hit."""
    print("\n========== TUTOR RETRIEVAL ==========")
    print(f"Language:\n{display_name(language) if language else language or 'unknown'}")
    print(f"\nTable:\n{table}")
    print(f"\nSQL\n\n{sql}")
    print(f"\nRows\n\n{rows}")
    print(f"\nTop Row\n\nID {top_row_id if top_row_id is not None else 'n/a'}")
    print("=====================================\n")


def print_duplicate_warning(lang_a: str, lang_b: str, sample: dict) -> None:
    word = sample.get("word") or sample.get("example") or "(empty)"
    print("\nWARNING")
    print("Possible duplicated database entries.\n")
    print(display_name(lang_a) if lang_a else lang_a)
    print("-> shares")
    print(word)
    print()
    print(display_name(lang_b) if lang_b else lang_b)
    print("-> shares")
    print(word)
    print()


def print_missing_language_filter_warning(sql: str) -> None:
    print("\nWARNING")
    print("Language filter missing.\n")
    print(sql)
    print()


def detect_cross_language_duplicates(
    hits: list, *, log_print: bool = False
) -> list[dict[str, Any]]:
    """
    After retrieval, compare word/meaning/example across languages.
    Returns warning objects (does not alter answers).
    """
    # language -> list of (word, meaning, example) fingerprints from vocab-like rows
    by_lang: dict[str, list[dict]] = defaultdict(list)
    for hit in hits or []:
        rows = getattr(hit, "rows", None) or (hit.get("rows") if isinstance(hit, dict) else [])
        table = getattr(hit, "table", None) or (hit.get("table") if isinstance(hit, dict) else "")
        if table and table != "vocabulary":
            continue
        for row in rows or []:
            lang = _row_language(row)
            if not lang:
                continue
            # Prefer canonical language key when query_language is display name
            canon = row.get("language") or lang
            fp = {
                "word": row.get("word"),
                "meaning": row.get("meaning_en") or row.get("meaning"),
                "example": row.get("example_sentence"),
                "id": row.get("id"),
            }
            if not fp["word"] and not fp["meaning"] and not fp["example"]:
                continue
            by_lang[str(canon)].append(fp)

    warnings: list[dict[str, Any]] = []
    langs = sorted(by_lang.keys())
    for i, la in enumerate(langs):
        set_a = {
            (_norm(r["word"]), _norm(r["meaning"]), _norm(r["example"])): r
            for r in by_lang[la]
            if _norm(r["word"]) or _norm(r["meaning"]) or _norm(r["example"])
        }
        for lb in langs[i + 1 :]:
            for r in by_lang[lb]:
                key = (_norm(r["word"]), _norm(r["meaning"]), _norm(r["example"]))
                if key == ("", "", ""):
                    continue
                if key in set_a:
                    sample = set_a[key]
                    warning = {
                        "type": "cross_language_duplicate",
                        "languages": [la, lb],
                        "word": sample.get("word"),
                        "meaning": sample.get("meaning"),
                        "example": sample.get("example"),
                        "ids": [sample.get("id"), r.get("id")],
                        "message": (
                            "Possible duplicated database entries between "
                            f"{display_name(la)} and {display_name(lb)}."
                        ),
                    }
                    warnings.append(warning)
                    if log_print:
                        print_duplicate_warning(la, lb, sample)
    return warnings


def build_retrieval_debug(bundle, plan=None, *, log_print: bool = False) -> dict[str, Any]:
    """Build retrieval[] debug entries + warnings from an EvidenceBundle."""
    retrieval: list[dict[str, Any]] = []
    filter_warnings: list[dict[str, Any]] = []
    hits = getattr(bundle, "hits", None) or []

    for hit in hits:
        rows = hit.rows or []
        top = rows[0] if rows else None
        intended_lang = None
        if plan is not None:
            for op in getattr(plan, "operations", None) or []:
                if getattr(op, "name", None) == hit.name:
                    intended_lang = (getattr(op, "params", None) or {}).get("language")
                    if intended_lang:
                        break
            if not intended_lang:
                intended_lang = getattr(plan, "language", None)

        row_lang = None
        if top:
            row_lang = top.get("language") or top.get("query_language")

        # Prefer planned/op language so missing filters don't mislabel the hit
        lang = intended_lang or row_lang
        if not lang and plan is not None:
            lang = getattr(plan, "language", None)

        top_res = _top_result(top)
        entry = {
            "language": lang or "unknown",
            "table": hit.table,
            "sql": hit.sql,
            "rows": len(rows),
            "top_result": {
                "word": top_res.get("word"),
                "meaning": top_res.get("meaning"),
            },
            "top_row_id": top_res.get("id"),
            "operation": hit.name,
            "row_language": row_lang,
        }
        # Include example in top_result when present (extra, harmless)
        if top_res.get("example"):
            entry["top_result"]["example"] = top_res["example"]
        retrieval.append(entry)

        if log_print:
            print_retrieval_log(
                language=str(lang or "unknown"),
                table=hit.table,
                sql=hit.sql,
                rows=len(rows),
                top_row_id=top_res.get("id"),
            )

        # Missing language filter — skip intentionally DB-wide ops
        op_name = (hit.name or "").lower()
        db_wide = any(
            x in op_name
            for x in ("all_languages", "vocab_size_all", "compare_all", "rank_all")
        )
        if not db_wide and not sql_has_language_filter(hit.sql):
            warn = {
                "type": "language_filter_missing",
                "operation": hit.name,
                "table": hit.table,
                "sql": hit.sql,
                "message": "Language filter missing.",
            }
            filter_warnings.append(warn)
            if log_print:
                print_missing_language_filter_warning(hit.sql)

    dup_warnings = (
        detect_cross_language_duplicates(hits, log_print=log_print) if hits else []
    )
    return {
        "retrieval": retrieval,
        "warnings": filter_warnings + dup_warnings,
    }


def build_debug_payload(
    *,
    plan=None,
    bundle=None,
    validation=None,
    entity_check=None,
    composer_meta: Optional[dict] = None,
    composer_received: Optional[dict] = None,
    log_print: bool = False,
) -> dict[str, Any]:
    """Assemble the client-facing debug object."""
    composer_meta = composer_meta or {}
    entity_check = entity_check

    planner = {}
    if plan is not None:
        planner = {
            "intent": getattr(plan, "intent", None),
            "languages_detected": [
                display_name(e) for e in (getattr(plan, "entities", None) or [])
            ],
            "requested_entities": list(getattr(plan, "entities", None) or []),
            "operations": [
                {
                    "name": getattr(op, "name", None),
                    "table": getattr(op, "table", None),
                    "kind": getattr(op, "kind", None),
                    "language": (getattr(op, "params", None) or {}).get("language"),
                    "required": getattr(op, "required", True),
                }
                for op in (getattr(plan, "operations", None) or [])
            ],
            "scope": getattr(plan, "scope", None),
            "confidence": getattr(plan, "confidence", None),
            "response_type": getattr(plan, "response_type", None),
            "query_spec": getattr(plan, "query_spec", None) or {},
            "knowledge_policy": getattr(plan, "knowledge_policy", None),
        }

    ret = build_retrieval_debug(bundle, plan, log_print=log_print) if bundle else {
        "retrieval": [],
        "warnings": [],
    }

    coverage_percent = None
    missing_languages: list = []
    grounded = True
    if entity_check is not None:
        coverage_percent = getattr(entity_check, "coverage_percent", None)
        if coverage_percent is None and isinstance(entity_check, dict):
            coverage_percent = entity_check.get("coverage_percent")
        missing_languages = list(
            getattr(entity_check, "missing_languages", None)
            or (entity_check.get("missing_languages") if isinstance(entity_check, dict) else [])
            or []
        )
        ok = getattr(entity_check, "ok", None)
        if ok is None and isinstance(entity_check, dict):
            ok = entity_check.get("ok")
        grounded = bool(ok) if ok is not None else True
    if validation is not None:
        v_ok = getattr(validation, "ok", True)
        grounded = grounded and bool(v_ok)

    if coverage_percent is None:
        coverage_percent = 100 if grounded else 0

    validator = {
        "coverage_percent": coverage_percent,
        "missing_languages": missing_languages,
        "grounded": grounded,
        "evidence_ok": getattr(validation, "ok", None) if validation is not None else None,
        "evidence_reason": getattr(validation, "reason", None) if validation is not None else None,
    }

    sections = composer_meta.get("composer_sections_generated") or composer_meta.get("sections") or []
    composer = {
        "used": bool(composer_meta.get("invoked")),
        "fallback": bool(composer_meta.get("fallback_used", True)),
        "tokens": composer_meta.get("tokens_estimate"),
        "latency_ms": composer_meta.get("latency_ms"),
        "sections": sections,
        "mode": composer_meta.get("composer_mode"),
        "reason": composer_meta.get("reason") or composer_meta.get("composer_reason"),
    }

    # Composer diagnostics: exactly what composer received (secrets masked)
    received = composer_received
    if received is None and plan is not None and bundle is not None and validation is not None:
        try:
            from composer import build_composer_payload

            received = build_composer_payload(
                user_question="(see request)",
                plan=plan,
                bundle=bundle,
                validation=validation,
            )
        except Exception as exc:
            received = {"error": f"could_not_build_composer_payload: {exc}"}

    if received is not None:
        composer["received"] = mask_secrets(received)
        # Pretty print for console when logging
        if log_print:
            print("\n========== COMPOSER DIAGNOSTICS ==========")
            print("Planner\n")
            print(json.dumps(mask_secrets(planner), indent=2, ensure_ascii=False, default=str))
            print("\nRetrieved Facts\n")
            facts = (received or {}).get("retrieved_facts") if isinstance(received, dict) else received
            print(json.dumps(mask_secrets(facts), indent=2, ensure_ascii=False, default=str)[:4000])
            print("\nValidation\n")
            print(json.dumps(mask_secrets(validator), indent=2, ensure_ascii=False, default=str))
            print("==========================================\n")

    debug = {
        "planner": planner,
        "retrieval": ret["retrieval"],
        "validator": validator,
        "composer": composer,
        "warnings": ret["warnings"],
    }

    # #region agent log
    _agent_log(
        "A",
        "tutor_debug.py:build_debug_payload",
        "debug_payload_built",
        {
            "intent": planner.get("intent"),
            "ops": len(planner.get("operations") or []),
            "retrieval_n": len(ret["retrieval"]),
            "warnings_n": len(ret["warnings"]),
            "composer_used": composer.get("used"),
            "coverage": coverage_percent,
        },
    )
    # #endregion

    return debug


# ---------------------------------------------------------------------------
# Diagnostic endpoints
# ---------------------------------------------------------------------------

def database_diagnostics() -> dict[str, Any]:
    """Per-language counts + longest word / id."""
    conn = get_db()
    keys = get_language_keys()
    languages = []
    for key in keys:
        vocab = conn.execute(
            "SELECT COUNT(*) AS c FROM vocabulary WHERE language = ?", (key,)
        ).fetchone()["c"]
        grammar = conn.execute(
            "SELECT COUNT(*) AS c FROM grammar WHERE language = ?", (key,)
        ).fetchone()["c"]
        culture = conn.execute(
            "SELECT COUNT(*) AS c FROM culture WHERE language = ?", (key,)
        ).fetchone()["c"]
        quiz = conn.execute(
            "SELECT COUNT(*) AS c FROM quiz WHERE language = ?", (key,)
        ).fetchone()["c"]
        longest = conn.execute(
            """
            SELECT id, word, meaning_en,
                   LENGTH(REPLACE(word, ' ', '')) AS word_len
            FROM vocabulary
            WHERE language = ?
            ORDER BY word_len DESC, word ASC
            LIMIT 1
            """,
            (key,),
        ).fetchone()
        entry = {
            "language": key,
            "display_name": display_name(key),
            "vocabulary": vocab,
            "grammar": grammar,
            "culture": culture,
            "quiz": quiz,
            "longest_word": longest["word"] if longest else None,
            "longest_word_id": longest["id"] if longest else None,
            "longest_word_len": longest["word_len"] if longest else None,
            "longest_meaning": longest["meaning_en"] if longest else None,
        }
        languages.append(entry)

    # #region agent log
    _agent_log(
        "E",
        "tutor_debug.py:database_diagnostics",
        "db_diag",
        {
            "languages": [
                {"k": L["language"], "v": L["vocabulary"], "longest_id": L["longest_word_id"]}
                for L in languages
            ]
        },
    )
    # #endregion

    return {"languages": languages}


def find_duplicates() -> dict[str, Any]:
    """Duplicate vocabulary / examples / meanings / cross-language / copy-paste."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, language, word, meaning_en, example_sentence, lesson_id
        FROM vocabulary
        ORDER BY language, id
        """
    ).fetchall()
    items = [dict(r) for r in rows]

    # Within-language duplicate words
    by_lang_word: dict[tuple, list] = defaultdict(list)
    by_lang_meaning: dict[tuple, list] = defaultdict(list)
    by_lang_example: dict[tuple, list] = defaultdict(list)
    cross_fp: dict[tuple, list] = defaultdict(list)

    for r in items:
        w, m, e = _norm(r["word"]), _norm(r["meaning_en"]), _norm(r["example_sentence"])
        if w:
            by_lang_word[(r["language"], w)].append(r["id"])
        if m:
            by_lang_meaning[(r["language"], m)].append(r["id"])
        if e:
            by_lang_example[(r["language"], e)].append(r["id"])
        if w or m or e:
            cross_fp[(w, m, e)].append(
                {"id": r["id"], "language": r["language"], "word": r["word"]}
            )

    duplicate_vocabulary = [
        {"language": lang, "word": word, "ids": ids}
        for (lang, word), ids in by_lang_word.items()
        if len(ids) > 1
    ]
    duplicate_meanings = [
        {"language": lang, "meaning": meaning, "ids": ids}
        for (lang, meaning), ids in by_lang_meaning.items()
        if len(ids) > 1
    ]
    duplicate_examples = [
        {"language": lang, "example": example, "ids": ids}
        for (lang, example), ids in by_lang_example.items()
        if len(ids) > 1
    ]
    cross_language_duplicates = []
    possible_copy_paste = []
    for fp, locs in cross_fp.items():
        langs = {x["language"] for x in locs}
        if len(langs) > 1 and (fp[0] or fp[1] or fp[2]):
            entry = {
                "word": fp[0],
                "meaning": fp[1],
                "example": fp[2],
                "languages": sorted(langs),
                "ids": [x["id"] for x in locs],
                "entries": locs,
            }
            cross_language_duplicates.append(entry)
            # Same word+meaning+example across langs ⇒ likely copy-paste
            if fp[0] and fp[1]:
                possible_copy_paste.append(entry)

    result = {
        "duplicate_vocabulary": duplicate_vocabulary,
        "duplicate_examples": duplicate_examples,
        "duplicate_meanings": duplicate_meanings,
        "cross_language_duplicates": cross_language_duplicates,
        "possible_copy_paste_errors": possible_copy_paste,
        "summary": {
            "duplicate_vocabulary": len(duplicate_vocabulary),
            "duplicate_examples": len(duplicate_examples),
            "duplicate_meanings": len(duplicate_meanings),
            "cross_language_duplicates": len(cross_language_duplicates),
            "possible_copy_paste_errors": len(possible_copy_paste),
        },
    }

    # #region agent log
    _agent_log(
        "C",
        "tutor_debug.py:find_duplicates",
        "duplicates_found",
        result["summary"],
    )
    # #endregion

    return result


def run_selfcheck(answer_fn) -> dict[str, Any]:
    """
    One-click verification suite.
    answer_fn(message, lang_key=None) -> result dict from answer_tutor_query
    """
    tests_spec = [
        {
            "name": "Longest Mah Meri",
            "message": "What is the longest word in Mah Meri?",
            "lang_key": "mah-meri",
            "expect": "longest_single",
            "entity": "mah-meri",
        },
        {
            "name": "Longest Bidayuh",
            "message": "What is the longest word in Bidayuh?",
            "lang_key": "bidayuh",
            "expect": "longest_single",
            "entity": "bidayuh",
        },
        {
            "name": "Longest Kadazan",
            "message": "What is the longest word in Kadazan?",
            "lang_key": "kadazan-dusun",
            "expect": "longest_single",
            "entity": "kadazan-dusun",
        },
        {
            "name": "Compare Mah Meri and Bidayuh",
            "message": "Compare the longest words in Mah Meri and Bidayuh",
            "lang_key": None,
            "expect": "compare_two",
            "entities": ["mah-meri", "bidayuh"],
        },
        {
            "name": "Compare Mah Meri and Kadazan",
            "message": "Compare the longest words in Mah Meri and Kadazan",
            "lang_key": None,
            "expect": "compare_two",
            "entities": ["mah-meri", "kadazan-dusun"],
        },
        {
            "name": "Top 10 Mah Meri",
            "message": "Top 10 longest words in Mah Meri",
            "lang_key": "mah-meri",
            "expect": "top_n",
            "entity": "mah-meri",
            "min_rows": 1,
        },
        {
            "name": "Top 10 Bidayuh",
            "message": "Top 10 longest words in Bidayuh",
            "lang_key": "bidayuh",
            "expect": "top_n",
            "entity": "bidayuh",
            "min_rows": 1,
        },
        {
            "name": "Vocabulary counts",
            "message": "What is the vocabulary size of all supported languages?",
            "lang_key": None,
            "expect": "vocab_counts",
        },
        {
            "name": "Greeting counts",
            "message": "How many greetings in Mah Meri?",
            "lang_key": "mah-meri",
            "expect": "greeting_count",
            "entity": "mah-meri",
        },
    ]

    results = []
    for spec in tests_spec:
        started = time.time()
        try:
            out = answer_fn(spec["message"], lang_key=spec.get("lang_key"))
        except Exception as exc:
            results.append(
                {
                    "name": spec["name"],
                    "status": "FAIL",
                    "detail": f"exception: {exc}",
                    "latency_ms": int((time.time() - started) * 1000),
                }
            )
            continue

        status = (out or {}).get("status")
        audit = (out or {}).get("audit") or {}
        extra = audit.get("extra") or {}
        debug_trace = (out or {}).get("debug_trace") or {}
        retrieval = debug_trace.get("retrieval") or []
        warnings = debug_trace.get("warnings") or []
        reply = (out or {}).get("reply") or ""

        passed = False
        detail = ""
        filter_missing = any(
            w.get("type") == "language_filter_missing" for w in warnings
        )
        sql_ok = all(
            sql_has_language_filter(r.get("sql") or "")
            for r in retrieval
            if r.get("sql")
        ) if retrieval else False

        if spec["expect"] == "longest_single":
            entity = spec.get("entity")
            has_row = any(r.get("rows", 0) > 0 for r in retrieval) or (
                audit.get("rows_returned") or 0
            ) > 0
            top_word = None
            row_lang = None
            for r in retrieval:
                tr = r.get("top_result") or {}
                if tr.get("word"):
                    top_word = tr["word"]
                    row_lang = r.get("row_language") or r.get("language")
                    break
            lang_match = True
            if entity and row_lang:
                lang_match = (
                    _norm(row_lang) == _norm(entity)
                    or _norm(row_lang) == _norm(display_name(entity))
                )
            passed = (
                status == "ok"
                and has_row
                and bool(top_word or reply)
                and sql_ok
                and not filter_missing
                and lang_match
            )
            detail = (
                f"status={status} rows={audit.get('rows_returned')} "
                f"top_word={top_word!r} row_lang={row_lang!r} sql_ok={sql_ok}"
            )

        elif spec["expect"] == "compare_two":
            entities = spec.get("entities") or []
            requested = extra.get("requested_languages") or entities
            retrieved = extra.get("retrieved_languages") or []
            if status == "incomplete_entities":
                passed = True
                detail = f"refused partial: missing={extra.get('missing_languages')}"
            else:
                ret_langs = {
                    str(r.get("language") or "").lower() for r in retrieval
                }
                entity_ok = all(
                    e in ret_langs or display_name(e).lower() in ret_langs
                    for e in entities
                )
                tops = [
                    (
                        r.get("language"),
                        (r.get("top_result") or {}).get("word"),
                        r.get("row_language"),
                    )
                    for r in retrieval
                    if (r.get("top_result") or {}).get("word")
                ]
                # Each hit's DB row language must match the intended language
                scoped = all(
                    t[2]
                    and (
                        _norm(t[2]) == _norm(t[0])
                        or _norm(t[2]) == _norm(display_name(t[0]))
                    )
                    for t in tops
                ) if tops else False
                passed = (
                    status == "ok"
                    and entity_ok
                    and bool(reply)
                    and sql_ok
                    and not filter_missing
                    and scoped
                )
                detail = (
                    f"status={status} requested={requested} "
                    f"retrieved={retrieved} ret_langs={sorted(ret_langs)} "
                    f"sql_ok={sql_ok} scoped={scoped} tops={tops}"
                )

        elif spec["expect"] == "top_n":
            rows = audit.get("rows_returned") or 0
            min_rows = spec.get("min_rows", 1)
            entity = spec.get("entity")
            scoped = True
            if entity:
                for r in retrieval:
                    rl = r.get("row_language")
                    if rl and _norm(rl) not in {_norm(entity), _norm(display_name(entity))}:
                        scoped = False
            passed = (
                status == "ok"
                and rows >= min_rows
                and bool(reply)
                and sql_ok
                and not filter_missing
                and scoped
            )
            detail = f"status={status} rows={rows} sql_ok={sql_ok} scoped={scoped}"

        elif spec["expect"] == "vocab_counts":
            rows = audit.get("rows_returned") or 0
            # Counts must differ per language or at least each SQL be language-scoped
            passed = (
                status == "ok"
                and rows >= 1
                and bool(reply)
                and sql_ok
                and not filter_missing
            )
            detail = f"status={status} rows={rows} sql_ok={sql_ok}"

        elif spec["expect"] == "greeting_count":
            rows = audit.get("rows_returned") or 0
            passed = (
                status == "ok"
                and rows >= 1
                and bool(reply)
                and sql_ok
                and not filter_missing
            )
            detail = f"status={status} rows={rows} sql_ok={sql_ok}"

        else:
            passed = status == "ok" and not filter_missing
            detail = f"status={status}"

        if filter_missing:
            detail += " | FAIL: language filter missing"

        results.append(
            {
                "name": spec["name"],
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
                "pipeline_status": status,
                "warnings": warnings,
                "latency_ms": int((time.time() - started) * 1000),
            }
        )

    passed_n = sum(1 for r in results if r["status"] == "PASS")
    failed_n = sum(1 for r in results if r["status"] == "FAIL")
    summary = {
        "passed": passed_n,
        "failed": failed_n,
        "total": len(results),
        "overall": "PASS" if failed_n == 0 else "FAIL",
    }

    # #region agent log
    _agent_log(
        "E",
        "tutor_debug.py:run_selfcheck",
        "selfcheck_done",
        {"summary": summary, "tests": [{"n": r["name"], "s": r["status"]} for r in results]},
    )
    # #endregion

    return {"tests": results, "summary": summary}
