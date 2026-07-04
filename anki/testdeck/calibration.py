# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: memory-model calibration on held-back reviews (section 9 Step 1).

Step 1 of the score bridge is: *show the memory model is calibrated* - when it says 80%,
the student recalls about 80% of the time - and prove it on **held-back** reviews.

The memory model is FSRS (the shared engine's scheduler). This harness:

  1. fits FSRS parameters on the ``calib::train`` split of the benchmark deck, then
  2. evaluates those parameters on the untouched ``calib::test`` split, reporting the
     engine's own calibration metrics:
       * log_loss  - a proper scoring rule (lower is better), and
       * rmse_bins - the ROOT-MEAN-SQUARE calibration error across probability bins, i.e.
         the numeric summary of a reliability diagram: how far predicted recall sits from
         observed recall. Small rmse_bins == "says 80% -> recalls ~80%".

Held-out (train-fit, test-evaluated) vs in-sample (train/train) is printed side by side so
overfitting would show up as a gap. The synthetic revlog is generated from a genuine
forgetting curve (see build_bench_deck.py) and is clearly labelled; pass ``--real`` to
also run in-sample calibration on your own collection's real review history.

Run from the anki repo root:

    out/pyenv/Scripts/python testdeck/calibration.py --col testdeck/bench.anki2
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANKI_ROOT = HERE.parent
os.chdir(ANKI_ROOT)
sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]

from anki.collection import Collection  # noqa: E402


def _fit(col: Collection, search: str) -> tuple[list[float], int]:
    resp = col._backend.compute_fsrs_params(
        search=search,
        current_params=[],
        ignore_revlogs_before_ms=0,
        num_of_relearning_steps=0,
        health_check=False,
    )
    return list(resp.params), int(resp.fsrs_items)


def _evaluate(col: Collection, params: list[float], search: str) -> tuple[float, float]:
    resp = col._backend.evaluate_params_legacy(
        params=params, search=search, ignore_revlogs_before_ms=0
    )
    return float(resp.log_loss), float(resp.rmse_bins)


def _n_reviews(col: Collection, search: str) -> int:
    cids = col.find_cards(search)
    if not cids:
        return 0
    placeholders = ",".join("?" for _ in cids)
    return col.db.scalar(
        f"select count() from revlog where cid in ({placeholders}) and type in (0,1,2)",
        *cids,
    ) or 0


def calibrate_split(col: Collection, train: str, test: str, label: str) -> None:
    print(f"\n--- {label} ---")
    try:
        params, n_items = _fit(col, train)
    except Exception as exc:
        print(f"  could not fit FSRS on '{train}': {exc}")
        return
    if not params:
        print(f"  not enough review history under '{train}' to fit FSRS.")
        return
    train_reviews = _n_reviews(col, train)
    test_reviews = _n_reviews(col, test)
    print(f"  fit on '{train}': {train_reviews} reviews, {n_items} FSRS items")
    print(f"  {len(params)} parameters learned")

    ll_in, rmse_in = _evaluate(col, params, train)
    print(f"  in-sample (train) : log_loss={ll_in:.4f}  rmse_bins={rmse_in:.4f}")
    if test_reviews:
        ll_out, rmse_out = _evaluate(col, params, test)
        print(f"  HELD-OUT (test)   : log_loss={ll_out:.4f}  rmse_bins={rmse_out:.4f}   <- reviews={test_reviews}")
        verdict = "calibrated" if rmse_out <= 0.10 else ("reasonable" if rmse_out <= 0.15 else "weak")
        print(f"  calibration error (held-out RMSE) = {rmse_out:.1%}  -> {verdict}")
        print("  interpretation: when FSRS says p% recall, observed recall is within")
        print(f"                  ~{rmse_out:.1%} of p% on the held-back reviews.")
    else:
        print(f"  no held-out reviews found under '{test}'.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--col", default=str(HERE / "bench.anki2"))
    ap.add_argument("--real", default="", help="optional path to a real collection for in-sample calibration")
    args = ap.parse_args()

    print("=== Speedrun memory calibration (section 9 Step 1) ===")
    print("Memory model = FSRS. Lower log_loss / rmse_bins = better calibrated.")

    col_path = str(Path(args.col).resolve())
    if Path(col_path).exists():
        col = Collection(col_path)
        try:
            calibrate_split(
                col, "tag:calib::train", "tag:calib::test",
                "synthetic bench deck (forgetting-curve revlog; held-out by card)",
            )
        finally:
            col.close()
    else:
        print(f"\nbench collection not found: {col_path} (run build_bench_deck.py first)")

    if args.real:
        real_path = str(Path(args.real).resolve())
        if Path(real_path).exists():
            col = Collection(real_path)
            try:
                # No holdout tags on a real deck -> in-sample only (optimistic), labelled.
                calibrate_split(col, "deck:*", "deck:*", "your real collection (IN-SAMPLE only)")
            finally:
                col.close()
        else:
            print(f"\nreal collection not found: {real_path}")

    print("\nNote: the bench revlog is synthetic (labelled). Real-student calibration over")
    print("time is section 9 Step 4 (bonus) and is not claimed here.\n")


if __name__ == "__main__":
    main()
