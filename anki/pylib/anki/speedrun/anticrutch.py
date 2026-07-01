"""The AI anti-crutch kill-switch (brainlift SPOV 9).

The exam is taken unassisted, so an AI hint that lifts assisted performance while
lowering UNASSISTED performance is fatal (Bastani PNAS: -17% unassisted). We compare
later unaided review accuracy for disconfirmer cards authored WITH an AI hint vs those
authored WITHOUT, and disable AI hints if the assisted cohort trails by >= 5 pp.

Single-user detection is approximate (it is a within-learner cohort split, not a
volume-matched RCT); that limitation is stated honestly. Pure functions; the GUI
persists the state in the collection config.
"""

from __future__ import annotations

from typing import Dict, Optional

THRESHOLD = 0.05  # 5 percentage points
MIN_N = 5

State = Dict[str, Dict[str, int]]


def empty_state() -> State:
    return {"assisted": {"n": 0, "correct": 0}, "unassisted": {"n": 0, "correct": 0}}


def record_outcome(state: State, *, assisted: bool, correct: bool) -> None:
    """Record one later *unaided* review outcome for a disconfirmer card."""
    cohort = state.setdefault(
        "assisted" if assisted else "unassisted", {"n": 0, "correct": 0}
    )
    cohort["n"] = int(cohort.get("n", 0)) + 1
    if correct:
        cohort["correct"] = int(cohort.get("correct", 0)) + 1


def accuracy(cohort: Dict[str, int]) -> Optional[float]:
    n = int(cohort.get("n", 0))
    return (int(cohort.get("correct", 0)) / n) if n else None


def crutch_signature(state: State, *, threshold: float = THRESHOLD, min_n: int = MIN_N) -> bool:
    """True when AI-assisted cards trail unassisted ones on unaided review by >= threshold."""
    assisted = state.get("assisted", {})
    unassisted = state.get("unassisted", {})
    if int(assisted.get("n", 0)) < min_n or int(unassisted.get("n", 0)) < min_n:
        return False
    a_acc = accuracy(assisted)
    u_acc = accuracy(unassisted)
    if a_acc is None or u_acc is None:
        return False
    return (u_acc - a_acc) >= threshold


def should_offer_ai_hints(state: State) -> bool:
    return not crutch_signature(state)
