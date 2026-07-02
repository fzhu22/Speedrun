# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Deterministic question-writing guidance shown while authoring a card.

Pure logic (no Qt, no AI, no network) so it is unit-testable and safe to run with AI off.
The desktop Add-dialog panel calls this to show tips for the chosen (or inferred) MCAT
content category; the AI hint button is a separate, optional layer on top.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from anki.speedrun.aamc_outline import load_outline_graph
from anki.speedrun.models import NodeKind

#: Universal "what makes a good card" rules, applied to any topic. Kept short (3) so
#: the Add-dialog panel never pushes the fields into scrolling.
TOPIC_TIPS: List[str] = [
    "Test why or how, not just a definition.",
    "One idea per card, with a specific answer.",
    "Add the trap: the tempting wrong answer it catches.",
]


def content_categories() -> List[Tuple[str, str]]:
    """The AAMC content categories as ``(code, title)``, sorted 1A, 1B, ... 10A."""
    graph = load_outline_graph()
    cats = [
        (n.id.split(":")[-1], n.title) for n in graph.nodes(NodeKind.CONTENT_CATEGORY)
    ]
    cats.sort(key=lambda c: (len(c[0]), c[0]))
    return cats


def guidance_for_topic(
    code: Optional[str] = None, title: Optional[str] = None
) -> List[str]:
    """Guidance lines for the panel: a short lead line followed by the universal tips.

    The lead names only the topic code (the full title is already shown in the picker
    above), so the panel stays compact."""
    if code:
        lead = f"For {code}, write a question that makes you USE the idea, not just restate it."
    else:
        lead = "Write a question that tests why or how, not just recall."
    return [lead, *TOPIC_TIPS]


def _tokens(strings: List[str]) -> set:
    out: set = set()
    for s in strings:
        for tok in re.split(r"[^a-z0-9]+", (s or "").lower()):
            if tok:
                out.add(tok)
    return out


def infer_topic(
    tags: Optional[List[str]], deck_name: str = ""
) -> Optional[Tuple[str, str]]:
    """Best-effort topic from the card's tags/deck (the "Auto" fallback for the picker).

    Matches (1) a content-category code appearing as a token (e.g. a ``MCAT::1A::...``
    tag), then (2) a content-category title appearing in the tag/deck text. Returns None
    when nothing matches (the panel then shows the general tips)."""
    sources = [str(s) for s in (list(tags or []) + ([deck_name] if deck_name else []))]
    if not sources:
        return None
    cats = content_categories()
    tokens = _tokens(sources)
    for code, title in cats:
        if code.lower() in tokens:
            return (code, title)
    hay = " ".join(sources).lower()
    for code, title in cats:
        if title.lower() in hay:
            return (code, title)
    return None
