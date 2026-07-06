# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: the Performance-lane evaluation harness (spec 7d / 7e / section 9 Step 2).

Runs the four honesty checks for the memory->performance bridge and prints REAL numbers:

  1. Paraphrase test (7d): base-card recall vs reworded held-out accuracy per concept.
  2. Held-out accuracy + calibration (9.2): accuracy and Brier of the fitted model.
  3. Incremental-validity gate (SPOV 3): out-of-sample AUC of the full model vs a
     recall-only model - Performance ships only if the full model wins by the margin.
  4. Leakage (7e): near-duplicate overlap between the studied memory set and the held-out
     items (must be clean by design - the reworded items share only the principle).

The graded responses are **simulated** from a planted latent skill so the whole pipeline
is exercised without a week of real study data; this is clearly a development harness. In
production the same `anki.speedrun.performance` functions run on responses extracted from
the review log. The leakage check runs on the *real* testdeck texts, not simulated.

Run from the anki repo root with the dev env:

    out/pyenv/Scripts/python testdeck/eval_performance.py     # Windows
    out/pyenv/bin/python testdeck/eval_performance.py         # macOS/Linux
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANKI_ROOT = HERE.parent
sys.path[:0] = [str(ANKI_ROOT / "pylib"), str(ANKI_ROOT / "out" / "pylib")]

from anki.speedrun import performance as perf  # noqa: E402

import _artifacts  # noqa: E402

SEED = 7
MEMORY_CSVS = ["memory_bio_biochem.csv", "memory_chem_phys.csv", "memory_psych_soc.csv"]


def _sigmoid(z: float) -> float:
    import math

    return 1.0 / (1.0 + math.exp(-z))


def load_concepts() -> list:
    data = json.loads((HERE / "performance_items.json").read_text(encoding="utf-8"))
    return data["concepts"]


def studied_texts() -> list:
    texts = []
    for name in MEMORY_CSVS:
        path = HERE / name
        if not path.exists():
            continue
        rows = [ln for ln in path.read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
        for row in csv.reader(rows):
            if len(row) >= 2:
                texts.append(f"{row[0]} {row[1]}")
    return texts


def simulate_responses(concepts: list) -> list:
    """Plant a latent per-concept recall and application skill (application drives
    correctness more than recall), so the full model should beat recall-only - i.e. the
    gate can pass. This is SIMULATED demo data, clearly labelled."""
    rng = random.Random(SEED)
    responses: list = []
    recall_by_concept: dict = {}
    correct_by_concept: dict = {}
    for c in concepts:
        cid = c["concept_id"]
        section = c["section_tag"].split("::")[1] if "::" in c["section_tag"] else c["section_tag"]
        recall = rng.uniform(0.45, 0.95)
        # application skill: correlated with recall but with independent variance
        app = max(0.0, min(1.0, 0.5 * recall + 0.5 * rng.uniform(0.0, 1.0)))
        recall_by_concept[cid] = recall
        corrects = []
        for item in c["items"]:
            difficulty = rng.uniform(0.3, 0.8)
            p = _sigmoid(3.0 * (app - difficulty) + 1.2 * (recall - 0.6))
            correct = rng.random() < p
            corrects.append(1 if correct else 0)
            responses.append(
                perf.Response(
                    correct=correct,
                    recall=recall,
                    difficulty=difficulty,
                    latency_ms=int(rng.uniform(8000, 45000) * (0.5 + difficulty)),
                    coverage=0.77,
                    section=section,
                    concept=cid,
                )
            )
        correct_by_concept[cid] = sum(corrects) / len(corrects)
    return responses, recall_by_concept, correct_by_concept


def main() -> None:
    concepts = load_concepts()
    responses, recall_by_concept, acc_by_concept = simulate_responses(concepts)

    print("\n=== Speedrun Performance-lane eval (SIMULATED responses; leakage is real) ===\n")
    print(f"concepts: {len(concepts)}   held-out responses: {len(responses)}\n")

    # 1 + 2: paraphrase gap, held-out accuracy + calibration
    para = perf.paraphrase_gap(recall_by_concept, acc_by_concept)
    fit = perf.fit_and_serialize(responses)
    overall_acc = sum(1 for r in responses if r.correct) / len(responses)
    print("Paraphrase test (7d): base-card recall vs reworded accuracy")
    print(f"  mean recall   : {para.mean_recall:.1%}")
    print(f"  mean accuracy : {para.mean_accuracy:.1%}")
    print(f"  memory->perf gap : {para.mean_gap:+.1%}  (positive = recall overstates performance)")
    print()
    print("Held-out performance (9.2)")
    print(f"  accuracy : {overall_acc:.1%}")
    print(f"  Brier    : {fit['brier']:.3f}  (lower = better calibrated)")
    print()

    # 3: incremental-validity gate
    g = fit["gate"]
    print("Incremental-validity gate (SPOV 3): does application beat recall out-of-sample?")
    print(f"  AUC recall-only : {g['auc_recall']:.3f}")
    print(f"  AUC full model  : {g['auc_full']:.3f}")
    print(f"  delta           : {g['delta']:+.3f}  (need >= {g['min_delta']:.3f})")
    print(f"  n responses     : {g['n']}          (need >= {g['min_responses']})")
    print(f"  GATE            : {'PASS - Performance may ship' if g['passes'] else 'FAIL - keep abstaining'}")
    print()

    # 4: leakage (on the REAL texts)
    studied = studied_texts()
    heldout = [item["stem"] for c in concepts for item in c["items"]]
    leak = perf.leakage_check(studied, heldout)
    print("Leakage check (7e): studied memory set vs held-out items")
    print(f"  studied texts : {len(studied)}   held-out items : {len(heldout)}")
    print(f"  max overlap   : {leak.max_overlap:.2f}  (threshold {perf.LEAKAGE_THRESHOLD})")
    print(f"  result        : {'CLEAN' if leak.clean else f'LEAK ({len(leak.matches)} items)'}")
    print()
    print("Note: responses are SIMULATED to exercise the pipeline; the gate verdict is only")
    print("meaningful on real review-log data. Leakage is computed on the actual texts.\n")

    _write_performance_artifact(
        concepts, responses, para, fit, overall_acc, leak, len(studied), len(heldout)
    )


def _write_performance_artifact(
    concepts, responses, para, fit, overall_acc, leak, n_studied, n_heldout
) -> None:
    """Save the performance artifact + a per-section accuracy SVG for the report."""
    # per-section held-out accuracy (for the chart)
    by_section: dict = {}
    for r in responses:
        sec = r.section or "?"
        agg = by_section.setdefault(sec, [0, 0])
        agg[0] += 1 if r.correct else 0
        agg[1] += 1
    section_items = [
        (sec, corr / tot) for sec, (corr, tot) in sorted(by_section.items()) if tot
    ]
    # Per-section accuracy WITH the item count (n), so the offline score mapping can
    # compute the same Wilson bounds the live engine uses (not a ballpark stand-in).
    per_section = {
        sec: {"accuracy": corr / tot, "correct": corr, "n": tot}
        for sec, (corr, tot) in sorted(by_section.items())
        if tot
    }
    if section_items:
        svg = _artifacts.bar_svg(
            section_items,
            title="Held-out performance accuracy by section",
            subtitle="SIMULATED responses (exercises the pipeline; not real answers)",
            ymax=1.0,
        )
        _artifacts.write_svg("performance", svg)

    g = fit["gate"]
    _artifacts.write_artifact(
        "performance",
        {
            "title": "Performance model on held-out exam-style items",
            "spec": "spec 7d / 7e / section 9 Step 2",
            "command": "just eval  (eval_performance.py)",
            "model": "logistic P(correct); responses SIMULATED (labelled)",
            "seed": SEED,
            "summary": [
                f"Held-out accuracy on {len(responses)} reworded items: "
                f"**{overall_acc:.1%}** (Brier {fit['brier']:.3f}; lower = better calibrated).",
                f"Paraphrase test (7d): mean card recall {para.mean_recall:.1%} vs reworded "
                f"accuracy {para.mean_accuracy:.1%} -> gap **{para.mean_gap:+.1%}** "
                f"(recall and performance are not identical, so performance is not a copy "
                f"of memory).",
                f"Incremental-validity gate (SPOV 3): out-of-sample AUC full model "
                f"{g['auc_full']:.3f} vs recall-only {g['auc_recall']:.3f}, delta "
                f"**{g['delta']:+.3f}** (need >= {g['min_delta']:.2f}), n={g['n']} -> "
                f"{'PASS' if g['passes'] else 'FAIL'}.",
                f"Leakage (7e): {n_studied} studied texts vs {n_heldout} held-out items, "
                f"max shingle overlap {leak.max_overlap:.2f} "
                f"(threshold {perf.LEAKAGE_THRESHOLD}) -> "
                f"{'CLEAN' if leak.clean else 'LEAK'} (real texts).",
            ],
            "table": {
                "headers": ["Metric", "Value", "Bar / need"],
                "rows": [
                    ["held-out accuracy", f"{overall_acc:.1%}", ""],
                    ["Brier", f"{fit['brier']:.3f}", "lower better"],
                    ["AUC full vs recall", f"{g['auc_full']:.3f} vs {g['auc_recall']:.3f}",
                     f"delta {g['delta']:+.3f}"],
                    ["incremental-validity gate", "PASS" if g["passes"] else "FAIL",
                     f">= {g['min_delta']:.2f}, n>={g['min_responses']}"],
                    ["leakage", "CLEAN" if leak.clean else "LEAK", f"overlap {leak.max_overlap:.2f}"],
                ],
            },
            "metrics": {
                "accuracy": overall_acc,
                "brier": fit["brier"],
                "gate": g,
                "paraphrase_gap": para.mean_gap,
                "leakage_clean": leak.clean,
                "leakage_max_overlap": leak.max_overlap,
                "n_responses": len(responses),
                "per_section_accuracy": {s: v for s, v in section_items},
                "per_section": per_section,
            },
            "chart": "performance.svg" if section_items else None,
            "verdict": ("PASS - Performance may ship" if g["passes"]
                        else "ABSTAIN - gate not cleared"),
            "nulls": [
                "The accuracy/Brier here are on SIMULATED responses (planted latent skill) "
                "to exercise the pipeline; they are NOT measured on real student answers. "
                "On a fresh real deck the engine's Performance score abstains until >= 5 "
                "graded items per section exist.",
                f"The memory->performance gap is small ({para.mean_gap:+.1%}): recall only "
                "modestly overstates performance on this synthetic set, so the case that "
                "performance is a distinct construct is suggestive here, not decisive.",
            ],
        },
    )
    print("wrote artifact: docs/eval-artifacts/performance.json"
          + (" + performance.svg" if section_items else ""))


if __name__ == "__main__":
    main()
