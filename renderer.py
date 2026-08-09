"""
Smart educational renderer — turns validated evidence into teaching answers.
"""

from __future__ import annotations

from typing import Any, Optional

from planner import (
    ANALYTICS,
    COMPARE,
    CONVERSATION,
    CULTURE,
    DIFFICULT_WORDS,
    EXAMPLE_SENTENCE,
    EXPLANATION,
    GRAMMAR_EXPLANATION,
    LESSON_SUMMARY,
    LINGUISTICS,
    LONGEST_WORD,
    MORPHOLOGY,
    PRONUNCIATION,
    RANKING,
    SEARCH,
    SEMANTICS,
    SHORTEST_WORD,
    STATISTICS,
    SYNTAX,
    TEACHING,
    TRANSLATION,
    VOCABULARY_LOOKUP,
)
from language_registry import display_name
from word_length import normalized_word_length


def _scope(lang_key: Optional[str], level_num: Optional[int]) -> str:
    lang = (lang_key or "this language").replace("_", " ").replace("-", " ").title()
    if level_num is not None:
        return f"{lang} Level {level_num}"
    return lang


def format_vocab_card(row: dict) -> str:
    lines = []
    word = row.get("word") or ""
    lines.append(f"**Word:** {word}")
    if row.get("meaning_en"):
        lines.append(f"**Meaning:** {row['meaning_en']}")
    if row.get("meaning_ms"):
        lines.append(f"**Malay:** {row['meaning_ms']}")
    if row.get("part_of_speech"):
        lines.append(f"**Part of speech:** {row['part_of_speech']}")
    if row.get("ipa"):
        lines.append(f"**Pronunciation:** {row['ipa']}")
    elif word:
        lines.append("**Pronunciation:** (IPA not listed yet)")
    if row.get("example_sentence"):
        lines.append(f"**Example sentence:** {row['example_sentence']}")
    if row.get("culture_note"):
        lines.append(f"**Culture note:** {row['culture_note']}")
    if row.get("difficulty"):
        lines.append(f"**Difficulty:** {row['difficulty']}")
    if row.get("lesson_id") is not None:
        lines.append(f"**Lesson:** {row['lesson_id']}")
    return "\n".join(lines)


def render_evidence(
    plan,
    bundle,
    *,
    coaching_note: str = "",
) -> str:
    intent = plan.intent
    lang_key = plan.language
    level_num = plan.lesson_id
    scope = _scope(lang_key, level_num)
    rows = bundle.rows or []
    parts: list[str] = []

    if coaching_note:
        parts.append(coaching_note)
        parts.append("")

    if intent == LONGEST_WORD and rows and getattr(plan, "response_type", "") != "comparison":
        r = rows[0]
        parts.append(
            f"The longest word in the {scope} vocabulary database is "
            f"**{r.get('word')}** "
            f"({int(r.get('word_len') or normalized_word_length(r.get('word') or ''))} letters)."
        )
        parts.append("")
        parts.append(format_vocab_card(r))
        return "\n".join(parts)

    if intent == SHORTEST_WORD and rows and getattr(plan, "response_type", "") != "comparison":
        r = rows[0]
        parts.append(
            f"The shortest word in the {scope} vocabulary database is "
            f"**{r.get('word')}** "
            f"({int(r.get('word_len') or normalized_word_length(r.get('word') or ''))} letters)."
        )
        parts.append("")
        parts.append(format_vocab_card(r))
        return "\n".join(parts)

    if intent == DIFFICULT_WORDS and getattr(plan, "response_type", "") != "comparison":
        parts.append(f"### Difficult words — {scope}")
        parts.append("")
        for r in rows:
            parts.append(format_vocab_card(r))
            parts.append("")
        return "\n".join(parts).strip()

    if (
        intent == COMPARE
        or getattr(plan, "response_type", "") == "comparison"
        or (
            intent in (ANALYTICS, STATISTICS, RANKING, LONGEST_WORD, SHORTEST_WORD)
            and len(getattr(plan, "entities", None) or []) > 1
        )
    ):
        return _render_comparison(plan, bundle)

    if intent in (ANALYTICS, STATISTICS, RANKING) or getattr(plan, "response_type", "") == "analytics":
        return _render_analytics(plan, bundle, scope)

    if intent in (TEACHING, EXPLANATION):
        return _render_teaching(plan, bundle, scope)

    if intent == TRANSLATION:
        return _render_translation(plan, bundle, scope)

    if intent == CONVERSATION:
        return _render_conversation(plan, bundle, scope)

    if intent == GRAMMAR_EXPLANATION:
        return _render_grammar(plan, bundle, scope)

    if intent == EXAMPLE_SENTENCE:
        return _render_examples(plan, bundle, scope)

    if intent == CULTURE:
        return _render_culture(plan, bundle, scope)

    if intent == PRONUNCIATION or intent in (LINGUISTICS, MORPHOLOGY, SYNTAX, SEMANTICS):
        parts.append(f"### From the {scope} lesson database")
        parts.append("")
        parts.append(
            "_Database evidence below. General linguistic background is not included "
            "in this fallback renderer._"
        )
        parts.append("")
        for r in rows[:10]:
            parts.append(format_vocab_card(r) if r.get("word") else str(r))
            parts.append("")
        return "\n".join(parts).strip()

    if intent == LESSON_SUMMARY:
        return _render_summary(plan, bundle, scope)

    if intent in (SEARCH, VOCABULARY_LOOKUP):
        parts.append(f"### Vocabulary — {scope}")
        parts.append("")
        for r in [x for x in rows if x.get("word")][:12]:
            parts.append(format_vocab_card(r))
            parts.append("")
            # Related words by same POS
            pos = r.get("part_of_speech")
            related = [
                x for x in rows
                if x.get("word") != r.get("word") and x.get("part_of_speech") == pos
            ][:3]
            if related:
                parts.append(
                    "**Related words:** "
                    + ", ".join(f"{x.get('word')} ({x.get('meaning_en')})" for x in related)
                )
                parts.append("")
        return "\n".join(parts).strip()

    # Generic
    parts.append(f"### From the {scope} lesson database")
    parts.append("")
    for r in rows[:10]:
        if r.get("word"):
            parts.append(format_vocab_card(r))
        elif r.get("title"):
            parts.append(f"**{r.get('title')}**")
            parts.append(r.get("content") or r.get("explanation") or "")
        parts.append("")
    return "\n".join(parts).strip()


def _render_analytics(plan, bundle, scope: str) -> str:
    kind = plan.analytics_kind or plan.operation or ""
    rows = bundle.rows
    if not rows and bundle.by_name:
        for v in bundle.by_name.values():
            rows.extend(v)

    if kind in ("count_all", "count_grammar", "count_culture") or kind.startswith("count_pos:"):
        count = rows[0].get("count") if rows else 0
        label = {
            "count_all": "vocabulary entries",
            "count_grammar": "grammar entries",
            "count_culture": "culture entries",
        }.get(kind, kind.split(":")[-1] + " entries" if ":" in kind else "entries")
        lang = rows[0].get("query_language") if rows else scope
        return f"In **{display_name(str(lang)) if lang and lang != 'all' else scope}** there are **{count}** {label}."

    if kind == "avg_length" and rows:
        avg = rows[0].get("avg_length")
        count = rows[0].get("count")
        return (
            f"Average word length in {scope}: **{float(avg or 0):.2f}** letters "
            f"(across {count} entries)."
        )

    if kind == "top_longest":
        parts = [f"### Top longest words — {scope}", ""]
        for i, r in enumerate(rows, 1):
            length = r.get("word_len") or len(str(r.get("word") or "").replace(" ", ""))
            parts.append(
                f"{i}. **{r.get('word')}** ({length}) — {r.get('meaning_en') or ''}"
            )
        return "\n".join(parts)

    parts = [f"### Analytics — {scope}", ""]
    for r in rows:
        if r.get("word"):
            parts.append(
                f"- **{r.get('word')}** — {r.get('meaning_en') or ''} "
                f"_{r.get('part_of_speech') or ''}_"
            )
        elif r.get("count") is not None:
            parts.append(f"- Count: **{r.get('count')}**")
        elif r.get("avg_length") is not None:
            parts.append(f"- Average length: **{float(r['avg_length']):.2f}**")
    return "\n".join(parts)


def _op_params_for_hit(plan, hit_name: str) -> dict:
    for op in getattr(plan, "operations", None) or []:
        if op.name == hit_name:
            return dict(op.params or {})
    return {}


def _render_comparison(plan, bundle) -> str:
    """
    Render one section per requested language for any compositional metric.

    plan.compare_metric is usually "<aggregation-or-operation>:<metric-or-table>"
    (e.g. "rank:word_length", "max:word_length", "count:vocabulary",
    "avg:word_length"). Heterogeneous multi-clause plans use "mixed:word_length"
    and render each hit from its own op aggregation. Row counts follow each
    op's requested limit — never a hardcoded semantic top-k.
    """
    metric_raw = plan.compare_metric or plan.analytics_kind or plan.operation or ""
    agg_part, _, field_part = metric_raw.partition(":")
    spec = getattr(plan, "query_spec", None) or {}
    order = (spec.get("order") or "").lower()
    requested_limit = spec.get("limit") or 5
    mixed = metric_raw.startswith("mixed:")
    is_word_length = (
        mixed
        or field_part == "word_length"
        or (agg_part in ("max", "min") and field_part in (None, "", "word_length"))
    )
    is_count = agg_part == "count" or field_part in ("vocabulary", "grammar", "culture") and agg_part == "count"
    is_avg = agg_part == "avg"

    title = (
        "Comparison — structured vocabulary analytics"
        if mixed
        else f"Comparison — {metric_raw.replace('_', ' ').replace(':', ' — ')}"
    )
    parts = [f"### {title}", ""]
    if plan.unsupported:
        parts.append(
            "Note: some requested languages are not in the database: "
            + ", ".join(plan.unsupported)
        )
        parts.append("")

    winners = []
    for hit in bundle.hits:
        lang_key = None
        if "__" in hit.name:
            bits = hit.name.split("__")
            if len(bits) >= 2 and bits[1] != "all":
                lang_key = bits[1]
        label = display_name(lang_key) if lang_key else "All languages"
        op_params = _op_params_for_hit(plan, hit.name)
        hit_agg = (op_params.get("aggregation") or agg_part or "").lower()
        hit_order = (op_params.get("order") or order or "").lower()
        hit_limit = int(op_params.get("limit") or requested_limit or 1)
        if hit_agg == "max":
            metric_label = "longest"
        elif hit_agg == "min":
            metric_label = "shortest"
        elif hit_agg == "rank" and hit_order == "asc":
            metric_label = "shortest ranked"
        elif hit_agg == "rank":
            metric_label = "longest ranked"
        else:
            metric_label = hit_agg or "result"

        parts.append(f"#### {label} — {metric_label}")
        rows = hit.rows or []
        if not rows:
            parts.append("No evidence found.")
            parts.append("")
            continue

        if is_count and not mixed:
            count = rows[0].get("count")
            parts.append(f"- Count: **{count}**")
            winners.append((label, str(count), float(count or 0), "count"))
        elif is_avg and not mixed:
            avg = float(rows[0].get("avg_length") or 0)
            parts.append(f"- Average length: **{avg:.2f}**")
            winners.append((label, f"{avg:.2f}", avg, "avg"))
        elif is_word_length:
            shown = rows[: max(1, hit_limit)]
            best_len = None
            for r in shown:
                length = int(
                    r.get("word_len")
                    or normalized_word_length(r.get("word") or "")
                )
                parts.append(
                    f"- **{r.get('word')}** ({length} letters) — {r.get('meaning_en') or ''}"
                )
                if best_len is None:
                    best_len = length
            if shown and shown[0].get("word"):
                winners.append(
                    (label, shown[0].get("word"), float(best_len or 0), hit_agg or hit_order)
                )
            if len(rows) < hit_limit:
                parts.append(
                    f"_Only {len(rows)} of the requested {hit_limit} entries "
                    "exist in the database for this language._"
                )
        else:
            shown = rows[: max(1, hit_limit)]
            for r in shown:
                if r.get("word"):
                    parts.append(f"- **{r.get('word')}** — {r.get('meaning_en') or ''}")
                elif r.get("count") is not None:
                    parts.append(f"- Count: **{r.get('count')}**")
        parts.append("")

    if winners and len(winners) > 1 and not mixed:
        kinds = {w[3] for w in winners}
        if is_count or is_avg or (is_word_length and order != "asc"):
            best = max(winners, key=lambda x: x[2])
            parts.append(f"**Winner:** {best[0]} → {best[1]}")
        elif is_word_length and order == "asc":
            best = min(winners, key=lambda x: x[2])
            parts.append(f"**Winner (shortest):** {best[0]} → {best[1]}")
        elif kinds == {"max"} or kinds == {"desc"}:
            best = max(winners, key=lambda x: x[2])
            parts.append(f"**Winner (longest):** {best[0]} → {best[1]}")

    return "\n".join(parts).strip()


def _render_teaching(plan, bundle, scope: str) -> str:
    greetings = bundle.rows_for("greetings") or [
        r for r in bundle.rows if r.get("part_of_speech") == "greeting"
    ]
    grammar = bundle.rows_for("grammar")
    examples = bundle.rows_for("examples")
    related = bundle.rows_for("related_vocab")

    parts = [
        f"### How to introduce yourself — {scope}",
        "",
        "Here is a complete teaching answer from the lesson database.",
        "",
        "#### 1. Greeting vocabulary",
        "",
    ]
    for r in greetings[:6]:
        parts.append(format_vocab_card(r))
        parts.append("")

    if related:
        parts.append("#### 2. Useful related words")
        parts.append("")
        for r in related[:6]:
            if r in greetings:
                continue
            parts.append(
                f"- **{r.get('word')}** — {r.get('meaning_en') or ''} "
                f"_{r.get('part_of_speech') or ''}_"
            )
        parts.append("")

    if grammar:
        parts.append("#### 3. Grammar / sentence patterns")
        parts.append("")
        for g in grammar[:2]:
            parts.append(f"**{g.get('title') or 'Pattern'}**")
            if g.get("explanation"):
                parts.append(g["explanation"])
            if g.get("examples"):
                parts.append(f"**Examples:** {g['examples']}")
            if g.get("common_mistakes"):
                parts.append(f"**Common mistakes:** {g['common_mistakes']}")
            parts.append("")

    parts.append("#### 4. Example dialogue (from verified words)")
    parts.append("")
    # Build a tiny dialogue only from retrieved greeting words
    by_meaning = {
        (r.get("meaning_en") or "").lower(): r for r in greetings + (related or [])
    }
    welcome = next(
        (r for r in greetings if "welcome" in (r.get("meaning_en") or "").lower()),
        greetings[0] if greetings else None,
    )
    how_are = next(
        (r for r in greetings if "how are you" in (r.get("meaning_en") or "").lower()),
        None,
    )
    my_name = next(
        (r for r in greetings if "my name" in (r.get("meaning_en") or "").lower()),
        None,
    )
    if welcome:
        parts.append(f"A: **{welcome.get('word')}** — {welcome.get('meaning_en')}")
    if how_are:
        parts.append(f"B: **{how_are.get('word')}** — {how_are.get('meaning_en')}")
    if my_name:
        parts.append(f"A: **{my_name.get('word')}** — {my_name.get('meaning_en')}")
    if not any([welcome, how_are, my_name]) and examples:
        for r in examples[:3]:
            if r.get("example_sentence"):
                parts.append(f"- {r['example_sentence']} ({r.get('word')})")

    parts.append("")
    parts.append(
        "Practice tip: learn the greeting forms first, then swap in your own name."
    )
    return "\n".join(parts)


def _render_translation(plan, bundle, scope: str) -> str:
    vocab = bundle.rows_for("translation_vocab") or [
        r for r in bundle.rows if r.get("word")
    ]
    grammar = bundle.rows_for("grammar")
    coverage = bundle.coverage or {}
    parts = [
        f"### Translation support — {scope}",
        "",
        f"**Source ({plan.source_lang or 'en'}):** {plan.source_text}",
        "",
        "#### Retrieved vocabulary evidence",
        "",
    ]
    for r in vocab:
        parts.append(format_vocab_card(r))
        parts.append("")

    if grammar:
        parts.append("#### Grammar notes from the lesson")
        parts.append("")
        g = grammar[0]
        parts.append(f"**{g.get('title') or 'Grammar'}**")
        if g.get("explanation"):
            parts.append(g["explanation"])
        if g.get("examples"):
            parts.append(f"Examples: {g['examples']}")
        parts.append("")

    matched = coverage.get("matched") or []
    missing = coverage.get("missing") or []
    parts.append(
        f"**Coverage:** {coverage.get('coverage_ratio', 0):.0%} "
        f"({len(matched)} matched / {len(coverage.get('tokens') or [])} tokens)."
    )
    if missing:
        parts.append(
            "Missing evidence for: " + ", ".join(missing)
            + ". Do not invent words for these."
        )
    parts.append("")
    # Deterministic draft using available glosses only
    glosses = []
    for r in vocab:
        glosses.append(f"{r.get('word')} ({r.get('meaning_en')})")
    if glosses:
        parts.append("**Evidence-based draft (word map):** " + " · ".join(glosses))
    return "\n".join(parts)


def _render_conversation(plan, bundle, scope: str) -> str:
    vocab = [r for r in bundle.rows if r.get("word")]
    parts = [
        f"### Conversation practice — {scope}",
        "",
        "I can role-play using **only** these verified lesson words:",
        "",
    ]
    for r in vocab[:20]:
        parts.append(f"- **{r.get('word')}** — {r.get('meaning_en') or ''}")
    parts.append("")
    greetings = [r for r in vocab if r.get("part_of_speech") == "greeting"]
    if greetings:
        g = greetings[0]
        parts.append(f"Opening line: **{g.get('word')}** ({g.get('meaning_en')})")
    parts.append("")
    parts.append(
        "Reply with a short line; I will stay inside this vocabulary set."
    )
    return "\n".join(parts)


def _render_grammar(plan, bundle, scope: str) -> str:
    grammar = bundle.rows_for("grammar") or [
        r for r in bundle.rows if r.get("explanation")
    ]
    vocab = bundle.rows_for("supporting_vocab") or []
    parts = [f"### Grammar — {scope}", ""]
    for g in grammar[:3]:
        parts.append(f"**{g.get('title') or 'Grammar'}**")
        if g.get("explanation"):
            parts.append(g["explanation"])
        if g.get("examples"):
            parts.append(f"**Examples:** {g['examples']}")
        if g.get("common_mistakes"):
            parts.append(f"**Common mistakes:** {g['common_mistakes']}")
        parts.append("")
    if vocab:
        parts.append("#### Related vocabulary")
        parts.append("")
        for r in vocab[:6]:
            parts.append(format_vocab_card(r))
            parts.append("")
    return "\n".join(parts).strip()


def _render_examples(plan, bundle, scope: str) -> str:
    rows = bundle.rows_for("examples") or bundle.rows
    parts = [f"### Example sentences — {scope}", ""]
    added = 0
    for r in rows:
        if r.get("example_sentence"):
            parts.append(f"- **{r.get('word')}**: {r['example_sentence']}")
            if r.get("meaning_en"):
                parts.append(f"  Meaning: {r['meaning_en']}")
            added += 1
    if not added:
        parts.append("No stored example sentences yet. Useful words for practice:")
        for r in rows[:8]:
            if r.get("word"):
                parts.append(f"- **{r.get('word')}** — {r.get('meaning_en') or ''}")
    return "\n".join(parts)


def _render_culture(plan, bundle, scope: str) -> str:
    rows = bundle.rows_for("culture") or bundle.rows
    parts = [f"### Culture — {scope}", ""]
    for r in rows[:4]:
        parts.append(f"**{r.get('title') or 'Culture note'}**")
        if r.get("content"):
            parts.append(r["content"])
        if r.get("references_text"):
            parts.append(f"_Reference: {r['references_text']}_")
        parts.append("")
    return "\n".join(parts).strip()


def _render_summary(plan, bundle, scope: str) -> str:
    vocab = bundle.rows_for("vocab") or [r for r in bundle.rows if r.get("word")]
    grammar = bundle.rows_for("grammar")
    culture = bundle.rows_for("culture")
    parts = [f"### Lesson summary — {scope}", ""]
    parts.append(f"This lesson has **{len(vocab)}** vocabulary entries in the database.")
    parts.append("")
    parts.append("#### Key words")
    for r in vocab[:8]:
        parts.append(f"- **{r.get('word')}** — {r.get('meaning_en') or ''}")
    if grammar:
        parts.append("")
        parts.append("#### Grammar focus")
        parts.append(grammar[0].get("explanation") or grammar[0].get("title") or "")
    if culture:
        parts.append("")
        parts.append("#### Culture note")
        parts.append(culture[0].get("title") or "")
        parts.append((culture[0].get("content") or "")[:280])
    return "\n".join(parts)
