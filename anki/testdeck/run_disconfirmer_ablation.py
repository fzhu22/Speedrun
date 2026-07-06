# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun DISCONFIRMER ablation (spec section 8), on SIMULATED learners.

Companion to ``run_ablation.py`` (which tests pretest-first, SPOV 2). This one tests the
second custom study feature - the in-review **disconfirmer** (brainlift SPOV 5): after a
miss on an application card the student must retrieve and name "what one fact would flip
this answer?", then gets the answer + the disconfirmer as mandatory feedback.

Section 8 wants a fair three-build test at EQUAL study time:
  1. full app     - the disconfirmer prompt ON,
  2. feature-off  - Speedrun with the disconfirmer OFF (other features on),
  3. plain Anki   - none of the Speedrun features (the baseline).

Real learners are not available in a week, so this runs simulated students with
literature-anchored, PRE-REGISTERED planted effects, purely to exercise the harness and
show what a fair comparison (with a range and honest nulls) looks like. It is clearly
labelled synthetic; it is NOT evidence the disconfirmer helps real students, and the
disconfirmer FORMAT itself is explicitly unvalidated in the brainlift (SPOV 5).

Why the effect is planted on TRANSFER, not recall: the disconfirmer is student-authored,
active retrieval of the boundary condition + mandatory feedback, so its mechanism targets
delayed transfer (surface-reworded / boundary-shifted items). It is planted there
(anchored to Pan 2023 authored>premade application d~0.29 + elaborative interrogation)
and at ~0 on verbatim recall of the same facts - an expected null that keeps the claim
transfer-specific rather than a general effort/time effect.

    out/pyenv/Scripts/python testdeck/run_disconfirmer_ablation.py
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import _artifacts  # noqa: E402

SEED = 7
N_STUDENTS = 80
N_TRANSFER_ITEMS = 24  # reworded / boundary-shifted application items (the target set)
N_RECALL_ITEMS = 24    # verbatim recall of the same facts (transfer-specific null probe)
BOOTSTRAP = 2000

# --- PRE-REGISTERED design (declared before any result is computed) -----------------------
HYPOTHESIS = (
    "Prompting for a disconfirmer (name the one fact that would flip the answer) on "
    "application-card misses raises delayed TRANSFER accuracy on surface-reworded / "
    "boundary-shifted items at equal study time, versus the same cards reviewed without the "
    "prompt, with roughly zero lift on verbatim recall of the same facts."
)
PRIMARY_METRIC = (
    "delayed accuracy on held-out TRANSFER (reworded / boundary-shifted) items, at equal "
    "study time"
)
FAILURE_CONDITION = (
    "If full <= feature-off on transfer items at equal time (CI overlap), the disconfirmer "
    "earns nothing here; if it lifts verbatim-recall items equally, the transfer-specific "
    "claim is wrong (it is a general effort/time effect, not the disconfirmer mechanism)."
)
# Planted effects on the logit scale (labelled synthetic; anchors in comments):
W_REVIEW = 0.40          # base learning from reviewing (all arms)
W_OTHER_FEATURES = 0.15  # Speedrun's non-disconfirmer features (feature-off + full)
W_DISC_TRANSFER = 0.34   # disconfirmer uplift on TRANSFER items only, full arm. Anchored to
                         # Pan 2023 authored>premade application d~0.29 + elaborative-
                         # interrogation/active-retrieval on transfer; deliberately smaller
                         # than pretest's item-specific effect (transfer is a harder win).
W_DISC_RECALL = 0.00     # planted ~0 on verbatim recall (transfer-specific; expected null)
# Secondary: the AI-hint CRUTCH signature (SPOV 5 kill-switch). Anchored to Bastani 2024:
# AI assistance raised assisted performance but cut unassisted performance ~17%, and a
# guard-railed tutor removed the penalty. The disconfirmer's AI-hint lane is governed by
# exactly this unaided-performance check.
W_ASSIST_INSESSION = 0.55  # an AI hint inflates the assisted (in-session) score...
W_ASSIST_UNAIDED = -0.50   # ...but lowers later UNAIDED transfer -> the crutch signature
                           # (Bastani 2024 measured ~-17% unaided; a level this strong trips
                           # the kill-switch, which is the point of instrumenting it)
CRUTCH_KILL_THRESHOLD = 0.05  # disable any AI level whose users do >=5 pts worse unaided


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def _simulate(rng: random.Random):
    """Per-arm, per-student mean accuracy on the transfer and verbatim-recall item sets."""
    students = [rng.gauss(0.0, 0.8) for _ in range(N_STUDENTS)]
    tr_diff = [rng.gauss(0.0, 0.6) for _ in range(N_TRANSFER_ITEMS)]
    rc_diff = [rng.gauss(0.0, 0.6) for _ in range(N_RECALL_ITEMS)]

    def arm(disc_on: bool, other_on: bool):
        tr_scores, rc_scores = [], []
        for theta in students:
            # transfer items (the disconfirmer's target)
            corr = 0
            for d in tr_diff:
                z = theta - d + W_REVIEW
                if other_on:
                    z += W_OTHER_FEATURES
                if disc_on:
                    z += W_DISC_TRANSFER
                corr += 1 if rng.random() < _sigmoid(z) else 0
            tr_scores.append(corr / len(tr_diff))
            # verbatim recall of the same facts (transfer-specific null probe)
            corr = 0
            for d in rc_diff:
                z = theta - d + W_REVIEW
                if other_on:
                    z += W_OTHER_FEATURES
                if disc_on:
                    z += W_DISC_RECALL
                corr += 1 if rng.random() < _sigmoid(z) else 0
            rc_scores.append(corr / len(rc_diff))
        return tr_scores, rc_scores

    return {
        "plain Anki": arm(disc_on=False, other_on=False),
        "feature-off": arm(disc_on=False, other_on=True),
        "full app": arm(disc_on=True, other_on=True),
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

    print("=== Speedrun DISCONFIRMER ablation (SIMULATED learners; spec section 8) ===")
    print("feature under test: in-review disconfirmer (SPOV 5)")
    print(f"hypothesis (pre-registered): {HYPOTHESIS}")
    print(f"primary metric: {PRIMARY_METRIC}")
    print(f"students={N_STUDENTS}  transfer items={N_TRANSFER_ITEMS}  "
          f"recall items={N_RECALL_ITEMS}  (equal study time across arms)\n")

    ci_rng = random.Random(SEED + 1)
    transfer = {name: tr for name, (tr, _rc) in arms.items()}
    recall = {name: rc for name, (_tr, rc) in arms.items()}

    rows = []
    for name in ("plain Anki", "feature-off", "full app"):
        tr = transfer[name]
        m = _mean(tr)
        lo, hi = _bootstrap_ci(ci_rng, tr)
        rows.append((name, m, lo, hi))
        print(f"  {name:12s} transfer acc = {m:.1%}  (95% CI {lo:.1%}-{hi:.1%})")

    d_full_off = _cohens_d(transfer["full app"], transfer["feature-off"])
    d_full_plain = _cohens_d(transfer["full app"], transfer["plain Anki"])
    d_off_plain = _cohens_d(transfer["feature-off"], transfer["plain Anki"])
    # transfer-specific null: full vs feature-off on VERBATIM RECALL items (expect ~0)
    d_recall = _cohens_d(recall["full app"], recall["feature-off"])

    print(f"\n  full vs feature-off (transfer)   d = {d_full_off:+.2f}   <- isolates the disconfirmer")
    print(f"  full vs plain Anki  (transfer)   d = {d_full_plain:+.2f}   <- whole-app effect")
    print(f"  feature-off vs plain (transfer)  d = {d_off_plain:+.2f}   <- other features")
    print(f"  recall null: full vs feature-off (VERBATIM items) d = {d_recall:+.2f}  (expect ~0)")

    # Secondary: the AI-hint crutch signature (SPOV 5 kill-switch) - an honest downside.
    base_z = [t + W_REVIEW + W_OTHER_FEATURES + W_DISC_TRANSFER for t in students]
    assisted_delta = _mean([_sigmoid(z + W_ASSIST_INSESSION) - _sigmoid(z) for z in base_z])
    unaided_delta = _mean([_sigmoid(z + W_ASSIST_UNAIDED) - _sigmoid(z) for z in base_z])
    kill = unaided_delta <= -CRUTCH_KILL_THRESHOLD
    print(f"\n  AI-hint crutch (SPOV 5, secondary): assisted {assisted_delta:+.1%} in-session, "
          f"unaided {unaided_delta:+.1%} later -> kill-switch {'FIRES' if kill else 'holds'} "
          f"(disable at <= -{CRUTCH_KILL_THRESHOLD:.0%} unaided)")

    svg = _artifacts.bar_svg(
        [(n, m) for (n, m, _lo, _hi) in rows],
        title="Disconfirmer ablation: delayed TRANSFER accuracy (equal time)",
        subtitle="SIMULATED learners (labelled); bars = mean, whiskers = 95% CI",
        ymax=1.0,
        ranges=[(lo, hi) for (_n, _m, lo, hi) in rows],
    )
    _artifacts.write_svg("ablation-disconfirmer", svg)

    full_m = _mean(transfer["full app"])
    off_m = _mean(transfer["feature-off"])
    plain_m = _mean(transfer["plain Anki"])
    nulls = [
        f"Transfer-specific null (expected): the disconfirmer gave ~0 lift on VERBATIM "
        f"recall of the same facts (full vs feature-off d={d_recall:+.2f}) - it trains "
        f"transfer/boundary understanding, not rote recall, so it is not a general booster.",
        f"AI-hint crutch signature (SPOV 5): an AI hint inflated the assisted in-session "
        f"score ({assisted_delta:+.1%}) but LOWERED later unaided transfer "
        f"({unaided_delta:+.1%}) -> the 'disable any AI level whose users do >= 5 pts worse "
        f"unaided' kill-switch {'fires' if kill else 'holds'}. This is why AI stays off the "
        f"authoring/grading path and is governed by unaided performance.",
        "ALL numbers here are SIMULATED with pre-registered, literature-anchored planted "
        "effects (labelled). They demonstrate the harness and a fair equal-time comparison; "
        "they are NOT evidence the disconfirmer helps real students. The disconfirmer FORMAT "
        "is explicitly unvalidated (brainlift SPOV 5); settling it needs a real three-arm, "
        "equal-time trial (study-first vs disconfirmer) on unseen transfer items, with an "
        "unassisted phase to catch the crutch signature.",
    ]

    _artifacts.write_artifact(
        "ablation-disconfirmer",
        {
            "title": "Study-feature ablation: in-review disconfirmer (3 builds, equal time)",
            "spec": "spec section 8 (SIMULATED learners)",
            "command": "just eval  (run_disconfirmer_ablation.py)",
            "model": _artifacts.OFFLINE_MODEL,
            "seed": SEED,
            "summary": [
                "Feature under test: **in-review disconfirmer** (SPOV 5) - name the one fact "
                "that would flip the answer, then get it as mandatory feedback.",
                f"Pre-registered hypothesis: {HYPOTHESIS}",
                f"Primary metric: **{PRIMARY_METRIC}**. Failure condition: {FAILURE_CONDITION}",
                f"On transfer items: full app **{full_m:.1%}** vs feature-off **{off_m:.1%}** "
                f"vs plain Anki **{plain_m:.1%}** (full vs feature-off d={d_full_off:+.2f}).",
                "Three arms at EQUAL study time; bootstrap 95% CIs shown; SIMULATED learners "
                "(labelled) - a harness demonstration, not a real-student result.",
            ],
            "table": {
                "headers": ["Arm", "Transfer acc", "95% CI"],
                "rows": [[n, f"{m:.1%}", f"{lo:.1%}-{hi:.1%}"] for (n, m, lo, hi) in rows],
            },
            "metrics": {
                "feature": "in-review-disconfirmer",
                "hypothesis": HYPOTHESIS,
                "primary_metric": PRIMARY_METRIC,
                "failure_condition": FAILURE_CONDITION,
                "n_students": N_STUDENTS,
                "arms_transfer_mean": {n: m for (n, m, _l, _h) in rows},
                "arms_transfer_ci": {n: [lo, hi] for (n, _m, lo, hi) in rows},
                "d_full_vs_featureoff": d_full_off,
                "d_full_vs_plain": d_full_plain,
                "d_featureoff_vs_plain": d_off_plain,
                "recall_null_d": d_recall,
                "crutch_assisted_delta": assisted_delta,
                "crutch_unaided_delta": unaided_delta,
                "crutch_kill_switch_fires": kill,
                "planted_effects": {
                    "w_review": W_REVIEW, "w_other": W_OTHER_FEATURES,
                    "w_disc_transfer": W_DISC_TRANSFER, "w_disc_recall": W_DISC_RECALL,
                    "w_assist_insession": W_ASSIST_INSESSION,
                    "w_assist_unaided": W_ASSIST_UNAIDED,
                },
            },
            "chart": "ablation-disconfirmer.svg",
            "verdict": (f"full {full_m:.1%} vs feature-off {off_m:.1%} on transfer items "
                        f"(d={d_full_off:+.2f}); SIMULATED"),
            "nulls": nulls,
        },
    )
    print("\nwrote artifact: docs/eval-artifacts/ablation-disconfirmer.json + .svg")


if __name__ == "__main__":
    main()
