# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: seed synthetic study progress so the dashboard's three scores show real
numbers instead of "LOCKED".

It unlocks each score the honest way the engine requires:

  * Memory     - gives sample cards across every section an FSRS memory state (stability +
                 last-review time), so per-section recall (and its Wilson range) computes.
  * Performance- seeds the exam-style Qbank if missing, adds graded answers whose
                 correctness carries latency signal beyond recall, then runs the real
                 incremental-validity gate (speedrun_fit_performance); Performance only
                 unlocks if the gate passes.
  * Readiness  - tops the review log up past the 200-review give-up line.

This is clearly-labelled synthetic demo data on the *sample* deck; it does not fabricate a
score, it just provides the reviews the gated engine needs. Close the desktop app first
(the collection is single-writer).

    out/pyenv/Scripts/python testdeck/seed_synthetic_progress.py            # default profile
    out/pyenv/Scripts/python testdeck/seed_synthetic_progress.py --col PATH
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANKI_ROOT = HERE.parent
os.chdir(ANKI_ROOT)
sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]

from anki.collection import Collection  # noqa: E402  (import first: initializes the package)
from anki.cards import FSRSMemoryState  # noqa: E402

CARD_TYPE_REV = 2
QUEUE_TYPE_REV = 2
SEED = 7
_DAY = 86_400


def _default_col() -> str:
    from aqt.profiles import ProfileManager

    base = Path(ProfileManager.get_created_base_folder(None))
    for prof in sorted(p.name for p in base.iterdir() if p.is_dir()):
        cand = base / prof / "collection.anki2"
        if cand.exists():
            return str(cand)
    return str(base / "User 1" / "collection.anki2")


def seed_memory(col: Collection, rng: random.Random) -> int:
    """Give every non-Qbank MCAT card an FSRS memory state so per-section recall computes."""
    cids = col.find_cards(
        'tag:MCAT::* -"note:Speedrun Performance Item" -"note:Speedrun Disconfirmer"'
    )
    now = int(time.time())
    today = col.sched.today  # days since collection creation
    updated = 0
    for cid in cids:
        card = col.get_card(cid)
        stability = rng.uniform(60.0, 220.0)  # days
        elapsed_days = rng.uniform(3.0, 130.0)  # -> recall spread ~0.75-0.98
        card.type = CARD_TYPE_REV
        card.queue = QUEUE_TYPE_REV
        card.ivl = max(1, int(stability))
        card.memory_state = FSRSMemoryState(
            stability=stability, difficulty=rng.uniform(4.0, 6.5)
        )
        card.last_review_time = now - int(elapsed_days * _DAY)
        # Make the cards due so the sample decks are actually studyable. A review card's
        # `due` is a day number; leaving it at the new-card position lands it past today,
        # which is why the decks showed "0 0 0". Due today keeps them reviewable while the
        # memory_state above still powers the per-section recall scores.
        card.due = today
        card.decay = None
        col.update_card(card)
        updated += 1
    return updated


def _revlog_rows(cid: int, base_id: int, answers: list[tuple[int, int]]) -> list[tuple]:
    """Build revlog rows (id, cid, usn, ease, ivl, lastIvl, factor, time, type)."""
    rows = []
    for i, (ease, latency_ms) in enumerate(answers):
        rows.append((base_id + i, cid, -1, ease, 1, 1, 2500, latency_ms, 1))
    return rows


def seed_performance(col: Collection, rng: random.Random) -> tuple[int, int]:
    """Seed the Qbank if missing, then add graded answers with latency signal so the
    incremental-validity gate can pass. Returns (perf_cards, responses)."""
    from anki.speedrun import seeding

    if not col.find_cards('"note:Speedrun Performance Item"'):
        seeding.seed_performance_deck(col)
    perf_cids = col.find_cards('"note:Speedrun Performance Item"')
    if not perf_cids:
        return 0, 0

    all_rows: list[tuple] = []
    base = int(time.time() * 1000) - 60 * _DAY * 1000
    responses = 0
    for ci, cid in enumerate(perf_cids):
        answers = []
        for _ in range(8):  # 8 graded answers per item
            latency_ms = int(rng.uniform(4000, 90000))
            lat_norm = min(1.0, latency_ms / 60000.0)
            # Correctness carries latency signal independent of recall, so the full
            # model (recall + latency + ...) beats a recall-only model out of sample.
            p_correct = 0.9 - 0.6 * lat_norm
            correct = rng.random() < p_correct
            answers.append((3 if correct else 1, latency_ms))
        rows = _revlog_rows(cid, base + ci * 1000, answers)
        all_rows.extend(rows)
        responses += len(rows)
    col.db.transact(
        lambda: col.db.executemany(
            "insert or ignore into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)"
            " values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            all_rows,
        )
    )
    return len(perf_cids), responses


# FSRS forgetting curve R(t) = (1 + FACTOR * t/S) ** DECAY, used only to synthesise
# believable review histories so the engine's FSRS calibration has data to train on.
_FACTOR = 19.0 / 81.0
_DECAY = -0.5


def _retr(elapsed_days: float, stability: float) -> float:
    if stability <= 0:
        return 0.0
    return (1.0 + _FACTOR * elapsed_days / stability) ** _DECAY


def _simulate_history(rng: random.Random, n_reviews: int) -> list[tuple]:
    """A believable FSRS history: list of (rel_ms, ease, ivl, last_ivl, type); rel_ms is the
    review time relative to the first review (a revlog id is the review time in ms)."""
    stability = rng.uniform(1.0, 6.0)
    events: list[tuple] = []
    rel = 0
    last_ivl = 0
    for r in range(n_reviews):
        if r == 0:
            true_r, rtype = 1.0, 0
        else:
            true_r, rtype = _retr(max(1.0, last_ivl), stability), 1
        passed = rng.random() < true_r
        ease = (3 if rng.random() < 0.85 else 4) if passed else 1
        if passed:
            stability *= rng.uniform(1.7, 2.8)
        else:
            stability = max(0.5, stability * 0.45)
            rtype = 2 if r > 0 else 0
        next_ivl = max(1, int(round(stability)))
        events.append((rel, ease, next_ivl, last_ivl, rtype))
        last_ivl = next_ivl
        rel += next_ivl * _DAY * 1000
    return events


def seed_review_histories(col: Collection, rng: random.Random, max_cards: int = 180) -> int:
    """Give memory cards multi-review forgetting-curve histories so the engine's FSRS
    calibration (Step 1) has trainable data. Returns the number of review rows added."""
    cids = list(
        col.find_cards('tag:MCAT::* -"note:Speedrun Performance Item" -"note:Speedrun Disconfirmer"')
    )[:max_cards]
    now_ms = int(time.time() * 1000)
    all_rows: list[tuple] = []
    for i, cid in enumerate(cids):
        events = _simulate_history(rng, rng.randint(6, 10))
        span = events[-1][0]
        # End the history 2-40 days ago; back-date the first review accordingly.
        first_ms = now_ms - rng.randint(2, 40) * _DAY * 1000 - span
        for rel, ease, ivl, last_ivl, rtype in events:
            rid = first_ms + rel + i  # +i disambiguates ids that share a timestamp
            all_rows.append((rid, cid, -1, ease, ivl, last_ivl, 2500, int(rng.uniform(3000, 20000)), rtype))
    if all_rows:
        col.db.transact(
            lambda: col.db.executemany(
                "insert or ignore into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)"
                " values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                all_rows,
            )
        )
    return len(all_rows)


def report(col: Collection) -> None:
    dash = col.speedrun_dashboard()
    print("\n=== Dashboard after seeding ===")
    print(f"coverage: {dash.overall_coverage:.0%}   total reviews: {dash.total_reviews}")
    print(f"readiness: {'ALLOWED' if dash.readiness_allowed else dash.readiness_status}")
    print(f"performance status: {dash.performance_status}")
    print("per-section:")
    for s in dash.sections:
        mem = f"{s.memory:.0%} ({s.memory_low:.0%}-{s.memory_high:.0%})" if s.memory else "-"
        perf = f"{s.performance:.0%}" if s.performance is not None else "-"
        print(f"  {s.abbrev:<12} memory={mem:<18} perf={perf:<6} items={s.performance_items}")
    if dash.HasField("evidence"):
        ev = dash.evidence
        print("evidence (Step 1 & 2):")
        if ev.HasField("memory_rmse"):
            print(
                f"  Step 1 memory calibration: RMSE={ev.memory_rmse:.1%} "
                f"log_loss={ev.memory_log_loss:.3f} reviews={ev.memory_reviews}"
            )
        else:
            print("  Step 1 memory calibration: not enough review history")
        print(
            f"  Step 2 performance model: AUC full={ev.perf_auc_full:.3f} "
            f"recall={ev.perf_auc_recall:.3f} delta={ev.perf_auc_delta:+.3f} passed={ev.perf_passed}"
        )
    else:
        print("evidence: none cached (run fit)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--col", default="")
    ap.add_argument("--min-reviews", type=int, default=220)
    args = ap.parse_args()
    rng = random.Random(SEED)

    col_path = args.col or _default_col()
    if not Path(col_path).exists():
        sys.exit(f"collection not found: {col_path}")
    print(f"seeding synthetic progress into: {col_path}")

    col = Collection(col_path)
    try:
        mem = seed_memory(col, rng)
        print(f"memory: set FSRS state on {mem} cards")
        perf_cards, responses = seed_performance(col, rng)
        print(f"performance: {perf_cards} Qbank cards, {responses} graded answers")
        hist = seed_review_histories(col, rng)
        print(f"calibration: added {hist} FSRS review-history rows")
        gate = col.speedrun_fit_performance()
        print(
            f"fit gate: {'PASS' if gate.passed else 'FAIL'} "
            f"(n={gate.n}, auc_full={gate.auc_full:.3f}, auc_recall={gate.auc_recall:.3f}, "
            f"delta={gate.delta:+.3f}, need n>={gate.min_responses} delta>={gate.min_delta:.2f})"
        )
        report(col)
    finally:
        col.close()
    print("\nDone. Reopen the desktop app to see the unlocked scores.")


if __name__ == "__main__":
    main()
