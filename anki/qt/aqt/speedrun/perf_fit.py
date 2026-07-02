# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Performance-lane prepare step (SPOV 1 desktop "prepare" tier).

Extracts graded responses to the held-out `Speedrun Performance Item` cards from the
review log, fits the calibrated model, runs the incremental-validity gate
(`anki.speedrun.performance`), and writes the result to the collection config. The shared
Rust dashboard reads the single `speedrun_performance_enabled` flag and only then shows a
per-section Performance number - so Performance is not displayed until it earns its place
by beating recall out-of-sample.
"""

from __future__ import annotations

from typing import Dict, List

import aqt
import aqt.main
from anki.speedrun import performance as perf
from aqt.utils import showInfo, tooltip

PERF_NOTETYPE = "Speedrun Performance Item"
TAG_PREFIX = "MCAT"
PERF_CONFIG_KEY = "speedrun_performance"
PERF_ENABLED_KEY = "speedrun_performance_enabled"


def _known_codes() -> set:
    from anki.speedrun.aamc_outline import outline_data

    codes = set()
    for section in outline_data()["sections"]:
        for fc in section.get("foundational_concepts", []):
            for cc in fc.get("content_categories", []):
                codes.add(cc["id"].split(":")[-1])  # "cc:1A" -> "1A"
    return codes


def _cc_from_tag(tag: str, known: set) -> str:
    for part in reversed(tag.split("::")):
        if part.strip() in known:
            return part.strip()
    return ""


def _recall_by_cc(col, known: set) -> Dict[str, float]:
    res = col.topic_mastery(tag_prefix=TAG_PREFIX, min_cards_for_average=1)
    weighted: Dict[str, float] = {}
    reviewed: Dict[str, int] = {}
    for topic in res.topics:
        cc = _cc_from_tag(topic.tag, known)
        if not cc or not topic.HasField("average_recall"):
            continue
        weighted[cc] = weighted.get(cc, 0.0) + topic.average_recall * topic.reviewed_cards
        reviewed[cc] = reviewed.get(cc, 0) + topic.reviewed_cards
    return {cc: weighted[cc] / reviewed[cc] for cc in weighted if reviewed.get(cc)}


def extract_responses(col) -> List[perf.Response]:
    """Build one Response per graded answer on a held-out performance item."""
    known = _known_codes()
    recall_by_cc = _recall_by_cc(col, known)
    responses: List[perf.Response] = []
    for cid in col.find_cards(f'note:"{PERF_NOTETYPE}"'):
        card = col.get_card(cid)
        note = card.note()
        cc = ""
        concept = ""
        for tag in note.tags:
            if not cc:
                cc = _cc_from_tag(tag, known)
            if tag.startswith("concept::"):
                concept = tag.split("::", 1)[1]
        recall = recall_by_cc.get(cc, 0.5)
        for ease, time_ms in col.db.all(
            "select ease, time from revlog where cid = ? and ease >= 1", cid
        ):
            responses.append(
                perf.Response(
                    correct=ease >= 2,
                    recall=recall,
                    difficulty=0.5,  # placeholder until per-item difficulty is estimated
                    latency_ms=int(time_ms or 0),
                    coverage=0.0,
                    section=cc,
                    concept=concept,
                )
            )
    return responses


def fit_performance_model(mw: aqt.main.AnkiQt) -> None:
    """Tools action: fit the model + gate from the review log and persist the flag."""
    col = mw.col
    if col is None:
        return
    responses = extract_responses(col)
    result = perf.fit_and_serialize(responses)
    col.set_config(PERF_CONFIG_KEY, result)
    col.set_config(PERF_ENABLED_KEY, bool(result["gate"]["passes"]))
    mw.reset()

    g = result["gate"]
    lines = [
        f"Graded held-out responses: {g['n']} (need >= {g['min_responses']})",
        "",
        f"AUC recall-only : {g['auc_recall']:.3f}",
        f"AUC full model  : {g['auc_full']:.3f}",
        f"Delta           : {g['delta']:+.3f} (need >= {g['min_delta']:.3f})",
        f"Calibration Brier: {result['brier'] if result['brier'] is not None else '-'}",
        "",
        (
            "GATE PASSED - Performance now shows on the dashboard."
            if g["passes"]
            else "GATE NOT PASSED - Performance keeps abstaining (it must beat recall)."
        ),
    ]
    showInfo("\n".join(lines), parent=mw, title="Speedrun: Fit Performance Model")
    tooltip("Performance model updated.", parent=mw)
