# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun leakage check (spec 7e), as a first-class command with a saved artifact.

Leaked test data makes a model look smarter than it is - and the spec zeroes that score -
so the studied ("training") set and the held-out test items must not overlap. This scans:

  1. the 176 studied memory texts vs the 60 held-out reworded performance items, and
  2. the AI classifier's few-shot prompt examples vs the classifier gold set,

and reports the maximum near-duplicate overlap against the threshold. Both should be CLEAN
by construction (the reworded items share only the principle, not wording). The underlying
scan already runs inside eval_performance.py / run_ai_eval.py; this makes it a standalone,
saved check. Runs fully offline on the real testdeck texts (no key, no network).

    out/pyenv/Scripts/python testdeck/run_leakage_check.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ANKI = _HERE.parent
for _p in ("pylib", "out/pylib"):
    _full = _ANKI / _p
    if str(_full) not in sys.path:
        sys.path.insert(0, str(_full))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import _artifacts  # noqa: E402
from anki.speedrun import ai, ai_eval, performance as perf  # noqa: E402

MEMORY_CSVS = ["memory_bio_biochem.csv", "memory_chem_phys.csv", "memory_psych_soc.csv"]


def _studied_texts() -> list[str]:
    texts: list[str] = []
    for name in MEMORY_CSVS:
        path = _HERE / name
        if not path.exists():
            continue
        rows = [ln for ln in path.read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
        for row in csv.reader(rows):
            if len(row) >= 2:
                texts.append(f"{row[0]} {row[1]}")
    return texts


def _heldout_stems() -> list[str]:
    data = json.loads((_HERE / "performance_items.json").read_text(encoding="utf-8"))
    return [item["stem"] for c in data["concepts"] for item in c["items"]]


def main() -> None:
    studied = _studied_texts()
    heldout = _heldout_stems()
    perf_leak = perf.leakage_check(studied, heldout)

    fewshot_leak = ai_eval.fewshot_leakage(ai.FEWSHOT_EXAMPLES)

    print("=== Speedrun leakage check (spec 7e) ===")
    print(f"1) studied memory set ({len(studied)}) vs held-out items ({len(heldout)})")
    print(f"   max shingle overlap {perf_leak.max_overlap:.2f} "
          f"(threshold {perf.LEAKAGE_THRESHOLD}) -> "
          f"{'CLEAN' if perf_leak.clean else f'LEAK ({len(perf_leak.matches)})'}")
    print(f"2) AI few-shot prompt vs classifier gold ({len(ai_eval.CARD_TYPE_GOLD)})")
    print(f"   -> {'CLEAN' if fewshot_leak.clean else f'LEAK ({len(fewshot_leak.leaks)})'}")

    clean = perf_leak.clean and fewshot_leak.clean
    nulls = []
    if not clean:
        nulls.append(
            "Leakage was found - per the spec this ZEROES the affected score. The offending "
            "items must be removed from the studied/training set before any number is shown."
        )
    _artifacts.write_artifact(
        "leakage",
        {
            "title": "Leakage check: training vs held-out test items",
            "spec": "spec 7e",
            "command": "just eval  (run_leakage_check.py)",
            "model": _artifacts.OFFLINE_MODEL,
            "summary": [
                f"Studied memory set ({len(studied)} texts) vs held-out reworded items "
                f"({len(heldout)}): max shingle overlap **{perf_leak.max_overlap:.2f}** "
                f"(threshold {perf.LEAKAGE_THRESHOLD}) -> "
                f"**{'CLEAN' if perf_leak.clean else 'LEAK'}**.",
                f"AI few-shot prompt vs classifier gold "
                f"({len(ai_eval.CARD_TYPE_GOLD)} items): "
                f"**{'CLEAN' if fewshot_leak.clean else 'LEAK'}**.",
                "Runs on the real testdeck texts (no simulation). A clean result is required "
                "before any score is trusted.",
            ],
            "table": {
                "headers": ["Scan", "Max overlap", "Threshold", "Result"],
                "rows": [
                    ["studied vs held-out", f"{perf_leak.max_overlap:.2f}",
                     f"{perf.LEAKAGE_THRESHOLD}", "CLEAN" if perf_leak.clean else "LEAK"],
                    ["few-shot vs gold", "-", "0.80",
                     "CLEAN" if fewshot_leak.clean else "LEAK"],
                ],
            },
            "metrics": {
                "studied_vs_heldout_clean": perf_leak.clean,
                "studied_vs_heldout_max_overlap": perf_leak.max_overlap,
                "fewshot_vs_gold_clean": fewshot_leak.clean,
                "n_studied": len(studied),
                "n_heldout": len(heldout),
            },
            "verdict": "CLEAN" if clean else "LEAK FOUND",
            "nulls": nulls,
        },
    )
    print("wrote artifact: docs/eval-artifacts/leakage.json")


if __name__ == "__main__":
    main()
