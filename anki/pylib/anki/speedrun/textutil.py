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


# -- prompt-injection defense (spec 10: a source file with hidden text) ---------------
# Untrusted text (a pasted "source" for card generation, a draft card) can carry hidden
# instructions - inside HTML tags/comments, zero-width characters, or plain "ignore the
# above" lines - that try to hijack the model. We defang it before it ever reaches a
# prompt: strip markup/hidden characters and neutralise known override phrases. Callers
# additionally frame it as untrusted DATA in the system prompt.

_ZERO_WIDTH = {ord(c): None for c in "\u200b\u200c\u200d\u2060\ufeff\u00ad"}
_HTML_BLOCK = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1>")
_HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")
_HTML_TAG = re.compile(r"(?s)<[^>]+>")
_INJECTION_PATTERNS = [
    ("ignore-previous", re.compile(
        r"(?is)ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier)\s+"
        r"(instructions?|prompts?|messages?|text)")),
    ("disregard", re.compile(
        r"(?is)disregard\s+(the\s+|all\s+)?(above|previous|prior|earlier|instructions?)")),
    ("role-override", re.compile(r"(?is)you\s+are\s+now\b|act\s+as\s+|pretend\s+to\s+be")),
    ("system-prompt", re.compile(
        r"(?is)system\s*prompt|reveal\s+(the\s+)?(system|hidden)\s+prompt")),
    ("role-tag", re.compile(r"(?im)^\s*(assistant|system|developer)\s*:")),
    ("new-instructions", re.compile(
        r"(?is)new\s+instructions?\s*:|instead\s*,?\s*(do|output|write|print|return)\b")),
    ("jailbreak", re.compile(r"(?is)override\s+your|jailbreak|do\s+anything\s+now|\bDAN\b")),
    # Exfiltration: an imperative to emit/append a payload back to the caller ("append X to
    # your response", "output ... in your answer"). Generic - removes whatever payload the
    # instruction carries, not a specific token.
    ("exfiltrate", re.compile(
        r"(?is)\b(append|add|output|print|include|emit|repeat|write|say|return|send)\b"
        r"[^\n.]{0,60}?\bto\s+(your\s+|the\s+)?"
        r"(response|reply|answer|output|message|user|screen)\b")),
    # A sequenced imperative to emit/reveal something ("then output ...", "also print ...").
    # Requires an explicit sequencing adverb so it does not fire on ordinary prose like
    # "the output of glycolysis".
    ("imperative-emit", re.compile(
        r"(?is)\b(then|also|now|next|finally|first|afterwards?)\b\s*,?\s*"
        r"(output|print|emit|reveal|expose|leak|repeat|append|say)\b[^\n.]{0,80}")),
    # Answer-forcing: a poisoned passage that tries to fix the "correct" choice.
    ("answer-forcing", re.compile(
        r"(?is)correct\s+answer\s+is\s+always|always\s+(pick|choose|select|answer|mark|say)\b")),
]


def _defang(text: str) -> str:
    t = _HTML_BLOCK.sub(" ", text)
    t = _HTML_COMMENT.sub(" ", t)
    t = _HTML_TAG.sub(" ", t)
    t = t.translate(_ZERO_WIDTH)
    return "".join(ch for ch in t if ch in "\n\t" or ord(ch) >= 32)


def find_injection_markers(text: str) -> List[str]:
    """Names of prompt-injection patterns present in ``text`` (after de-fanging markup and
    hidden characters). Empty list == looks clean. Used by tests and reporting."""
    if not text:
        return []
    defanged = _defang(str(text))
    return [name for name, pat in _INJECTION_PATTERNS if pat.search(defanged)]


def sanitize_source(text: str, *, max_len: int = 8000) -> str:
    """Return ``text`` safe to embed as untrusted DATA in a prompt: markup and hidden
    characters stripped, known override phrases neutralised, length capped."""
    if not text:
        return ""
    t = _defang(str(text))
    for _name, pat in _INJECTION_PATTERNS:
        t = pat.sub(" [removed] ", t)
    t = re.sub(r"[ \t]{3,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    if len(t) > max_len:
        t = t[:max_len]
    return t.strip()
