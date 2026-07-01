"""The leakage check (PRD Section 8.3 / spec 7e).

:func:`leakage_check` scans the grounding corpus for near-duplicates of held-out test
items; any hit zeroes the score per the spec, so this must come back clean. This is the
in-scope AI-discipline guard (the AI-proposed-edge validation lives in Rust now).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Tuple

from .textutil import Document, shingles


@dataclass
class LeakageReport:
    """Near-duplicate hits between the corpus and held-out test items."""

    leaks: List[Tuple[str, str, float]] = field(default_factory=list)
    threshold: float = 0.8

    @property
    def clean(self) -> bool:
        return not self.leaks


def leakage_check(
    corpus: Sequence[Document],
    test_items: Iterable[Tuple[str, str]],
    *,
    threshold: float = 0.8,
    k: int = 3,
) -> LeakageReport:
    """Flag any corpus doc that contains (a near-copy of) a held-out test item.

    Similarity is k-gram shingle *containment* (fraction of the test item's shingles
    present in the doc), so a short test item copied into a large document is still
    caught. ``(test_id, doc_id, score)`` is recorded for every pair at or above
    ``threshold``.
    """
    report = LeakageReport(threshold=threshold)
    doc_shingles = [(d.id, shingles(d.text, k)) for d in corpus]
    for test_id, text in test_items:
        t_sh = shingles(text, k)
        if not t_sh:
            continue
        for doc_id, d_sh in doc_shingles:
            score = len(t_sh & d_sh) / len(t_sh)
            if score >= threshold:
                report.leaks.append((test_id, doc_id, score))
    return report
