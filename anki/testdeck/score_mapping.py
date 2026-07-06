# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun readiness score mapping (spec section 9 Step 3), reproduced offline.

Applies the documented performance->MCAT method (see docs/score-mapping.md) so the projected
score + range is re-runnable outside the live UI and saved as an artifact. It reuses the
per-section accuracies from the performance eval artifact when present, else a clearly
labelled synthetic example, and mirrors `computeProjected` in the dashboard exactly.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import _artifacts  # noqa: E402

MCAT_MIN, MCAT_MAX = 472, 528
SECTION_MIN, SECTION_MAX = 118, 132
N_SECTIONS = 4


def to_section(acc: float) -> float:
    return SECTION_MIN + acc * (SECTION_MAX - SECTION_MIN)


def project(sections: list[dict]) -> dict:
    """sections: [{name, accuracy, low, high}]. Returns {score, low, high, covered}."""
    scored = [s for s in sections if s.get("accuracy") is not None]
    if not scored:
        return {}
    total = sum(to_section(s["accuracy"]) for s in scored)
    lo = sum(to_section(s.get("low", s["accuracy"])) for s in scored)
    hi = sum(to_section(s.get("high", s["accuracy"])) for s in scored)
    missing = max(0, N_SECTIONS - len(scored))
    mean, mean_lo, mean_hi = total / len(scored), lo / len(scored), hi / len(scored)

    def clamp(v: float) -> int:
        return round(min(MCAT_MAX, max(MCAT_MIN, v)))

    return {
        "score": clamp(total + missing * mean),
        "low": clamp(lo + missing * mean_lo),
        "high": clamp(hi + missing * mean_hi),
        "covered": len(scored),
        "imputed_sections": missing,
    }


def _wilson(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval - identical to the engine's `wilson_interval`
    (rslib/src/speedrun/dashboard.rs), so the offline projection's range matches the
    live UI exactly instead of a ballpark band."""
    if n <= 0:
        return (p, p)
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = (z / denom) * ((p * (1 - p) / n) + (z2 / (4 * n * n))) ** 0.5
    return (max(0.0, center - margin), min(1.0, center + margin))


def _sections_from_performance_artifact() -> tuple[list[dict], str]:
    """Per-section accuracy + true 95% Wilson bounds from performance.json (computed from
    the section item count n, matching the live engine). Falls back to a labelled synthetic
    worked example when the artifact is absent. Returns (sections, source_label)."""
    path = _artifacts.ARTIFACT_DIR / "performance.json"
    if path.exists():
        try:
            metrics = json.loads(path.read_text(encoding="utf-8")).get("metrics") or {}
            per = metrics.get("per_section")
            if per:
                secs = []
                for name, d in per.items():
                    acc, n = float(d["accuracy"]), int(d["n"])
                    lo, hi = _wilson(acc, n)
                    secs.append({"name": name, "accuracy": acc, "n": n, "low": lo, "high": hi})
                return secs, "performance.json (simulated responses; 95% Wilson bounds from n)"
            # Older artifact without per-section n: accuracy only, no invented band.
            per_acc = metrics.get("per_section_accuracy") or {}
            if per_acc:
                secs = [{"name": name, "accuracy": acc} for name, acc in per_acc.items()]
                return secs, "performance.json (accuracy only; no per-section n for a range)"
        except Exception:
            pass
    demo = [
        {"name": "BioBiochem", "accuracy": 0.62, "low": 0.53, "high": 0.72},
        {"name": "ChemPhys", "accuracy": 0.50, "low": 0.40, "high": 0.60},
        {"name": "PsychSoc", "accuracy": 0.48, "low": 0.38, "high": 0.58},
    ]
    return demo, "synthetic worked example (labelled)"


def main() -> None:
    sections, source = _sections_from_performance_artifact()
    proj = project(sections)

    print("=== Speedrun readiness score mapping (section 9 Step 3) ===")
    print(f"input sections ({source}):")
    for s in sections:
        print(f"  {s['name']:12s} acc={s['accuracy']:.1%} -> section {to_section(s['accuracy']):.1f}")
    if proj:
        print(f"projected MCAT: {proj['score']}  (likely {proj['low']}-{proj['high']})")
        print(f"covered sections: {proj['covered']}/{N_SECTIONS}  "
              f"(imputed {proj['imputed_sections']} at the covered mean, e.g. CARS)")

    _artifacts.write_artifact(
        "score-mapping",
        {
            "title": "Readiness score mapping (performance -> MCAT 472-528)",
            "spec": "spec section 9 Step 3",
            "command": "just eval  (score_mapping.py); method in docs/score-mapping.md",
            "model": _artifacts.OFFLINE_MODEL,
            "summary": [
                "Method (documented in docs/score-mapping.md): each covered section's "
                "held-out accuracy -> its MCAT band [118,132]; the four sections sum to "
                "[472,528]; uncovered sections (e.g. CARS) are imputed at the covered mean; "
                "the range is the summed section Wilson bounds.",
                f"Inputs from {source}.",
                (f"Projected MCAT **{proj['score']}** (likely **{proj['low']}-{proj['high']}**), "
                 f"from {proj['covered']}/{N_SECTIONS} covered sections "
                 f"({proj['imputed_sections']} imputed)." if proj else
                 "No performance data -> readiness abstains (no number shown)."),
            ],
            "metrics": {"sections": sections, "projection": proj},
            "verdict": (f"{proj['score']} ({proj['low']}-{proj['high']})" if proj else "abstains"),
            "nulls": [
                "This projection is an UNVALIDATED display-layer index: it is not anchored "
                "to real MCAT scores (section 9 Step 4 needs longitudinal student data).",
                "The uncovered-section imputation (CARS at the covered mean) is a stated "
                "assumption, not a measurement.",
            ],
        },
    )
    print("wrote artifact: docs/eval-artifacts/score-mapping.json")


if __name__ == "__main__":
    main()
