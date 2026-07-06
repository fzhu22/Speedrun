# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A compact FSRS forward replay, used ONLY to draw the memory reliability diagram.

The engine's ``EvaluateParams`` returns just two scalars (``log_loss`` + ``rmse_bins``),
not the per-bin predicted-vs-observed data a reliability diagram needs. To visualise
calibration we replay each held-out card's review history through the FSRS long-term
recurrence using the ENGINE-FITTED parameters, producing a predicted retrievability before
each review that we compare to the actual pass/fail.

This is the standard FSRS-5/6 long-term update (initial stability/difficulty, difficulty
damping + mean reversion, stability-on-recall / stability-on-forget, power forgetting
curve with a learnable decay ``w[20]``). The bench review log is spaced at day-level
intervals, so the same-day short-term steps (``w[17..19]``) are not exercised and are
omitted. The engine's own ``rmse_bins`` remains the AUTHORITATIVE calibration number; this
replay's rmse is reported alongside as a cross-check, so any divergence is visible.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple


def _clamp_d(d: float) -> float:
    return min(10.0, max(1.0, d))


def _init_difficulty(w: Sequence[float], g: int) -> float:
    return _clamp_d(w[4] - math.exp(w[5] * (g - 1)) + 1.0)


def decay_and_factor(w: Sequence[float]) -> Tuple[float, float]:
    decay = -w[20] if len(w) > 20 and w[20] else -0.5
    factor = 0.9 ** (1.0 / decay) - 1.0
    return decay, factor


def retrievability(w: Sequence[float], t_days: float, stability: float) -> float:
    if stability <= 0:
        return 0.0
    decay, factor = decay_and_factor(w)
    return (1.0 + factor * max(0.0, t_days) / stability) ** decay


def _next_difficulty(w: Sequence[float], d: float, g: int) -> float:
    delta = -w[6] * (g - 3)
    dp = d + delta * (10.0 - d) / 9.0
    d0_easy = _init_difficulty(w, 4)
    return _clamp_d(w[7] * d0_easy + (1.0 - w[7]) * dp)


def _stability_on_recall(w: Sequence[float], d: float, s: float, r: float, g: int) -> float:
    hard = w[15] if g == 2 else 1.0
    easy = w[16] if g == 4 else 1.0
    inc = (
        math.exp(w[8])
        * (11.0 - d)
        * (s ** (-w[9]))
        * (math.exp((1.0 - r) * w[10]) - 1.0)
        * hard
        * easy
    )
    return s * (1.0 + inc)


def _stability_on_forget(w: Sequence[float], d: float, s: float, r: float) -> float:
    sf = w[11] * (d ** (-w[12])) * (((s + 1.0) ** w[13]) - 1.0) * math.exp((1.0 - r) * w[14])
    return min(sf, s)


def replay_card(
    w: Sequence[float], reviews: Sequence[Tuple[float, int]]
) -> List[Tuple[float, int]]:
    """Replay one card. ``reviews`` = ordered ``(elapsed_days_since_last, grade)`` where
    grade is the revlog ease (1=Again .. 4=Easy). Returns ``(predicted_R, observed)`` for
    every review that had a prior state (the first exposure is skipped: no prediction)."""
    out: List[Tuple[float, int]] = []
    if len(w) < 17:
        return out  # not FSRS-shaped params
    s: float = 0.0
    d: float = 0.0
    started = False
    for elapsed, g in reviews:
        g = max(1, min(4, int(g)))
        if not started:
            s = max(0.1, float(w[g - 1]))
            d = _init_difficulty(w, g)
            started = True
            continue
        r = retrievability(w, elapsed, s)
        r = min(1.0, max(0.0, r))
        out.append((r, 1 if g >= 2 else 0))
        if g >= 2:
            s = _stability_on_recall(w, d, s, r, g)
        else:
            s = _stability_on_forget(w, d, s, r)
        s = max(0.01, s)
        d = _next_difficulty(w, d, g)
    return out


def reliability_bins(
    preds: Sequence[Tuple[float, int]], *, n_bins: int = 10
) -> List[dict]:
    """Bin ``(predicted, observed)`` pairs into equal-width probability bins and return the
    per-bin mean predicted, observed rate, and count (bins with no data are dropped)."""
    buckets: List[List[Tuple[float, int]]] = [[] for _ in range(n_bins)]
    for p, o in preds:
        idx = min(n_bins - 1, max(0, int(p * n_bins)))
        buckets[idx].append((p, o))
    bins: List[dict] = []
    for b in buckets:
        if not b:
            continue
        pm = sum(p for p, _ in b) / len(b)
        om = sum(o for _, o in b) / len(b)
        bins.append({"predicted": pm, "observed": om, "n": len(b)})
    return bins


def brier(preds: Sequence[Tuple[float, int]]) -> float:
    if not preds:
        return 0.0
    return sum((p - o) ** 2 for p, o in preds) / len(preds)


def rmse_bins(bins: Sequence[dict]) -> float:
    """RMSE between predicted and observed across bins, count-weighted (the reliability
    diagram's numeric summary; comparable to the engine's ``rmse_bins``)."""
    total = sum(b["n"] for b in bins)
    if not total:
        return 0.0
    se = sum(b["n"] * (b["predicted"] - b["observed"]) ** 2 for b in bins)
    return (se / total) ** 0.5
