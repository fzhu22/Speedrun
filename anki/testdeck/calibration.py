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

import _artifacts  # noqa: E402
import _fsrs_replay  # noqa: E402


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


def _card_reviews(col: Collection, search: str) -> list[list[tuple[float, int]]]:
    """Per held-out card, its ordered ``(elapsed_days, ease)`` reviews (from the revlog)."""
    cards = []
    for cid in col.find_cards(search):
        rows = col.db.all(
            "select lastIvl, ease from revlog where cid=? and type in (0,1,2) order by id",
            cid,
        )
        reviews = [(max(0.0, float(last)), int(ease)) for last, ease in rows]
        if len(reviews) >= 2:
            cards.append(reviews)
    return cards


def reliability_from_split(
    col: Collection, params: list[float], test_search: str
) -> dict | None:
    """Replay the held-out cards through FSRS (engine-fitted params) to get the reliability
    diagram data + Brier the engine's scalar can't provide. Returns None if unavailable."""
    if not params or len(params) < 17:
        return None
    preds: list[tuple[float, int]] = []
    for reviews in _card_reviews(col, test_search):
        preds.extend(_fsrs_replay.replay_card(params, reviews))
    if len(preds) < 10:
        return None
    bins = _fsrs_replay.reliability_bins(preds)
    return {
        "bins": bins,
        "brier": _fsrs_replay.brier(preds),
        "replay_rmse_bins": _fsrs_replay.rmse_bins(bins),
        "n_predicted_reviews": len(preds),
    }


def calibrate_split(col: Collection, train: str, test: str, label: str) -> dict | None:
    print(f"\n--- {label} ---")
    try:
        params, n_items = _fit(col, train)
    except Exception as exc:
        print(f"  could not fit FSRS on '{train}': {exc}")
        return None
    if not params:
        print(f"  not enough review history under '{train}' to fit FSRS.")
        return None
    train_reviews = _n_reviews(col, train)
    test_reviews = _n_reviews(col, test)
    print(f"  fit on '{train}': {train_reviews} reviews, {n_items} FSRS items")
    print(f"  {len(params)} parameters learned")

    ll_in, rmse_in = _evaluate(col, params, train)
    print(f"  in-sample (train) : log_loss={ll_in:.4f}  rmse_bins={rmse_in:.4f}")
    metrics: dict = {
        "params": params,
        "n_params": len(params),
        "train_reviews": train_reviews,
        "test_reviews": test_reviews,
        "in_sample": {"log_loss": ll_in, "rmse_bins": rmse_in},
    }
    if test_reviews:
        ll_out, rmse_out = _evaluate(col, params, test)
        print(f"  HELD-OUT (test)   : log_loss={ll_out:.4f}  rmse_bins={rmse_out:.4f}   <- reviews={test_reviews}")
        verdict = "calibrated" if rmse_out <= 0.10 else ("reasonable" if rmse_out <= 0.15 else "weak")
        print(f"  calibration error (held-out RMSE) = {rmse_out:.1%}  -> {verdict}")
        print("  interpretation: when FSRS says p% recall, observed recall is within")
        print(f"                  ~{rmse_out:.1%} of p% on the held-back reviews.")
        metrics["held_out"] = {"log_loss": ll_out, "rmse_bins": rmse_out, "verdict": verdict}
    else:
        print(f"  no held-out reviews found under '{test}'.")
    return metrics


def _write_calibration_artifact(metrics: dict, rel: dict | None) -> None:
    """Assemble the memory-calibration artifact (+ reliability SVG) for the report."""
    ho = metrics.get("held_out") or {}
    isamp = metrics.get("in_sample") or {}
    summary = [
        "Memory model = FSRS (the shared engine's scheduler). Fit on `calib::train`, "
        "evaluated on the untouched `calib::test` split (held out by card).",
    ]
    table = {
        "headers": ["Split", "log_loss", "rmse_bins (calibration error)", "reviews"],
        "rows": [
            [
                "in-sample (train)",
                f"{isamp.get('log_loss', 0):.4f}",
                f"{isamp.get('rmse_bins', 0):.4f}",
                metrics.get("train_reviews", 0),
            ],
        ],
    }
    verdict = None
    chart = None
    nulls = []
    if ho:
        table["rows"].append([
            "**held-out (test)**",
            f"{ho.get('log_loss', 0):.4f}",
            f"**{ho.get('rmse_bins', 0):.4f}**",
            metrics.get("test_reviews", 0),
        ])
        summary.append(
            f"Held-out calibration error (RMSE across probability bins) = "
            f"**{ho['rmse_bins']:.1%}**: when FSRS says p% recall, observed recall is "
            f"within ~{ho['rmse_bins']:.1%} of p% on reviews it never trained on."
        )
        gap = ho["rmse_bins"] - isamp.get("rmse_bins", 0)
        summary.append(
            f"Small train->test gap ({isamp.get('rmse_bins', 0):.1%} -> {ho['rmse_bins']:.1%}, "
            f"+{gap:.1%}) indicates it is calibrated, not overfit."
        )
        verdict = (
            f"{ho.get('verdict', '')} (held-out RMSE {ho['rmse_bins']:.1%}, "
            f"log_loss {ho['log_loss']:.3f})"
        )
    if rel:
        summary.append(
            f"Brier score on {rel['n_predicted_reviews']} held-out reviews = "
            f"**{rel['brier']:.3f}** (lower = better; a proper scoring rule)."
        )
        summary.append(
            f"Cross-check: the FSRS replay used for the chart gives rmse across bins "
            f"{rel['replay_rmse_bins']:.1%}, tracking the engine's authoritative "
            f"{ho.get('rmse_bins', float('nan')):.1%}."
        )
        svg = _artifacts.reliability_diagram_svg(
            rel["bins"],
            subtitle=f"held-out reviews (n={rel['n_predicted_reviews']}); "
            f"Brier {rel['brier']:.3f}",
        )
        _artifacts.write_svg("memory-calibration", svg)
        chart = "memory-calibration.svg"
    else:
        nulls.append(
            "The reliability-diagram replay was skipped (params not FSRS-shaped or too few "
            "held-out reviews); the engine's scalar rmse_bins/log_loss are still reported."
        )
    _artifacts.write_artifact(
        "memory-calibration",
        {
            "title": "Memory calibration on held-out reviews",
            "spec": "spec section 9 Step 1 / PRD AC3",
            "command": "just eval  (calibration.py --col testdeck/bench.anki2)",
            "model": "FSRS (synthetic bench revlog, labelled)",
            "seed": 7,
            "summary": summary,
            "table": table,
            "metrics": {
                "in_sample": isamp,
                "held_out": ho,
                "brier": (rel or {}).get("brier"),
                "n_params": metrics.get("n_params"),
                "reliability_bins": (rel or {}).get("bins"),
            },
            "chart": chart,
            "verdict": verdict,
            "nulls": nulls,
        },
    )
    print("\nwrote artifact: docs/eval-artifacts/memory-calibration.json"
          + (" + memory-calibration.svg" if chart else ""))


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
            metrics = calibrate_split(
                col, "tag:calib::train", "tag:calib::test",
                "synthetic bench deck (forgetting-curve revlog; held-out by card)",
            )
            if metrics:
                rel = reliability_from_split(col, metrics["params"], "tag:calib::test")
                _write_calibration_artifact(metrics, rel)
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
