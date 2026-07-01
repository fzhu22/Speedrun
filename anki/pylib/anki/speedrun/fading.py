"""Support-fading guidance ladder - display helpers (PRD Section 6.3 / brainlift SPOV 10).

Scaffolding fades per concept-family as competence grows: heavy support helps novices
but hurts experts (expertise-reversal). The advance/regress *mutation* on each review
now lives in the shared Rust engine (``speedrun_record_review``); what remains here is
what the desktop authoring dialog reads to render the rung:

* the :class:`Rung` ladder and its per-rung :data:`RUNG_GUIDANCE`, :data:`EXEMPLAR`, and
  :data:`PERTURBATION_CHECKLIST`;
* :func:`estimate_rung`, the **conservative** initial estimate from the Rust
  ``topic_mastery`` recall signal - it never starts at mastery (L0), because mastery
  estimates over-predict, so L0 is only reachable by demonstrated advancement;
* :func:`current_rung`, which reads the persisted per-family state (declarative-recall
  families opt out and report L1).

No Anki/Qt imports here so it is unit-testable in isolation.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional


class Rung(str, Enum):
    """Scaffolding level, most support (L3) to least (L0)."""

    L3 = "L3"  # Guided
    L2 = "L2"  # Assisted
    L1 = "L1"  # Independent
    L0 = "L0"  # Mastery


#: What the authoring dialog should surface at each rung.
RUNG_GUIDANCE: Dict[Rung, Dict[str, object]] = {
    Rung.L3: {
        "label": "L3 - Guided",
        "summary": "New or weak family: full scaffold, a worked exemplar, and the perturbation checklist.",
        "show_exemplar": True,
        "show_checklist": True,
    },
    Rung.L2: {
        "label": "L2 - Assisted",
        "summary": "Improving: prompts and an exemplar available on demand.",
        "show_exemplar": False,
        "show_checklist": True,
    },
    Rung.L1: {
        "label": "L1 - Independent",
        "summary": "Competent: required fields and disconfirmer validation only.",
        "show_exemplar": False,
        "show_checklist": False,
    },
    Rung.L0: {
        "label": "L0 - Mastery",
        "summary": "Mastered: minimal checklist; the disconfirmer is still required.",
        "show_exemplar": False,
        "show_checklist": False,
    },
}

#: A worked exemplar shown at L3 (a good disconfirmer names what would flip the answer).
EXEMPLAR = (
    "Q: A weak acid HA has pKa 4.8. At pH 4.8, which dominates?  Answer: [HA] = [A-].  "
    "Disconfirmer: if the pH rose above the pKa, A- would dominate (Henderson-Hasselbalch) "
    "- so the answer flips when pH crosses the pKa."
)

#: Surface dimensions to vary while holding the deep principle fixed.
PERTURBATION_CHECKLIST = [
    "cover-story / context",
    "named entities",
    "units",
    "numeric values",
    "question framing / polarity",
    "representation (prose <-> diagram)",
]


def estimate_rung(avg_recall: Optional[float]) -> Rung:
    """Initial rung from the per-family average FSRS recall (None = no data).

    Conservative by design: the initial estimate is capped at L1 and never seeds L0 from
    recall alone, because per-family mastery estimates over-predict mastery and would fade
    support too early. Reaching L0 (mastery) requires demonstrated unaided + transfer wins.
    """
    if avg_recall is None:
        return Rung.L3
    if avg_recall < 0.6:
        return Rung.L3
    if avg_recall < 0.85:
        return Rung.L2
    return Rung.L1  # conservative cap; L0 only via demonstrated advancement


# -- per-family state (persisted by the shared engine in col config) ----------
#: The fading state the Rust engine writes; ``current_rung`` reads it for display.
State = Dict[str, Dict[str, object]]


def current_rung(
    state: State, family: str, avg_recall: Optional[float] = None, *, declarative: bool = False
) -> Rung:
    """The family's current rung; declarative families stay at L1 (no ladder).

    A read helper only: the advance/regress mutation lives in the Rust engine now. When
    the family has no persisted rung yet, fall back to the conservative initial estimate.
    """
    if declarative:
        return Rung.L1
    entry = state.get(family)
    if entry and "rung" in entry:
        return Rung(str(entry["rung"]))
    return estimate_rung(avg_recall)
