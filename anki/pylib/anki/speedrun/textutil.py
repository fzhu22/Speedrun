"""Tiny, dependency-free text helpers shared by validation and the AI eval lane.

Deliberately simple and deterministic so the whole package runs and tests without an
embedding model or any network access (the AI-off baseline path).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


@dataclass
class Document:
    """A grounding-corpus chunk (a cited source span).

    Used by the leakage check and the AI eval few-shot container; kept here (a
    leaf util with no package deps) so both can share it without a cycle.
    """

    id: str
    text: str
    source: str

_STOPWORDS = frozenset(
    """
    the a an and or of to in on for with within from into by as is are be that this
    these those their its his her how ways way and/or main groups single
    """.split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokens(text: str, *, keep_stopwords: bool = False) -> List[str]:
    """Lowercase alphanumeric tokens, dropping short/stopword tokens by default."""
    raw = _TOKEN_RE.findall(text.lower())
    if keep_stopwords:
        return raw
    return [t for t in raw if len(t) > 2 and t not in _STOPWORDS]


def token_set(text: str) -> Set[str]:
    return set(tokens(text))


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def containment(needle: Set[str], haystack: Set[str]) -> float:
    """Fraction of ``needle`` tokens present in ``haystack`` (asymmetric)."""
    if not needle:
        return 0.0
    return len(needle & haystack) / len(needle)


def shingles(text: str, k: int = 3) -> Set[Tuple[str, ...]]:
    """Set of k-gram token shingles (for near-duplicate detection)."""
    toks = tokens(text, keep_stopwords=True)
    if len(toks) < k:
        return {tuple(toks)} if toks else set()
    return {tuple(toks[i : i + k]) for i in range(len(toks) - k + 1)}


def bag_of_words(text: str) -> Dict[str, float]:
    """A deterministic term-frequency vector (the no-model 'embedding')."""
    vec: Dict[str, float] = {}
    for t in tokens(text):
        vec[t] = vec.get(t, 0.0) + 1.0
    return vec


def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    shared = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in shared)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    return dot / (na * nb) if na and nb else 0.0
