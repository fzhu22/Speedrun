# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: build a large benchmark collection (spec 7h / section 10 / section 9 Step 1).

Creates a single ``.anki2`` collection with:

  * ~50,000 memory cards fanned out from the original ``[Sample]`` content across the
    AAMC content categories (tagged ``MCAT::<code>``), so the dashboard, scheduler, and
    memory footprint are exercised on a realistic large deck; and
  * a smaller **calibration set** whose review log is synthesised from a genuine
    forgetting curve (tagged ``calib::train`` / ``calib::test``), so
    ``calibration.py`` can fit FSRS on the train split and measure calibration on the
    held-back test split (section 9 Step 1).

The cards are procedurally generated, clearly-labelled ``[Sample]`` content - no
copyrighted stems are stored. This is a development fixture; the product ships no deck.

Run from the anki repo root with the built env:

    out/pyenv/Scripts/python testdeck/build_bench_deck.py                 # Windows
    out/pyenv/bin/python     testdeck/build_bench_deck.py                 # macOS/Linux

Options:
    --out PATH            where to write the collection (default: testdeck/bench.anki2)
    --cards N             number of memory cards to generate (default: 50000)
    --calib-cards N       number of calibration cards with synthetic revlog (default: 800)
    --reviews-per N       mean reviews per calibration card (default: 9)
    --seed N              RNG seed (default: 7)
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

from anki.collection import Collection  # noqa: E402
from anki.speedrun.sample_content import SAMPLE_CARDS  # noqa: E402

# FSRS-style forgetting curve R(t) = (1 + FACTOR * t/S) ** DECAY (FSRS defaults), used
# only to *generate* believable review outcomes; FSRS then has to recover calibration.
_FACTOR = 19.0 / 81.0
_DECAY = -0.5
_DAY_MS = 86_400_000


def _retrievability(elapsed_days: float, stability: float) -> float:
    if stability <= 0:
        return 0.0
    return (1.0 + _FACTOR * elapsed_days / stability) ** _DECAY


def _categories() -> list[str]:
    """AAMC content-category codes present in the sample content, in a stable order."""
    return sorted(SAMPLE_CARDS.keys())


def add_memory_cards(col: Collection, n: int) -> int:
    """Fan the sample Q/A out to ``n`` unique cards tagged ``MCAT::<code>`` so the
    dashboard/coverage/scheduler run against a realistic large deck."""
    basic = col.models.by_name("Basic")
    did = col.decks.id("Speedrun Bench")
    cats = _categories()
    pairs_by_cat = {c: SAMPLE_CARDS[c] for c in cats}
    added = 0
    i = 0
    while added < n:
        code = cats[i % len(cats)]
        pairs = pairs_by_cat[code]
        front, back = pairs[(i // len(cats)) % len(pairs)]
        rep = i // (len(cats) * len(pairs))
        note = col.new_note(basic)
        # Unique front so notes are not deduplicated by checksum.
        note["Front"] = f"{front} [#{rep}-{code}]"
        note["Back"] = back
        note.tags = [f"MCAT::{code}"]
        col.add_note(note, did)
        added += 1
        i += 1
        if added % 5000 == 0:
            print(f"  memory cards: {added}/{n}")
    return added


def _simulate_revlog(rng: random.Random, cid: int, base_ms: int, n_reviews: int) -> list[tuple]:
    """Generate a plausible review history for one card from a forgetting curve.

    Returns a list of revlog rows (id, cid, usn, ease, ivl, lastIvl, factor, time, type).
    Reviews are back-dated: the card is first seen ~n_reviews scheduling steps ago and
    reviewed at intervals ~ its current stability (so true recall sits near ~90%).
    """
    rows: list[tuple] = []
    stability = rng.uniform(1.0, 4.0)  # initial memory strength in days
    difficulty = rng.uniform(3.0, 7.0)
    # Start far enough in the past that all reviews land before "now".
    t_ms = base_ms
    last_ivl = 0
    for r in range(n_reviews):
        if r == 0:
            elapsed_days = 0.0
            true_r = 1.0  # first exposure (learning)
            rtype = 0
        else:
            elapsed_days = max(1.0, last_ivl)
            true_r = _retrievability(elapsed_days, stability)
            rtype = 1
        passed = rng.random() < true_r
        ease = (3 if rng.random() < 0.8 else 4) if passed else 1
        # Update stability: growth on success (bigger when harder-but-recalled), lapse on fail.
        if passed:
            gain = 1.0 + (0.9 + 0.6 * rng.random()) * (1.0 + (5.0 - min(difficulty, 5.0)) * 0.1)
            stability *= max(1.2, gain)
        else:
            stability = max(0.5, stability * 0.4)
            rtype = 2 if r > 0 else 0
        next_ivl = max(1, int(round(stability)))
        rid = t_ms + r  # unique within a card; base_ms already unique per card
        rows.append((rid, cid, 0, ease, next_ivl, last_ivl, 0, int(rng.uniform(3000, 20000)), rtype))
        last_ivl = next_ivl
        t_ms += next_ivl * _DAY_MS
    return rows


def add_calibration_cards(
    col: Collection, n: int, mean_reviews: int, rng: random.Random
) -> tuple[int, int]:
    """Add ``n`` cards with synthetic forgetting-curve revlog, split 80/20 into
    ``calib::train`` / ``calib::test``. Returns (cards, revlog_rows)."""
    basic = col.models.by_name("Basic")
    did = col.decks.id("Speedrun Calib")
    cats = _categories()
    now_ms = int(time.time() * 1000)
    # First review starts this many days ago, with room for the whole history to fit.
    start_ms = now_ms - 400 * _DAY_MS
    all_rows: list[tuple] = []
    for i in range(n):
        code = cats[i % len(cats)]
        note = col.new_note(basic)
        note["Front"] = f"[Calib] item {i} ({code})"
        note["Back"] = f"answer {i}"
        split = "calib::train" if (i % 5) != 0 else "calib::test"
        note.tags = [f"MCAT::{code}", "calib", split]
        col.add_note(note, did)
        cid = note.cards()[0].id
        # Spread each card's history start so revlog ids never collide across cards.
        base = start_ms + i * (mean_reviews + 4)
        n_rev = max(3, int(rng.gauss(mean_reviews, 1.5)))
        all_rows.extend(_simulate_revlog(rng, cid, base, n_rev))
        if (i + 1) % 200 == 0:
            print(f"  calib cards: {i + 1}/{n}")
    col.db.transact(
        lambda: col.db.executemany(
            "insert or ignore into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)"
            " values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            all_rows,
        )
    )
    return n, len(all_rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "bench.anki2"))
    ap.add_argument("--cards", type=int, default=50_000)
    ap.add_argument("--calib-cards", type=int, default=800)
    ap.add_argument("--reviews-per", type=int, default=9)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--skip-if-exists", action="store_true", help="do nothing if --out already exists")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists() and args.skip_if_exists:
        print(f"benchmark collection already exists at {out} (skipping build)")
        return
    if out.exists():
        out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    t0 = time.time()
    col = Collection(str(out))
    try:
        print(f"Building benchmark collection at {out}")
        n_mem = add_memory_cards(col, args.cards)
        n_cal, n_rev = add_calibration_cards(col, args.calib_cards, args.reviews_per, rng)
    finally:
        col.close()

    dt = time.time() - t0
    size_mb = out.stat().st_size / (1024 * 1024)
    print("\nDone.")
    print(f"  memory cards      : {n_mem}")
    print(f"  calibration cards : {n_cal}  (80% train / 20% test)")
    print(f"  synthetic reviews : {n_rev}")
    print(f"  file size         : {size_mb:.1f} MB")
    print(f"  build time        : {dt:.1f}s")
    print(f"\nUse it:  out/pyenv/Scripts/python testdeck/bench.py --col {out}")
    print(f"         out/pyenv/Scripts/python testdeck/calibration.py --col {out}")


if __name__ == "__main__":
    main()
