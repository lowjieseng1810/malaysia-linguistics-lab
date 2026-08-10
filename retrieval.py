"""
Retriever stage: execute planned SQLite operations (multi-table + analytics).
Never calls the LLM.

Language is NEVER optional. Every SQL must constrain by target_language.
search_all means all lessons for that language — never all languages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from db import get_db
from word_length import (
    COMPLETE_SCAN_NOTE,
    normalized_word_length,
    rank_rows_by_word_length,
)

if TYPE_CHECKING:
    from planner import TutorPlan, RetrievalOp


class RetrievalError(ValueError):
    """Raised when retrieval cannot safely scope SQL to a target language."""


def topic_terms(message: str) -> list[str]:
    stop = {
        "tell", "me", "about", "the", "a", "an", "what", "is", "are", "please",
        "can", "you", "explain", "today", "lesson", "this", "that", "related",
        "to", "give", "show", "some", "any", "how", "does", "do", "for", "with",
        "from", "your", "our", "and", "or", "in", "on", "of", "it", "its",
        "translate", "translation", "meaning", "means", "mean", "say", "word",
        "words", "find", "search", "look", "lookup", "who",
    }
    terms = []
    for word in re.findall(r"[a-zA-Z]{2,}", (message or "").lower()):
        if word not in stop and word not in terms:
            terms.append(word)
    return terms


def wants_all_lessons(message: str) -> bool:
    return bool(
        re.search(
            r"\b(all\s+lessons?|every\s+lesson|whole\s+course|across\s+lessons?)\b",
            message or "",
            re.I,
        )
    )


def build_language_filter(language: Optional[str]) -> tuple[str, list[Any]]:
    """
    Mandatory language constraint for every retrieval query.

    Returns ("WHERE language = ?", [language]).
    Raises RetrievalError if language is missing.
    """
    if language is None or not str(language).strip():
        raise RetrievalError("Language filter missing.")
    return "WHERE language = ?", [str(language).strip()]


def _sql_has_language_constraint(sql: str) -> bool:
    text = " ".join((sql or "").lower().split())
    if re.search(r"\blanguage\s*=\s*\?", text):
        return True
    if re.search(r"\blanguage\s*=\s*['\"][^'\"]+['\"]", text):
        return True
    if re.search(r"\blanguage\s+in\s*\(", text):
        return True
    return False


def _assert_executable_sql(sql: str, language: str) -> None:
    """Abort before execution if language is missing from SQL."""
    if language is None or not str(language).strip():
        raise RetrievalError("Language filter missing.")
    if not _sql_has_language_constraint(sql):
        raise RetrievalError("Language filter missing.")


def _scope_clause(
    language: Optional[str],
    lesson_id: Optional[int],
    search_all: bool,
) -> tuple[str, list[Any]]:
    """
    Build WHERE clause. Language is always required.

    search_all=True  → all lessons for this language (no lesson_id filter)
    search_all=False → language + optional lesson_id
    """
    where, params = build_language_filter(language)
    if not search_all and lesson_id is not None:
        where = where + " AND lesson_id = ?"
        params = list(params) + [lesson_id]
    return where, params


def _resolve_target_language(
    op: "RetrievalOp",
    plan_language: Optional[str],
) -> str:
    p = op.params or {}
    if "language" in p and p.get("language") is not None:
        language = p.get("language")
    else:
        language = plan_language
    if language is None or not str(language).strip():
        raise RetrievalError("Language filter missing.")
    return str(language).strip()


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]


def _format_sql(sql: str, params: list[Any]) -> str:
    compact = " ".join(sql.split())
    return f"{compact} | params={list(params)}"


def _safe_run(
    sql: str,
    params: list[Any],
    language: str,
    *,
    fetch_one: bool = False,
) -> list[dict]:
    _assert_executable_sql(sql, language)
    return _run_query(sql, params, fetch_one=fetch_one)


@dataclass
class QueryHit:
    name: str
    table: str
    sql: str
    rows: list[dict] = field(default_factory=list)
    required: bool = True


@dataclass
class EvidenceBundle:
    intent: str
    language: Optional[str]
    lesson_id: Optional[int]
    tables: list[str]
    hits: list[QueryHit] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    by_name: dict[str, list[dict]] = field(default_factory=dict)
    require_topic_match: bool = False
    notes: list[str] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)

    @property
    def sql_statements(self) -> list[str]:
        return [hit.sql for hit in self.hits]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def rows_for(self, name: str) -> list[dict]:
        return list(self.by_name.get(name) or [])


def _run_query(sql: str, params: list[Any], fetch_one: bool = False) -> list[dict]:
    conn = get_db()
    try:
        if fetch_one:
            row = conn.execute(sql, params).fetchone()
            return [dict(row)] if row else []
        rows = conn.execute(sql, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def _apply_filters(
    where: str,
    params: list[Any],
    filters: list[dict[str, Any]],
) -> tuple[str, list[Any]]:
    """Append compositional filters to a language-scoped WHERE clause."""
    where2 = where
    params2 = list(params)
    for f in filters or []:
        field = (f.get("field") or "").strip()
        op = (f.get("op") or "=").strip()
        value = f.get("value")
        if field == "word_length":
            # Length filters are applied in Python after a complete vocabulary
            # scan (see rank_rows_by_word_length). Skip SQL-side LENGTH here so
            # punctuation-normalized lengths stay consistent.
            continue
        elif field == "part_of_speech":
            if op == "!=":
                where2 += " AND LOWER(COALESCE(part_of_speech, '')) != ?"
                params2.append(str(value).lower())
            else:
                where2 += " AND part_of_speech = ?"
                params2.append(value)
        elif field == "word" and op == "starts_with":
            where2 += " AND LOWER(word) LIKE ?"
            params2.append(f"{str(value).lower()}%")
        elif field == "word" and op == "ends_with":
            where2 += " AND LOWER(word) LIKE ?"
            params2.append(f"%{str(value).lower()}")
        elif field == "word" and op == "contains":
            where2 += " AND LOWER(word) LIKE ?"
            params2.append(f"%{str(value).lower()}%")
        elif field == "difficulty":
            where2 += " AND difficulty = ?"
            params2.append(value)
    return where2, params2


def _compile_universal_query(
    *,
    language: str,
    lesson_id: Optional[int],
    search_all: bool,
    params: dict[str, Any],
    op_name: str,
    required: bool,
) -> QueryHit:
    """
    Compile a compositional QueryStructure into language-scoped SQL.

    Never bypasses WHERE language=?.
    """
    table = (params.get("table") or "vocabulary").strip()
    if table not in ("vocabulary", "grammar", "culture", "quiz"):
        table = "vocabulary"

    operation = (params.get("operation") or "retrieve").strip()
    metric = params.get("metric")
    aggregation = params.get("aggregation")
    order = (params.get("order") or "").strip().lower()
    limit = int(params.get("limit") or 12)
    offset = int(params.get("offset") or 0)
    filters = list(params.get("filters") or [])
    meanings = list(params.get("meanings") or [])
    pos = params.get("part_of_speech")

    if pos and not any(f.get("field") == "part_of_speech" for f in filters):
        filters.append({"field": "part_of_speech", "op": "=", "value": pos})

    where, base_params = _scope_clause(language, lesson_id, search_all)
    where, base_params = _apply_filters(where, base_params, filters)
    lang_label = language

    # Meaning / topic search (vocabulary)
    if meanings and table == "vocabulary" and operation in ("retrieve", "filter", "search"):
        where2 = where
        run_params: list[Any] = [lang_label] + list(base_params)
        clauses = []
        for meaning in meanings[:15]:
            like = f"%{meaning}%"
            clauses.append(
                "(LOWER(meaning_en) LIKE ? OR LOWER(meaning_ms) LIKE ? "
                "OR LOWER(word) LIKE ? OR LOWER(meaning_zh) LIKE ?)"
            )
            run_params.extend([like.lower(), like.lower(), like.lower(), like.lower()])
        where2 = where + " AND (" + " OR ".join(clauses) + ")"
        run_params.append(limit)
        sql = f"""
            SELECT *, ? AS query_language FROM vocabulary
            {where2}
            ORDER BY LENGTH(word) ASC, word ASC
            LIMIT ?
        """
        return QueryHit(
            op_name, table, _format_sql(sql, run_params),
            _safe_run(sql, run_params, language), required,
        )

    # Topic search (culture)
    if meanings and table == "culture":
        where2 = where
        run_params = [lang_label] + list(base_params)
        clauses = []
        for meaning in meanings[:6]:
            like = f"%{meaning}%"
            clauses.append(
                "(LOWER(title) LIKE ? OR LOWER(content) LIKE ? OR LOWER(references_text) LIKE ?)"
            )
            run_params.extend([like.lower(), like.lower(), like.lower()])
        if clauses:
            where2 = where + " AND (" + " OR ".join(clauses) + ")"
        run_params.append(limit)
        sql = f"""
            SELECT *, ? AS query_language FROM culture
            {where2}
            ORDER BY id ASC
            LIMIT ?
        """
        return QueryHit(
            op_name, "culture", _format_sql(sql, run_params),
            _safe_run(sql, run_params, language), required,
        )

    # COUNT aggregation (complete language-scoped set; length filters via Python)
    if operation == "count" or aggregation == "count":
        length_filters = [f for f in filters if f.get("field") == "word_length"]
        if length_filters and table == "vocabulary":
            sql = f"""
                SELECT *, ? AS query_language
                FROM vocabulary
                {where}
            """
            params2 = [lang_label] + list(base_params)
            all_rows = _safe_run(sql, params2, language)
            matched = rank_rows_by_word_length(
                all_rows,
                descending=True,
                limit=max(len(all_rows), 1),
                offset=0,
                length_filters=length_filters,
            )
            audit = (
                f"{_format_sql(sql, params2)} "
                f"| {COMPLETE_SCAN_NOTE} scanned={len(all_rows)} matched={len(matched)}"
            )
            return QueryHit(
                op_name,
                "vocabulary",
                audit,
                [{"count": len(matched), "query_language": lang_label}],
                required,
            )
        sql = f"SELECT COUNT(*) AS count, ? AS query_language FROM {table} {where}"
        params2 = [lang_label] + list(base_params)
        return QueryHit(
            op_name, table, _format_sql(sql, params2),
            _safe_run(sql, params2, language), required,
        )

    # Frequency / distribution by part of speech
    if aggregation == "frequency" or metric == "part_of_speech":
        sql = f"""
            SELECT part_of_speech, COUNT(*) AS count, ? AS query_language
            FROM vocabulary
            {where}
            GROUP BY part_of_speech
            ORDER BY count DESC, part_of_speech ASC
            LIMIT ?
        """
        params2 = [lang_label] + list(base_params) + [limit]
        return QueryHit(
            op_name, "vocabulary", _format_sql(sql, params2),
            _safe_run(sql, params2, language), required,
        )

    # Random sample
    if aggregation == "random" or order == "random":
        sql = f"""
            SELECT *, ? AS query_language FROM vocabulary
            {where}
            ORDER BY RANDOM()
            LIMIT ?
        """
        params2 = [lang_label] + list(base_params) + [max(1, limit)]
        return QueryHit(
            op_name, "vocabulary", _format_sql(sql, params2),
            _safe_run(sql, params2, language), required,
        )

    # Alphabetical listing
    if order == "alpha":
        sql = f"""
            SELECT *, ? AS query_language FROM vocabulary
            {where}
            ORDER BY LOWER(word) ASC
            LIMIT ?
        """
        params2 = [lang_label] + list(base_params) + [limit]
        return QueryHit(
            op_name, "vocabulary", _format_sql(sql, params2),
            _safe_run(sql, params2, language), required,
        )

    # AVG / median / max / min / rank by word length — ALWAYS scan the complete
    # language-scoped vocabulary set, then rank with normalized_word_length.
    # Never answer these from a top-k meaning/semantic LIMIT slice.
    # Do NOT divert difficulty/POS ranking into this path.
    length_filters = [f for f in filters if f.get("field") == "word_length"]
    field_hint = params.get("field")
    wants_length_analytics = table == "vocabulary" and aggregation != "count" and (
        metric == "word_length"
        or field_hint == "word_length"
        or bool(length_filters)
        or (
            aggregation in ("max", "min", "avg", "median")
            and metric in (None, "word_length")
            and field_hint in (None, "word_length")
        )
        or (
            aggregation == "rank"
            and metric in (None, "word_length")
            and field_hint in (None, "word_length")
            and (order in ("asc", "desc") or bool(length_filters))
        )
    )
    if wants_length_analytics:
        sql = f"""
            SELECT *, ? AS query_language
            FROM vocabulary
            {where}
        """
        params2 = [lang_label] + list(base_params)
        all_rows = _safe_run(sql, params2, language)
        audit_sql = (
            f"{_format_sql(sql, params2)} "
            f"| {COMPLETE_SCAN_NOTE} scanned={len(all_rows)}"
        )

        if aggregation == "avg":
            lengths = [normalized_word_length(r.get("word") or "") for r in all_rows]
            avg = (sum(lengths) / len(lengths)) if lengths else 0.0
            result = [{
                "avg_length": avg,
                "count": len(lengths),
                "query_language": lang_label,
            }]
            return QueryHit(op_name, "vocabulary", audit_sql, result, required)

        if aggregation == "median":
            lengths = sorted(
                normalized_word_length(r.get("word") or "") for r in all_rows
            )
            if not lengths:
                med = None
            elif len(lengths) % 2:
                med = float(lengths[len(lengths) // 2])
            else:
                mid = len(lengths) // 2
                med = (lengths[mid - 1] + lengths[mid]) / 2.0
            result = [{
                "median_length": med,
                "count": len(lengths),
                "query_language": lang_label,
            }]
            return QueryHit(op_name, "vocabulary", audit_sql, result, required)

        descending = True
        if aggregation == "min" or order == "asc":
            descending = False
        if aggregation == "max" or order == "desc":
            descending = True

        ranked = rank_rows_by_word_length(
            all_rows,
            descending=descending,
            limit=max(1, int(limit or 1)),
            offset=max(0, int(offset or 0)),
            length_filters=length_filters,
        )
        return QueryHit(op_name, "vocabulary", audit_sql, ranked, required)

    # Difficulty ranking
    if metric == "difficulty":
        sql = f"""
            SELECT *, ? AS query_language FROM vocabulary
            {where}
            ORDER BY
                CASE difficulty WHEN 'hard' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                LENGTH(REPLACE(word, ' ', '')) DESC
            LIMIT ?
        """
        params2 = [lang_label] + list(base_params) + [limit]
        return QueryHit(
            op_name, "vocabulary", _format_sql(sql, params2),
            _safe_run(sql, params2, language), required,
        )

    # Generic retrieve for grammar / culture / quiz / vocabulary
    if table == "grammar":
        sql = f"SELECT *, ? AS query_language FROM grammar {where} ORDER BY id ASC LIMIT ?"
        params2 = [lang_label] + list(base_params) + [limit]
        return QueryHit(
            op_name, "grammar", _format_sql(sql, params2),
            _safe_run(sql, params2, language), required,
        )

    if table == "culture":
        sql = f"SELECT *, ? AS query_language FROM culture {where} ORDER BY id ASC LIMIT ?"
        params2 = [lang_label] + list(base_params) + [limit]
        return QueryHit(
            op_name, "culture", _format_sql(sql, params2),
            _safe_run(sql, params2, language), required,
        )

    if table == "quiz":
        sql = f"SELECT *, ? AS query_language FROM quiz {where} ORDER BY id ASC LIMIT ?"
        params2 = [lang_label] + list(base_params) + [limit]
        return QueryHit(
            op_name, "quiz", _format_sql(sql, params2),
            _safe_run(sql, params2, language), required,
        )

    # Default vocabulary list / filter
    sql = f"""
        SELECT *, ? AS query_language FROM vocabulary
        {where}
        ORDER BY word ASC
        LIMIT ?
    """
    params2 = [lang_label] + list(base_params) + [limit]
    return QueryHit(
        op_name, "vocabulary", _format_sql(sql, params2),
        _safe_run(sql, params2, language), required,
    )


def _execute_op(
    op: "RetrievalOp",
    language: Optional[str],
    lesson_id: Optional[int],
    search_all: bool,
) -> QueryHit:
    p = op.params or {}
    try:
        language = _resolve_target_language(op, language)
    except RetrievalError as exc:
        return QueryHit(op.name, op.table, str(exc), [], op.required)

    if "lesson_id" in p:
        lesson_id = p.get("lesson_id")
    if "search_all" in p:
        search_all = bool(p.get("search_all"))

    kind = op.kind

    # Universal query compiler (compositional plans)
    if kind == "query":
        try:
            return _compile_universal_query(
                language=language,
                lesson_id=lesson_id,
                search_all=search_all,
                params=p,
                op_name=op.name,
                required=op.required,
            )
        except RetrievalError as exc:
            return QueryHit(op.name, op.table, str(exc), [], op.required)

    try:
        where, params = _scope_clause(language, lesson_id, search_all)
    except RetrievalError as exc:
        return QueryHit(op.name, op.table, str(exc), [], op.required)

    limit = int(p.get("limit") or 12)
    lang_label = language

    try:
        if kind in ("longest", "shortest", "top_longest", "avg_length"):
            sql = f"""
                SELECT *, ? AS query_language
                FROM vocabulary
                {where}
            """
            params2 = [lang_label] + list(params)
            all_rows = _safe_run(sql, params2, language)
            audit = (
                f"{_format_sql(sql, params2)} "
                f"| {COMPLETE_SCAN_NOTE} scanned={len(all_rows)}"
            )
            if kind == "avg_length":
                lengths = [normalized_word_length(r.get("word") or "") for r in all_rows]
                avg = (sum(lengths) / len(lengths)) if lengths else 0.0
                return QueryHit(
                    op.name,
                    "vocabulary",
                    audit,
                    [{
                        "avg_length": avg,
                        "count": len(lengths),
                        "query_language": lang_label,
                    }],
                    op.required,
                )
            descending = kind != "shortest"
            ranked = rank_rows_by_word_length(
                all_rows,
                descending=descending,
                limit=1 if kind in ("longest", "shortest") else max(1, limit),
                offset=0,
            )
            return QueryHit(op.name, "vocabulary", audit, ranked, op.required)

        if kind == "random":
            sql = f"""
                SELECT * FROM vocabulary
                {where}
                ORDER BY RANDOM()
                LIMIT 1
            """
            return QueryHit(
                op.name, "vocabulary", _format_sql(sql, params),
                _safe_run(sql, params, language, fetch_one=True), op.required,
            )

        if kind == "by_pos":
            pos = p.get("part_of_speech") or ""
            where2 = where + " AND part_of_speech = ?"
            params2 = list(params) + [pos, limit]
            sql = f"""
                SELECT * FROM vocabulary
                {where2}
                ORDER BY word ASC
                LIMIT ?
            """
            return QueryHit(
                op.name, "vocabulary", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        if kind == "difficult":
            params2 = list(params) + [limit]
            sql = f"""
                SELECT * FROM vocabulary
                {where}
                ORDER BY
                    CASE difficulty WHEN 'hard' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                    LENGTH(REPLACE(word, ' ', '')) DESC
                LIMIT ?
            """
            return QueryHit(
                op.name, "vocabulary", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        if kind == "list":
            params2 = list(params) + [limit]
            sql = f"""
                SELECT * FROM vocabulary
                {where}
                ORDER BY word ASC
                LIMIT ?
            """
            rows = _safe_run(sql, params2, language)
            if p.get("prefer_examples"):
                with_ex = [r for r in rows if (r.get("example_sentence") or "").strip()]
                if with_ex:
                    rows = with_ex
            return QueryHit(op.name, "vocabulary", _format_sql(sql, params2), rows, op.required)

        if kind == "search_meanings":
            meanings = list(p.get("meanings") or p.get("terms") or [])
            if not meanings:
                return QueryHit(op.name, "vocabulary", "SKIPPED search_meanings (empty)", [], op.required)
            clauses = []
            params2 = list(params)
            for meaning in meanings[:15]:
                like = f"%{meaning}%"
                clauses.append(
                    "(LOWER(meaning_en) LIKE ? OR LOWER(meaning_ms) LIKE ? "
                    "OR LOWER(word) LIKE ? OR LOWER(meaning_zh) LIKE ?)"
                )
                params2.extend([like.lower(), like.lower(), like.lower(), like.lower()])
            extra = " (" + " OR ".join(clauses) + ")"
            where2 = where + " AND" + extra
            params2.append(limit)
            sql = f"""
                SELECT * FROM vocabulary
                {where2}
                ORDER BY LENGTH(word) ASC, word ASC
                LIMIT ?
            """
            rows = _safe_run(sql, params2, language)
            return QueryHit(op.name, "vocabulary", _format_sql(sql, params2), rows, op.required)

        if kind == "search":
            terms = list(p.get("terms") or [])
            query = (p.get("query") or "").strip()
            if not terms and query:
                terms = topic_terms(query) or [query]
            if not terms:
                return QueryHit(op.name, "vocabulary", "SKIPPED search (empty)", [], op.required)
            from planner import RetrievalOp

            return _execute_op(
                RetrievalOp(
                    name=op.name,
                    table=op.table,
                    kind="search_meanings",
                    params={
                        "meanings": terms,
                        "limit": limit,
                        "language": language,
                        "lesson_id": lesson_id,
                        "search_all": search_all,
                    },
                    required=op.required,
                ),
                language,
                lesson_id,
                search_all,
            )

        if kind == "analytics":
            return _run_analytics(op, language, lesson_id, search_all)

        if kind == "grammar":
            sql = f"""
                SELECT * FROM grammar
                {where}
                ORDER BY id ASC
            """
            return QueryHit(
                op.name, "grammar", _format_sql(sql, params),
                _safe_run(sql, params, language), op.required,
            )

        if kind == "culture":
            query = (p.get("query") or "").strip()
            terms = topic_terms(query) if query else []
            where2, params2 = where, list(params)
            if terms:
                clauses = []
                for term in terms[:6]:
                    like = f"%{term}%"
                    clauses.append(
                        "(title LIKE ? OR content LIKE ? OR references_text LIKE ?)"
                    )
                    params2.extend([like, like, like])
                extra = " (" + " OR ".join(clauses) + ")"
                where2 = where2 + " AND" + extra
            params2.append(limit)
            sql = f"""
                SELECT * FROM culture
                {where2}
                ORDER BY id ASC
                LIMIT ?
            """
            rows = _safe_run(sql, params2, language)
            # Widen to all lessons for same language if topic search missed
            if not rows and terms and not search_all:
                where_b, params_b = _scope_clause(language, lesson_id, True)
                for term in terms[:6]:
                    like = f"%{term}%"
                    params_b = list(params_b) + [like, like, like]
                clauses = [
                    "(title LIKE ? OR content LIKE ? OR references_text LIKE ?)"
                    for _ in terms[:6]
                ]
                extra = " (" + " OR ".join(clauses) + ")"
                where_b = where_b + " AND" + extra
                params_b.append(limit)
                sql_b = f"SELECT * FROM culture {where_b} ORDER BY id ASC LIMIT ?"
                rows = _safe_run(sql_b, params_b, language)
                return QueryHit(
                    op.name, "culture",
                    _format_sql(sql, params2) + " || FALLBACK " + _format_sql(sql_b, params_b),
                    rows, op.required,
                )
            return QueryHit(op.name, "culture", _format_sql(sql, params2), rows, op.required)

        if kind == "quiz":
            params2 = list(params) + [limit]
            sql = f"""
                SELECT * FROM quiz
                {where}
                ORDER BY id ASC
                LIMIT ?
            """
            return QueryHit(
                op.name, "quiz", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        return QueryHit(op.name, op.table, f"UNKNOWN kind={kind}", [], op.required)

    except RetrievalError as exc:
        return QueryHit(op.name, op.table, str(exc), [], op.required)


def _run_analytics(
    op: "RetrievalOp",
    language: Optional[str],
    lesson_id: Optional[int],
    search_all: bool,
) -> QueryHit:
    p = op.params or {}
    try:
        language = _resolve_target_language(op, language)
    except RetrievalError as exc:
        return QueryHit(op.name, op.table, str(exc), [], op.required)

    if "lesson_id" in p:
        lesson_id = p.get("lesson_id")
    if "search_all" in p:
        search_all = bool(p.get("search_all"))

    try:
        where, params = _scope_clause(language, lesson_id, search_all)
    except RetrievalError as exc:
        return QueryHit(op.name, op.table, str(exc), [], op.required)

    kind = p.get("kind") or "count_all"
    limit = int(p.get("limit") or 12)
    lang_label = language

    try:
        if kind == "count_grammar":
            sql = f"SELECT COUNT(*) AS count, ? AS query_language FROM grammar {where}"
            params2 = [lang_label] + list(params)
            return QueryHit(
                op.name, "grammar", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        if kind == "count_culture":
            sql = f"SELECT COUNT(*) AS count, ? AS query_language FROM culture {where}"
            params2 = [lang_label] + list(params)
            return QueryHit(
                op.name, "culture", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        if kind.startswith("count_pos:"):
            pos = kind.split(":", 1)[1]
            where2 = where + " AND part_of_speech = ?"
            # SQL order: part_of_speech alias, query_language, WHERE language, WHERE pos
            sql = (
                f"SELECT COUNT(*) AS count, ? AS part_of_speech, ? AS query_language "
                f"FROM vocabulary {where2}"
            )
            params2 = [pos, lang_label] + list(params) + [pos]
            return QueryHit(
                op.name, "vocabulary", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        if kind.startswith("most_common_pos:"):
            pos = kind.split(":", 1)[1]
            where2 = where + " AND part_of_speech = ?"
            sql = f"""
                SELECT word, meaning_en, part_of_speech, difficulty, lesson_id, language,
                       ? AS query_language
                FROM vocabulary
                {where2}
                ORDER BY word ASC
                LIMIT ?
            """
            params2 = [lang_label] + list(params) + [pos, limit]
            return QueryHit(
                op.name, "vocabulary", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        if kind.startswith("starts_with:"):
            letter = kind.split(":", 1)[1]
            where2 = where + " AND LOWER(word) LIKE ?"
            sql = f"""
                SELECT *, ? AS query_language FROM vocabulary
                {where2}
                ORDER BY word ASC
                LIMIT ?
            """
            params2 = [lang_label] + list(params) + [f"{letter.lower()}%", limit]
            return QueryHit(
                op.name, "vocabulary", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        if kind.startswith("ends_with:"):
            frag = kind.split(":", 1)[1]
            where2 = where + " AND LOWER(word) LIKE ?"
            sql = f"""
                SELECT *, ? AS query_language FROM vocabulary
                {where2}
                ORDER BY word ASC
                LIMIT ?
            """
            params2 = [lang_label] + list(params) + [f"%{frag.lower()}", limit]
            return QueryHit(
                op.name, "vocabulary", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        if kind.startswith("contains:"):
            frag = kind.split(":", 1)[1]
            where2 = where + " AND LOWER(word) LIKE ?"
            sql = f"""
                SELECT *, ? AS query_language FROM vocabulary
                {where2}
                ORDER BY word ASC
                LIMIT ?
            """
            params2 = [lang_label] + list(params) + [f"%{frag.lower()}%", limit]
            return QueryHit(
                op.name, "vocabulary", _format_sql(sql, params2),
                _safe_run(sql, params2, language), op.required,
            )

        # longest / top_longest / avg_length handled above via complete-scan path

        # count_all / vocabulary size / greeting counts via count_pos
        sql = f"SELECT COUNT(*) AS count, ? AS query_language FROM vocabulary {where}"
        params2 = [lang_label] + list(params)
        return QueryHit(
            op.name, "vocabulary", _format_sql(sql, params2),
            _safe_run(sql, params2, language), op.required,
        )

    except RetrievalError as exc:
        return QueryHit(op.name, op.table, str(exc), [], op.required)


def _coverage_for_translation(tokens: list[str], rows: list[dict]) -> dict[str, Any]:
    matched = []
    missing = []
    meanings_blob = " ".join(
        f"{(r.get('meaning_en') or '')} {(r.get('word') or '')}".lower()
        for r in rows
    )
    for token in tokens:
        if token.lower() in meanings_blob:
            matched.append(token)
        else:
            missing.append(token)
    ratio = (len(matched) / len(tokens)) if tokens else 0.0
    return {
        "tokens": tokens,
        "matched": matched,
        "missing": missing,
        "coverage_ratio": round(ratio, 3),
    }


def execute_plan(plan: "TutorPlan") -> EvidenceBundle:
    hits: list[QueryHit] = []
    merged: list[dict] = []
    by_name: dict[str, list[dict]] = {}
    seen = set()
    require_topic = False

    for op in plan.operations:
        if op.kind == "culture" and (op.params or {}).get("require_topic_match"):
            require_topic = True
        hit = _execute_op(op, plan.language, plan.lesson_id, plan.search_all)
        hits.append(hit)
        by_name[hit.name] = hit.rows
        for row in hit.rows:
            key = (
                hit.table,
                row.get("id"),
                row.get("word"),
                row.get("question"),
                row.get("title"),
                row.get("count"),
                row.get("query_language"),
                hit.name,
            )
            if key in seen:
                continue
            seen.add(key)
            tagged = dict(row)
            tagged["_source_op"] = hit.name
            tagged["_source_table"] = hit.table
            # Preserve which language this op targeted
            if "__" in hit.name:
                parts = hit.name.split("__")
                if len(parts) >= 2 and parts[1] != "all":
                    tagged["_plan_language"] = parts[1]
            merged.append(tagged)

    coverage: dict[str, Any] = {}
    if plan.intent == "TRANSLATION" and plan.tokens:
        vocab_rows = by_name.get("translation_vocab") or []
        coverage = _coverage_for_translation(plan.tokens, vocab_rows)

    return EvidenceBundle(
        intent=plan.intent,
        language=plan.language,
        lesson_id=plan.lesson_id,
        tables=list(plan.required_tables),
        hits=hits,
        rows=merged,
        by_name=by_name,
        require_topic_match=require_topic,
        notes=list(plan.notes),
        coverage=coverage,
    )


_SORT_MAP = {
    "alpha": ("LOWER(word) ASC", "asc"),
    "alpha_desc": ("LOWER(word) DESC", "desc"),
    "length_desc": ("LENGTH(REPLACE(word, ' ', '')) DESC, word ASC", "desc"),
    "length_asc": ("LENGTH(REPLACE(word, ' ', '')) ASC, word ASC", "asc"),
    "difficulty": (
        "CASE difficulty WHEN 'hard' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, word ASC",
        "asc",
    ),
}


def normalize_search_term(term: str) -> str:
    """
    Search normalization (case, punctuation, apostrophes, hyphens, whitespace)
    used for the searchable dictionary UI. Exact match is tried by the caller
    first; this normalized form backs the safe fallback LIKE match — never a
    fuzzy match aggressive enough to cross languages.
    """
    text = (term or "").strip().lower()
    text = text.replace("'", "").replace("’", "")
    text = re.sub(r"[-\u2010-\u2015]", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def dictionary_search(
    *,
    language: str,
    query: str = "",
    part_of_speech: Optional[str] = None,
    difficulty: Optional[str] = None,
    sort: str = "alpha",
    limit: int = 30,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Structured (non-NLP) vocabulary browse/search for the Dictionary UI.

    Returns the universal query result contract. Always language-scoped;
    raises RetrievalError if language is missing/unsupported by the caller's
    own validation before this is called.
    """
    where, base_params = build_language_filter(language)
    filters_applied: list[dict[str, Any]] = []

    if part_of_speech:
        where += " AND part_of_speech = ?"
        base_params = list(base_params) + [part_of_speech]
        filters_applied.append({"field": "part_of_speech", "op": "=", "value": part_of_speech})

    if difficulty:
        where += " AND difficulty = ?"
        base_params = list(base_params) + [difficulty]
        filters_applied.append({"field": "difficulty", "op": "=", "value": difficulty})

    normalized = normalize_search_term(query)
    exact_rows: list[dict] = []
    if normalized:
        exact_sql = f"""
            SELECT *, LENGTH(REPLACE(word, ' ', '')) AS word_len FROM vocabulary
            {where} AND LOWER(word) = ?
        """
        exact_rows = _run_query(exact_sql, list(base_params) + [normalized])
        where += (
            " AND (LOWER(word) LIKE ? OR LOWER(meaning_en) LIKE ? "
            "OR LOWER(meaning_ms) LIKE ?)"
        )
        like = f"%{normalized}%"
        base_params = list(base_params) + [like, like, like]
        filters_applied.append({"field": "word_or_meaning", "op": "contains", "value": normalized})

    order_sql, order_dir = _SORT_MAP.get(sort, _SORT_MAP["alpha"])

    count_sql = f"SELECT COUNT(*) AS c FROM vocabulary {where}"
    total_row = _run_query(count_sql, list(base_params), fetch_one=True)
    total_matches = int(total_row[0]["c"]) if total_row else 0

    sql = f"""
        SELECT *, LENGTH(REPLACE(word, ' ', '')) AS word_len FROM vocabulary
        {where}
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
    """
    rows = _safe_run(sql, list(base_params) + [limit, offset], language)

    if exact_rows:
        exact_ids = {r.get("id") for r in exact_rows}
        rows = exact_rows + [r for r in rows if r.get("id") not in exact_ids]
        rows = rows[:limit]

    return {
        "language": language,
        "query_type": "search" if query else "browse",
        "metric": None,
        "filters": filters_applied,
        "order": order_dir,
        "limit": limit,
        "offset": offset,
        "rows": rows,
        "total_matches": total_matches,
        "coverage": {"exact_match": bool(exact_rows)},
        "source": "vocabulary_table",
    }


def dictionary_word_by_id(language: str, word_id: int) -> Optional[dict[str, Any]]:
    """Fetch one vocabulary row by id, always scoped to the given language."""
    where, params = build_language_filter(language)
    sql = f"""
        SELECT *, LENGTH(REPLACE(word, ' ', '')) AS word_len FROM vocabulary
        {where} AND id = ?
    """
    rows = _safe_run(sql, list(params) + [word_id], language, fetch_one=True)
    return rows[0] if rows else None


def dictionary_random_word(
    *,
    language: Optional[str] = None,
    part_of_speech: Optional[str] = None,
    difficulty: Optional[str] = None,
    seed: Optional[str] = None,
    exclude_ids: Optional[list[int]] = None,
) -> Optional[dict[str, Any]]:
    """
    Return one real vocabulary row. Never fabricates fields.

    If seed is provided, selection is deterministic for that seed
    (useful for daily / testable 'random' draws).
    exclude_ids avoids immediate repeats within a discovery session.
    """
    import hashlib
    import random as _random

    filters = ["word IS NOT NULL", "TRIM(word) != ''"]
    params: list[Any] = []

    if language:
        where_lang, lang_params = build_language_filter(language)
        clause = where_lang.replace("WHERE ", "", 1).strip()
        if clause:
            filters.append(f"({clause})")
            params.extend(list(lang_params))

    if part_of_speech:
        filters.append("part_of_speech = ?")
        params.append(part_of_speech)
    if difficulty:
        filters.append("difficulty = ?")
        params.append(difficulty)

    where_sql = " WHERE " + " AND ".join(filters)
    blocked = {
        int(x)
        for x in (exclude_ids or [])
        if isinstance(x, int) or (isinstance(x, str) and str(x).isdigit())
    }
    # Prefer COUNT + OFFSET over loading every matching id into Python.
    count_sql = f"SELECT COUNT(*) AS c FROM vocabulary {where_sql}"
    count_row = _run_query(count_sql, list(params), fetch_one=True)
    total = int(count_row[0]["c"]) if count_row else 0
    if total <= 0:
        return None

    if seed:
        digest = hashlib.sha256(str(seed).encode("utf-8")).hexdigest()
        rng = _random.Random(int(digest[:16], 16))
        pick = rng.randrange(total)
    else:
        pick = _random.randrange(total)

    # When excludes are small, retry a few OFFSET picks instead of materializing all ids.
    chosen_id = None
    for attempt in range(6):
        offset = (pick + attempt) % total
        id_sql = f"SELECT id FROM vocabulary {where_sql} LIMIT 1 OFFSET ?"
        id_rows = _run_query(id_sql, list(params) + [offset], fetch_one=True)
        if not id_rows:
            break
        candidate = id_rows[0]["id"]
        if candidate not in blocked or attempt == 5 or total <= len(blocked):
            chosen_id = candidate
            break
    if chosen_id is None:
        return None

    detail_sql = """
        SELECT *, LENGTH(REPLACE(word, ' ', '')) AS word_len
        FROM vocabulary WHERE id = ?
    """
    detail = _run_query(detail_sql, [chosen_id], fetch_one=True)
    return detail[0] if detail else None


def get_quiz_questions(
    language: str,
    lesson_id: int,
    limit: int = 40,
    search_all: bool = False,
    difficulty: Optional[str] = None,
) -> list[dict]:
    where, params = _scope_clause(language, lesson_id, search_all)
    if difficulty:
        where = where + " AND difficulty = ?"
        params = list(params) + [difficulty]
    params = list(params) + [limit]
    sql = f"""
        SELECT * FROM quiz
        {where}
        ORDER BY id ASC
        LIMIT ?
    """
    return _safe_run(sql, params, language)
