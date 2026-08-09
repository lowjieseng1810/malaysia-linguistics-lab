# Verified vocabulary packs

This folder holds **externally verified** vocabulary JSON packs for dictionary expansion.

## Rules

- Do **not** invent indigenous-language words or translations.
- Do **not** treat LLM output as a source.
- Every pack must include a non-empty `source_ref`.
- Preserve `dialect_variant` when the source names a variety (especially Bidayuh and Kadazan-Dusun).
- The project course currently uses language keys `iban`, `kadazan-dusun`, `bidayuh`, and `mah-meri` without finer variety labels in `COURSE_DATA`. Leave `dialect_variant` null for those course-harvested rows unless a source specifies a variety.

## Target vs verified

Learning target: **250 entries per language** (1,000 total).

Accuracy beats the count. If verified packs are missing, the database keeps only course-harvested entries and reports the shortfall as unavailable.

## Pack format

Save one JSON file per source/language (filename free-form, `*.json`). Skip `sources.json` / `manifest.json`.

```json
{
  "language": "iban",
  "source_ref": "Publisher / dictionary title (year)",
  "dialect_variant": null,
  "entries": [
    {
      "word": "Apai",
      "meaning_en": "Father",
      "meaning_ms": "Bapa",
      "part_of_speech": "noun",
      "lesson_id": 2,
      "ipa": null,
      "example_sentence": null
    }
  ]
}
```

Import happens on app startup via `import_verified_vocabulary_packs()` in `database.py`.

## Rebuild from open sources

Raw downloads live under `raw/`. Rebuild pack JSON with:

```bash
python qa_temp/_build_vocab_packs.py
```

Then restart the app (or run `python qa_temp/_import_and_validate_vocab.py`).

Provenance ledger: [`sources.json`](sources.json).
