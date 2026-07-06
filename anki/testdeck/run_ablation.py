# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun study-feature ablation (spec section 8), on SIMULATED learners.

Section 8 wants a fair three-build test at EQUAL study time:
  1. full app        - the feature ON,
  2. feature-off     - the app with that one feature OFF (the ablation),
  3. plain Anki      - none of the Speedrun features (the baseline).

Real learners are not available in a week, so this runs simulated students with
literature-anchored, PRE-REGISTERED planted effects, purely to exercise the harness and
show what a fair comparison (with a range and honest nulls) looks like. It is clearly
labelled synthetic; it is NOT evidence the feature works on real students.

Feature under test: **pretest-first cards** (brainlift SPOV 2 - the strongest position,
cleanest item-level metric). Primary metric is stated BEFORE results.

    out/pyenv/Scripts/python testdeck/run_ablation.py
"""

from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import _artifacts  # noqa: E402

SEED = 7
N_STUDENTS = 80
N_PRETESTED_ITEMS = 24     # held-out items whose topic was pre-tested (the trained set)
N_UNTESTED_ITEMS = 24      # same-topic held-out items NOT pre-tested (spillover probe)
BOOTSTRAP = 2000

# --- PRE-REGISTERED design (declared before any result is computed) -----------------------
HYPOTHESIS = (
    "Introducing new material with a forced guess + immediate feedback (pretest-first) "
    "raises delayed accuracy on the PRETESTED items at equal study time, versus seeing the "
    "same cards study-first, with roughly zero spillover to untested same-topic items."
)
PRIMARY_METRIC = "delayed accuracy on held-out PRETESTED items, at equal study time"
FAILURE_CONDITION = (
    "If full <= feature-off on the pretested items at equal time (CI overlap), the pretest "
    "feature earns nothing here; if it also lifts untested items equally, the item-specific "
    "claim is wrong."
)
# Planted effects on the logit scale (labelled synthetic):
W_REVIEW = 0.40          # base learning from reviewing (all arms)
W_OTHER_FEATURES = 0.15  # Speedrun's non-pretest features (feature-off + full, all items)
W_PRETEST = 0.55         # pretest+feedback uplift, PRETESTED items only (~g0.3-0.4), full arm
W_SPILLOVER = 0.00       # planted ~0 spillover to untested items (an expected null)


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def _simulate(rng: random.Random):
    """Return per-arm, per-student mean accuracy on pretested and untested item sets."""
    students = [rng.gauss(0.0, 0.8) for _ in range(N_STUDENTS)]
    pre_diff = [rng.gauss(0.0, 0.6) for _ in range(N_PRETESTED_ITEMS)]
    unt_diff = [rng.gauss(0.0, 0.6) for _ in range(N_UNTESTED_ITEMS)]

    def arm(pretest_on: bool, other_on: bool):
        pre_scores, unt_scores = [], []
        for theta in students:
            # pretested items
            corr = 0
            for d in pre_diff:
                z = theta - d + W_REVIEW
                if other_on:
                    z += W_OTHER_FEATURES
                if pretest_on:
                    z += W_PRETEST
                corr += 1 if rng.random() < _sigmoid(z) else 0
            pre_scores.append(corr / len(pre_diff))
            # untested same-topic items (spillover probe)
            corr = 0
            for d in unt_diff:
                z = theta - d + W_REVIEW
                if other_on:
                    z += W_OTHER_FEATURES
                if pretest_on:
                    z += W_SPILLOVER
                corr += 1 if rng.random() < _sigmoid(z) else 0
            unt_scores.append(corr / len(unt_diff))
        return pre_scores, unt_scores

    return {
        "plain Anki": arm(pretest_on=False, other_on=False),
        "feature-off": arm(pretest_on=False, other_on=True),
        "full app": arm(pretest_on=True, other_on=True),
    }, students


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _bootstrap_ci(rng: random.Random, xs, iters=BOOTSTRAP):
    n = len(xs)
    means = []
    for _ in range(iters):
        means.append(_mean([xs[rng.randrange(n)] for _ in range(n)]))
    means.sort()
    return means[int(0.025 * iters)], means[int(0.975 * iters)]


def _cohens_d(a, b) -> float:
    na, nb = len(a), len(b)
    ma, mb = _mean(a), _mean(b)
    va = sum((x - ma) ** 2 for x in a) / (na - 1) if na > 1 else 0.0
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1) if nb > 1 else 0.0
    sp = math.sqrt(((na - 1) * va + (nb - 1) * vb) / max(1, na + nb - 2)) or 1e-9
    return (ma - mb) / sp


def main() -> None:
    rng = random.Random(SEED)
    arms, students = _simulate(rng)

    print("=== Speedrun study-feature ablation (SIMULATED learners; spec section 8) ===")
    print(f"feature under test: pretest-first cards (SPOV 2)")
    print(f"hypothesis (pre-registered): {HYPOTHESIS}")
    print(f"primary metric: {PRIMARY_METRIC}")
    print(f"students={N_STUDENTS}  pretested items={N_PRETESTED_ITEMS}  "
          f"untested items={N_UNTESTED_ITEMS}  (equal study time across arms)\n")

    ci_rng = random.Random(SEED + 1)
    pretested = {name: pre for name, (pre, _unt) in arms.items()}
    untested = {name: unt for name, (_pre, unt) in arms.items()}

    rows = []
    for name in ("plain Anki", "feature-off", "full app"):
        pre = pretested[name]
        m = _mean(pre)
        lo, hi = _bootstrap_ci(ci_rng, pre)
        rows.append((name, m, lo, hi))
        print(f"  {name:12s} pretested acc = {m:.1%}  (95% CI {lo:.1%}-{hi:.1%})")

    d_full_off = _cohens_d(pretested["full app"], pretested["feature-off"])
    d_full_plain = _cohens_d(pretested["full app"], pretested["plain Anki"])
    d_off_plain = _cohens_d(pretested["feature-off"], pretested["plain Anki"])
    # spillover: full vs feature-off on UNTESTED items (expect ~0)
    d_spillover = _cohens_d(untested["full app"], untested["feature-off"])

    print(f"\n  full vs feature-off (pretested)  d = {d_full_off:+.2f}   <- isolates the feature")
    print(f"  full vs plain Anki  (pretested)  d = {d_full_plain:+.2f}   <- whole-app effect")
    print(f"  feature-off vs plain (pretested) d = {d_off_plain:+.2f}   <- other features")
    print(f"  spillover: full vs feature-off (UNTESTED items) d = {d_spillover:+.2f}  (expect ~0)")

    # Secondary: the fading bet (SPOV 6) - a planted high-ability reversal, an honest null.
    fade_rng = random.Random(SEED + 2)
    order = sorted(range(len(students)), key=lambda i: students[i])
    top_q = set(order[int(0.75 * len(order)):])
    def fade_delta(high: bool) -> float:
        # fading uplift: helps low-prior (+0.30 logit), reverses for high-prior (-0.12)
        deltas = []
        for i, theta in enumerate(students):
            is_high = i in top_q
            if high != is_high:
                continue
            base = theta + W_REVIEW
            up = -0.12 if is_high else 0.30
            p_fixed = _sigmoid(base)
            p_fade = _sigmoid(base + up)
            deltas.append(p_fade - p_fixed)
        return _mean(deltas)
    fade_low = fade_delta(high=False)
    fade_high = fade_delta(high=True)
    print(f"\n  fading (SPOV 6, secondary): low-ability delta {fade_low:+.1%}, "
          f"high-ability delta {fade_high:+.1%}  (reversal for high-ability = the named null)")

    svg = _artifacts.bar_svg(
        [(n, m) for (n, m, _lo, _hi) in rows],
        title="Ablation: delayed accuracy on pretested items (equal time)",
        subtitle="SIMULATED learners (labelled); bars = mean, whiskers = 95% CI",
        ymax=1.0,
        ranges=[(lo, hi) for (_n, _m, lo, hi) in rows],
    )
    _artifacts.write_svg("ablation", svg)

    full_m = _mean(pretested["full app"])
    off_m = _mean(pretested["feature-off"])
    nulls = [
        f"Spillover null (expected): pretest gave ~0 lift on UNTESTED same-topic items "
        f"(full vs feature-off d={d_spillover:+.2f}) - the benefit is item-specific, not a "
        f"general topic boost.",
        f"Fading (SPOV 6) reverses for high-ability learners (delta {fade_high:+.1%} vs "
        f"{fade_low:+.1%} for low-ability) - the MCAT population is high-prior, so fading is "
        f"kept as a bet with a 'disable if fixed wins for high-ability' rule, not shipped as "
        f"a proven win.",
        "ALL numbers here are SIMULATED with planted effects (labelled). They demonstrate the "
        "harness and a fair comparison; they are NOT evidence the feature helps real "
        "students - that needs a real equal-time trial on unseen MCAT-style items.",
    ]

    _artifacts.write_artifact(
        "ablation",
        {
            "title": "Study-feature ablation: pretest-first (3 builds, equal time)",
            "spec": "spec section 8 (SIMULATED learners)",
            "command": "just eval  (run_ablation.py)",
            "model": _artifacts.OFFLINE_MODEL,
            "seed": SEED,
            "summary": [
                f"Feature under test: **pretest-first cards** (SPOV 2).",
                f"Pre-registered hypothesis: {HYPOTHESIS}",
                f"Primary metric: **{PRIMARY_METRIC}**. Failure condition: {FAILURE_CONDITION}",
                f"On pretested items: full app **{full_m:.1%}** vs feature-off **{off_m:.1%}** "
                f"vs plain Anki **{_mean(pretested['plain Anki']):.1%}** "
                f"(full vs feature-off d={d_full_off:+.2f}).",
                "Three arms at EQUAL study time; bootstrap 95% CIs shown; SIMULATED learners "
                "(labelled) - a harness demonstration, not a real-student result.",
            ],
            "table": {
                "headers": ["Arm", "Pretested acc", "95% CI"],
                "rows": [[n, f"{m:.1%}", f"{lo:.1%}-{hi:.1%}"] for (n, m, lo, hi) in rows],
            },
            "metrics": {
                "feature": "pretest-first",
                "hypothesis": HYPOTHESIS,
                "primary_metric": PRIMARY_METRIC,
                "failure_condition": FAILURE_CONDITION,
                "n_students": N_STUDENTS,
                "arms_pretested_mean": {n: m for (n, m, _l, _h) in rows},
                "arms_pretested_ci": {n: [lo, hi] for (n, _m, lo, hi) in rows},
                "d_full_vs_featureoff": d_full_off,
                "d_full_vs_plain": d_full_plain,
                "d_featureoff_vs_plain": d_off_plain,
                "spillover_d_untested": d_spillover,
                "fading_low_ability_delta": fade_low,
                "fading_high_ability_delta": fade_high,
                "planted_effects": {
                    "w_review": W_REVIEW, "w_other": W_OTHER_FEATURES,
                    "w_pretest": W_PRETEST, "w_spillover": W_SPILLOVER,
                },
            },
            "chart": "ablation.svg",
            "verdict": (f"full {full_m:.1%} vs feature-off {off_m:.1%} on pretested items "
                        f"(d={d_full_off:+.2f}); SIMULATED"),
            "nulls": nulls,
        },
    )
    print("\nwrote artifact: docs/eval-artifacts/ablation.json + ablation.svg")


if __name__ == "__main__":
    main()
