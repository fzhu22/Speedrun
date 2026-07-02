"""The Performance lane's model + honesty gate (brainlift SPOV 3, spec section 9 Step 2).

Performance is the second of the three scores: the chance a student answers a *new,
exam-style* question right. FSRS (Memory) is not allowed to stand in for it - per SPOV 3,
Performance must add predictive value *beyond recall* or it does not ship. This module is
the deterministic, dependency-free core (no numpy/sklearn, no network) so it runs on the
AI-off path and is unit-testable:

* a calibrated logistic model of P(correct) from recall + item difficulty + timing +
  coverage,
* the **incremental-validity gate**: k-fold, out-of-sample AUC of a recall-only model vs
  the full model; the full model must beat recall by a margin or the gate fails and the
  Performance score keeps abstaining,
* the **paraphrase test** (spec 7d): card recall vs reworded-item accuracy per concept,
* the **leakage check** (spec 7e): near-duplicate overlap between the studied set and the
  held-out items.

The collection glue (extracting responses from the revlog, writing the fitted model to
config) lives in the GUI/testdeck; everything here is pure functions over plain records.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from anki.speedrun.textutil import containment, shingles

#: Minimum graded held-out responses before Performance may be shown (give-up rule).
MIN_RESPONSES = 30
#: The full model must beat a recall-only model by at least this out-of-sample AUC.
MIN_AUC_DELTA = 0.02
#: Near-duplicate shingle-containment at/above this fraction counts as leakage.
LEAKAGE_THRESHOLD = 0.8


@dataclass
class Response:
    """One graded answer on a held-out exam-style item."""

    correct: bool
    recall: float  # per-family FSRS recall at/around answer time (0..1)
    difficulty: float = 0.5  # item difficulty in [0,1] (1 = hardest); 0.5 if unknown
    latency_ms: int = 0
    coverage: float = 0.0  # section coverage in [0,1]
    section: str = ""
    concept: str = ""


# -- feature extraction -------------------------------------------------------


def _latency_norm(ms: int) -> float:
    # squash to [0,1]; ~60s = fully "slow". Timing is a weak, bounded feature.
    return max(0.0, min(1.0, ms / 60000.0))


def full_features(r: Response) -> List[float]:
    return [r.recall, r.difficulty, _latency_norm(r.latency_ms), r.coverage]


def recall_features(r: Response) -> List[float]:
    return [r.recall]


# -- tiny numerics (pure python) ----------------------------------------------


def _sigmoid(z: float) -> float:
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def _standardize(rows: Sequence[Sequence[float]]):
    d = len(rows[0])
    means = [sum(r[k] for r in rows) / len(rows) for k in range(d)]
    stds = []
    for k in range(d):
        var = sum((r[k] - means[k]) ** 2 for r in rows) / len(rows)
        stds.append(math.sqrt(var) or 1.0)
    return means, stds


def fit_logistic(
    X: Sequence[Sequence[float]],
    y: Sequence[int],
    *,
    l2: float = 1.0,
    lr: float = 0.3,
    iters: int = 800,
) -> Dict:
    """Standardized logistic regression by batch gradient descent (deterministic)."""
    means, stds = _standardize(X)
    xs = [[(row[k] - means[k]) / stds[k] for k in range(len(means))] for row in X]
    d = len(means)
    w = [0.0] * d
    b = 0.0
    n = len(xs)
    for _ in range(iters):
        gw = [0.0] * d
        gb = 0.0
        for xi, yi in zip(xs, y):
            p = _sigmoid(b + sum(w[k] * xi[k] for k in range(d)))
            err = p - yi
            for k in range(d):
                gw[k] += err * xi[k]
            gb += err
        for k in range(d):
            w[k] -= lr * (gw[k] / n + l2 * w[k] / n)
        b -= lr * gb / n
    return {"w": w, "b": b, "means": means, "stds": stds}


def predict(model: Dict, x: Sequence[float]) -> float:
    means, stds, w, b = model["means"], model["stds"], model["w"], model["b"]
    xs = [(x[k] - means[k]) / stds[k] for k in range(len(means))]
    return _sigmoid(b + sum(w[k] * xs[k] for k in range(len(w))))


def auc(y: Sequence[int], scores: Sequence[float]) -> float:
    """Mann-Whitney AUC with average ranks for ties. 0.5 if degenerate."""
    n_pos = sum(1 for v in y if v == 1)
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(order)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    sum_pos = sum(ranks[i] for i in range(len(y)) if y[i] == 1)
    return (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def brier(y: Sequence[int], probs: Sequence[float]) -> float:
    if not y:
        return 0.0
    return sum((p - t) ** 2 for p, t in zip(probs, y)) / len(y)


# -- the incremental-validity gate (SPOV 3) -----------------------------------


def incremental_validity(responses: Sequence[Response], *, folds: int = 5, seed: int = 0) -> Dict:
    """Out-of-sample AUC of a full model vs a recall-only model, via k-fold CV.

    The crux of SPOV 3: Performance is only worth showing if the application signals add
    predictive value beyond recall on held-out data.
    """
    n = len(responses)
    if n < 2:
        return {"n": n, "auc_full": 0.5, "auc_recall": 0.5, "delta": 0.0}
    y = [1 if r.correct else 0 for r in responses]
    full = [full_features(r) for r in responses]
    rec = [recall_features(r) for r in responses]

    idx = list(range(n))
    random.Random(seed).shuffle(idx)
    k = max(2, min(folds, n))
    full_scores: List[float] = []
    rec_scores: List[float] = []
    ys: List[int] = []
    for f in range(k):
        test = [idx[i] for i in range(n) if i % k == f]
        train = [i for i in idx if i not in set(test)]
        if not train or not test or len({y[i] for i in train}) < 2:
            continue
        mf = fit_logistic([full[i] for i in train], [y[i] for i in train])
        mr = fit_logistic([rec[i] for i in train], [y[i] for i in train])
        for i in test:
            full_scores.append(predict(mf, full[i]))
            rec_scores.append(predict(mr, rec[i]))
            ys.append(y[i])
    if not ys:
        return {"n": n, "auc_full": 0.5, "auc_recall": 0.5, "delta": 0.0}
    a_full = auc(ys, full_scores)
    a_rec = auc(ys, rec_scores)
    return {"n": n, "auc_full": a_full, "auc_recall": a_rec, "delta": a_full - a_rec}


def gate(
    responses: Sequence[Response],
    *,
    min_responses: int = MIN_RESPONSES,
    min_delta: float = MIN_AUC_DELTA,
) -> Dict:
    """Whether Performance may ship: enough data AND it beats recall out-of-sample."""
    iv = incremental_validity(responses)
    passes = iv["n"] >= min_responses and iv["delta"] >= min_delta
    return {**iv, "passes": passes, "min_responses": min_responses, "min_delta": min_delta}


def fit_and_serialize(responses: Sequence[Response]) -> Dict:
    """Fit the full model + compute the gate + calibration, as a config-storable dict."""
    if not responses:
        return {"model": None, "gate": gate(responses), "brier": None, "n": 0}
    y = [1 if r.correct else 0 for r in responses]
    model = fit_logistic([full_features(r) for r in responses], y)
    probs = [predict(model, full_features(r)) for r in responses]
    return {
        "model": model,
        "gate": gate(responses),
        "brier": brier(y, probs),
        "n": len(responses),
    }


# -- the paraphrase test (spec 7d) --------------------------------------------


@dataclass
class ParaphraseResult:
    per_concept: Dict[str, Dict[str, float]] = field(default_factory=dict)
    mean_recall: float = 0.0
    mean_accuracy: float = 0.0
    mean_gap: float = 0.0


def paraphrase_gap(
    recall_by_concept: Dict[str, float],
    accuracy_by_concept: Dict[str, float],
) -> ParaphraseResult:
    """Compare base-card recall vs reworded-item accuracy per concept (memory->perf gap)."""
    concepts = sorted(set(recall_by_concept) & set(accuracy_by_concept))
    per: Dict[str, Dict[str, float]] = {}
    for c in concepts:
        r = recall_by_concept[c]
        a = accuracy_by_concept[c]
        per[c] = {"recall": r, "accuracy": a, "gap": r - a}
    if not concepts:
        return ParaphraseResult()
    mr = sum(recall_by_concept[c] for c in concepts) / len(concepts)
    ma = sum(accuracy_by_concept[c] for c in concepts) / len(concepts)
    return ParaphraseResult(per_concept=per, mean_recall=mr, mean_accuracy=ma, mean_gap=mr - ma)


# -- the leakage check (spec 7e) ----------------------------------------------


@dataclass
class LeakageResult:
    clean: bool
    max_overlap: float
    matches: List[Dict[str, object]] = field(default_factory=list)


def leakage_check(
    studied_texts: Sequence[str],
    heldout_texts: Sequence[str],
    *,
    threshold: float = LEAKAGE_THRESHOLD,
    k: int = 3,
) -> LeakageResult:
    """Flag held-out items whose shingles are largely contained in any studied text."""
    studied = [shingles(t, k) for t in studied_texts]
    matches: List[Dict[str, object]] = []
    max_overlap = 0.0
    for hi, ht in enumerate(heldout_texts):
        hs = shingles(ht, k)
        best = 0.0
        for si in studied:
            best = max(best, containment(hs, si))
        max_overlap = max(max_overlap, best)
        if best >= threshold:
            matches.append({"index": hi, "overlap": best, "text": ht})
    return LeakageResult(clean=not matches, max_overlap=max_overlap, matches=matches)
