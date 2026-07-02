"""Speedrun: print the readiness-dashboard metrics with REAL numbers.

The dashboard shows "-" (abstain) for Memory until a section has cards in the FSRS
Review state (i.e. with a defined recall). A brand-new deck has none, which is why the
app shows the dash. This script seeds a *throwaway* collection with MCAT-tagged cards
placed in the Review state (varying stability + time-since-review), then prints the
`speedrun_dashboard` output so you can see:

  - Memory as a real per-section percentage,
  - the 95% range (wide when few cards back it, tight when many do),
  - Performance / Readiness still abstaining (honest, separate scores),
  - the coverage map and give-up gate.

Nothing here touches your real collection.

Run from the `anki/` folder using the dev environment:

    out\\pyenv\\Scripts\\python testdeck\\show_metrics.py      (Windows)
    out/pyenv/bin/python testdeck/show_metrics.py             (Mac/Linux)
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

# Import anki/aqt from the dev build (same paths tools/run.py uses).
sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]

# Import anki.collection first: it pulls in the whole module graph in the right order
# and avoids a circular import if anki.cards is imported on its own.
from anki.collection import Collection  # noqa: E402
from anki.cards import FSRSMemoryState  # noqa: E402
from anki.consts import CARD_TYPE_REV, QUEUE_TYPE_REV  # noqa: E402


def add_reviewed_card(
    col: Collection,
    deck_id: int,
    notetype: dict,
    tag: str,
    front: str,
    *,
    stability: float,
    days_since_review: float,
) -> None:
    """Add a card and force it into the Review state with an FSRS memory state, so it
    has a defined retrievability (mirrors the engine's own unit-test helper)."""
    note = col.new_note(notetype)
    note["Front"] = front
    note["Back"] = "answer"
    note.tags = [tag]
    col.add_note(note, deck_id)

    cid = col.card_ids_of_note(note.id)[0]
    card = col.get_card(cid)
    card.type = CARD_TYPE_REV
    card.queue = QUEUE_TYPE_REV
    card.ivl = max(1, round(stability))
    card.due = col.sched.today + card.ivl
    card.memory_state = FSRSMemoryState(stability=float(stability), difficulty=5.0)
    card.last_review_time = int(time.time()) - int(days_since_review * 86400)
    card.decay = None
    col.update_card(card)


def add_new_card(col: Collection, deck_id: int, notetype: dict, tag: str, front: str) -> None:
    """A brand-new (unreviewed) card: covered, but no recall yet -> abstains."""
    note = col.new_note(notetype)
    note["Front"] = front
    note["Back"] = "answer"
    note.tags = [tag]
    col.add_note(note, deck_id)


def fmt_pct(value: float | None) -> str:
    return "-" if value is None else f"{round(value * 100)}%"


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="speedrun_metrics_"))
    col = Collection(str(tmp / "collection.anki2"))
    try:
        basic = col.models.by_name("Basic")
        deck_id = col.decks.id("MCAT")

        # Bio/Biochem: many strong, recently-reviewed cards -> high recall, TIGHT range.
        for i in range(20):
            add_reviewed_card(
                col, deck_id, basic, "MCAT::BioBiochem::1A", f"bio {i}",
                stability=60.0, days_since_review=5 + (i % 10),
            )
        # Chem/Phys: only a few, older cards -> lower recall, WIDE range (little data).
        for i in range(3):
            add_reviewed_card(
                col, deck_id, basic, "MCAT::ChemPhys::5E", f"chem {i}",
                stability=20.0, days_since_review=15 + i * 8,
            )
        # Psych/Soc: covered but brand-new -> Memory abstains ("-"), by design.
        for i in range(4):
            add_new_card(col, deck_id, basic, "MCAT::PsychSoc::7A", f"psych {i}")

        res = col.speedrun_dashboard()

        print("\n=== Speedrun readiness dashboard (throwaway seeded collection) ===\n")
        print(
            f"Coverage: {fmt_pct(res.overall_coverage)} "
            f"({res.covered_leaves}/{res.total_leaves} content categories)   "
            f"total reviews: {res.total_reviews}\n"
        )
        header = f"{'Section':<14}{'Coverage':>9}{'Memory (95% range)':>26}{'n':>6}"
        print(header)
        print("-" * len(header))
        for s in res.sections:
            if s.HasField("memory"):
                rng = f"{fmt_pct(s.memory)} ({fmt_pct(s.memory_low)}-{fmt_pct(s.memory_high)})"
            else:
                rng = "-  (abstains: no reviewed cards)"
            print(f"{s.abbrev:<14}{fmt_pct(s.coverage):>9}{rng:>26}{s.reviewed_cards:>6}")

        print(f"\nPerformance: {res.performance_status}")
        print(f"Readiness:   {res.readiness_status}")
        print(
            "\nNote how Bio/Biochem (20 cards) has a tight range while Chem/Phys (3 cards)"
            "\nis wide, and Psych/Soc abstains until its cards are reviewed - the honest"
            "\n'don't imply more certainty than the data supports' behaviour.\n"
        )
    finally:
        col.close()


if __name__ == "__main__":
    main()
