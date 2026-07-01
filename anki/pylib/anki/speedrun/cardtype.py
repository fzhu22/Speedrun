"""Card-type classification + the disconfirmer gating decision (PRD 6.3 scoping).

Not every miss deserves a disconfirmer: a pure fact ("how many amino acids?") should
just be re-studied, while an application/reasoning card is where "what would flip this?"
pays off. This module is the deterministic baseline (also the AI-off path); the AI
classifier in ``ai.py`` is held against it in ``ai_eval.py``.
"""

from __future__ import annotations

import re
from enum import Enum


class CardType(str, Enum):
    DECLARATIVE = "declarative"  # a fact to recall; no disconfirmer
    APPLICATION = "application"  # reasoning/transfer; a disconfirmer helps


# Reasoning cues -> application (checked first; they win regardless of answer length).
_APPLICATION_MARKERS = (
    "why",
    "predict",
    "compare",
    "explain",
    "how does",
    "how would",
    "what would",
    "which would",
    "if ",
    "calculate",
    "versus",
    " vs ",
    "patient",
    "scenario",
    "would happen",
    "more likely",
    "best explains",
    "what happens",
    "derive",
)

# Fact cues -> declarative.
_DECLARATIVE_MARKERS = (
    "how many",
    "what is the",
    "what are the",
    "define",
    "list ",
    "name the",
    "name a",
    "where does",
    "where is",
    "what bond",
    "what type",
    "who ",
    "which gland",
    "which organelle",
    "which enzyme",
    "abbreviation",
)

_WORD = re.compile(r"\w+")


def _short_answer(answer: str) -> bool:
    a = answer.strip()
    if not a:
        return True
    if re.fullmatch(r"[\d\.\,/\-\s]+[a-zA-Z%]*", a):  # numeric-ish ("2 ATP", "7", "14")
        return True
    return len(_WORD.findall(a)) <= 3


def heuristic_classify(question: str, answer: str = "") -> CardType:
    """Deterministic classifier (AI-off path and the eval baseline)."""
    q = f" {question.lower().strip()} "
    if any(marker in q for marker in _APPLICATION_MARKERS):
        return CardType.APPLICATION
    if _short_answer(answer):
        return CardType.DECLARATIVE
    if any(marker in q for marker in _DECLARATIVE_MARKERS):
        return CardType.DECLARATIVE
    # Unsure with a longer answer: treat as application so we don't suppress a
    # potentially useful disconfirmer.
    return CardType.APPLICATION


#: Total recent misses (review lapses + repeated Again this session) that count as the
#: student "clearly struggling" with a card - at which point a disconfirmer is required
#: regardless of card type, because rote re-study is demonstrably not working.
STRUGGLE_THRESHOLD = 2


def should_prompt_disconfirmer(
    card_type: CardType,
    ease: int,
    *,
    trigger: str = "again_hard",
    misses: int = 0,
    struggle_threshold: int = STRUGGLE_THRESHOLD,
) -> bool:
    """Decide whether this miss should require a disconfirmer.

    Two paths into the prompt:

    - **First miss of an application/reasoning card** -> prompt. (A one-off slip on a pure
      fact is just re-studied, so a single declarative miss is left alone.)
    - **Clearly struggling** (``misses`` >= ``struggle_threshold`` - i.e. repeated Again or
      accumulated lapses on the *same* card) -> prompt regardless of type. Repeatedly
      failing a card is the signal that re-reading the fact isn't working and the deeper
      "what would flip this?" is the intervention that pays off.
    """
    fail_eases = {1, 2} if trigger == "again_hard" else {1}
    if ease not in fail_eases:
        return False
    if misses >= struggle_threshold:
        return True
    return card_type == CardType.APPLICATION
