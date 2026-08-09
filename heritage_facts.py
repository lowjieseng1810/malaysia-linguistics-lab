"""Curated local 'Do You Know?' facts — no AI generation.

Facts are general, non-invented statements grounded in widely documented
public knowledge about Malaysian linguistic diversity. Keep this list
conservative; prefer geography / language-family framing over disputed claims.
"""

from __future__ import annotations

import hashlib
from typing import Any

HERITAGE_FACTS: list[dict[str, Any]] = [
    {
        "id": "my-diversity",
        "language": None,
        "category": "geography",
        "fact": "Malaysia is home to many indigenous and minority languages across Peninsular Malaysia, Sabah, and Sarawak.",
        "source": "General linguistic geography of Malaysia",
    },
    {
        "id": "iban-sarawak",
        "language": "iban",
        "category": "geography",
        "fact": "Iban is closely associated with Iban communities in Sarawak.",
        "source": "Project course region data",
    },
    {
        "id": "kadazan-sabah",
        "language": "kadazan-dusun",
        "category": "geography",
        "fact": "Kadazan-Dusun language traditions are strongly connected with communities in Sabah.",
        "source": "Project course region data",
    },
    {
        "id": "bidayuh-sarawak",
        "language": "bidayuh",
        "category": "geography",
        "fact": "Bidayuh language heritage is associated with communities in Sarawak.",
        "source": "Project course region data",
    },
    {
        "id": "mah-meri-selangor",
        "language": "mah-meri",
        "category": "geography",
        "fact": "Mah Meri is connected with coastal communities in Selangor, Peninsular Malaysia.",
        "source": "Project course region data",
    },
    {
        "id": "borneo-island",
        "language": None,
        "category": "geography",
        "fact": "Sabah and Sarawak, on the island of Borneo, are home to many of Malaysia's indigenous languages.",
        "source": "General geography",
    },
    {
        "id": "peninsular-indigenous",
        "language": None,
        "category": "geography",
        "fact": "Peninsular Malaysia also has indigenous language communities, including Orang Asli languages such as Mah Meri.",
        "source": "General linguistic geography",
    },
    {
        "id": "learn-preserves",
        "language": None,
        "category": "preservation",
        "fact": "Learning and documenting living languages helps keep community knowledge and stories connected across generations.",
        "source": "Language preservation principle",
    },
    {
        "id": "four-worlds",
        "language": None,
        "category": "exploration",
        "fact": "This explorer focuses on four living language worlds: Iban, Kadazan-Dusun, Bidayuh, and Mah Meri.",
        "source": "Project language set",
    },
    {
        "id": "beacon-idea",
        "language": None,
        "category": "exploration",
        "fact": "In the Language Universe, each beacon marks a living language community connected to a place in Malaysia.",
        "source": "Product exploration design",
    },
    {
        "id": "dictionary-bridge",
        "language": None,
        "category": "learning",
        "fact": "A single word can become a bridge — dictionary exploration connects sound, meaning, and culture.",
        "source": "Learning design principle",
    },
    {
        "id": "consistency",
        "language": None,
        "category": "learning",
        "fact": "Short, regular practice often helps language learning more than rare long sessions.",
        "source": "General language-learning principle",
    },
]


def pick_heritage_fact(seed: str | None = None, language: str | None = None) -> dict[str, Any]:
    pool = HERITAGE_FACTS
    if language:
        focused = [f for f in pool if f.get("language") in (None, language)]
        if focused:
            pool = focused
    if not pool:
        pool = HERITAGE_FACTS
    if seed:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(pool)
    else:
        index = 0
    fact = dict(pool[index])
    return fact
