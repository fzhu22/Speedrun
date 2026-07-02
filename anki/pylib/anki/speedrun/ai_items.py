"""AI exam-style item generation behind the spec 7f eval gate.

Discipline (SPOV 5 guardrail + spec AI rules):
- AI may *propose* MC items strictly from a **cited source**; it never grades a student.
- An item never reaches the deck unless it passes a **structural check** and a **leakage
  scan** against the protected (held-out / gold) set.
- The batch must clear a **pre-set cutoff** of structurally-valid items.
- **AI-off (no key) yields no items** (no fabrication); the app still runs.
- Every accepted item carries its **source** (provenance).

Pure/deterministic except for `generate_items` (the one network call); everything else is
unit-testable offline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from anki.speedrun.ai import LLMClient
from anki.speedrun.performance import leakage_check

#: Minimum fraction of a generated batch that must be structurally valid to accept it.
CUTOFF = 0.8
#: Shingle-containment at/above which a generated stem counts as leaked from a protected item.
LEAK_THRESHOLD = 0.8

_OPTS = ["A", "B", "C", "D"]


@dataclass
class GeneratedItem:
    stem: str
    options: Dict[str, str]  # keys "A".."D"
    correct: str  # "A".."D"
    rationale: str
    source: str


def structural_problems(item: GeneratedItem) -> List[str]:
    """Reasons an item is unusable (empty -> ok)."""
    problems: List[str] = []
    if not item.stem.strip():
        problems.append("empty stem")
    opts = item.options or {}
    if sorted(opts.keys()) != _OPTS:
        problems.append("options must be exactly A-D")
    else:
        vals = [(opts[k] or "").strip() for k in _OPTS]
        if any(not v for v in vals):
            problems.append("a blank option")
        if len({v.lower() for v in vals}) < len(vals):
            problems.append("duplicate options")
    if item.correct not in _OPTS:
        problems.append("correct must be one of A-D")
    if not item.rationale.strip():
        problems.append("empty rationale")
    if not item.source.strip():
        problems.append("missing source (provenance)")
    return problems


def _json_slice(text: str) -> str:
    a, b = text.find("["), text.rfind("]")
    return text[a : b + 1] if a != -1 and b != -1 and b > a else text


def generate_items(
    client: Optional[LLMClient],
    source_text: str,
    *,
    n: int = 5,
    source_name: str = "source",
) -> List[GeneratedItem]:
    """Ask the model for ``n`` MC items grounded in ``source_text``. AI-off -> []."""
    if client is None:
        return []  # no key -> no fabrication (spec: app still runs AI-off)
    try:
        system = (
            "You write MCAT-style multiple-choice items STRICTLY from the provided source. "
            "Return ONLY a JSON array of objects "
            '{"stem":str,"options":{"A":str,"B":str,"C":str,"D":str},"correct":"A|B|C|D",'
            '"rationale":str}. Every fact must be supported by the source; no preamble.'
        )
        out = client.complete(system, f"Source:\n{source_text}\n\nWrite {n} items as JSON.")
        data = json.loads(_json_slice(out))
        items: List[GeneratedItem] = []
        for d in data:
            opts = d.get("options", {}) or {}
            items.append(
                GeneratedItem(
                    stem=str(d.get("stem", "")),
                    options={k: str(opts.get(k, "")) for k in _OPTS},
                    correct=str(d.get("correct", "")).strip()[:1].upper(),
                    rationale=str(d.get("rationale", "")),
                    source=source_name,
                )
            )
        return items
    except Exception as exc:  # network/parse failure -> no items, app keeps running
        print("speedrun ai: item generation failed:", exc)
        return []


def evaluate(items: Sequence[GeneratedItem], *, cutoff: float = CUTOFF) -> Dict:
    """Batch structural pass rate vs the pre-set cutoff (run before students see items)."""
    n = len(items)
    valid = sum(1 for it in items if not structural_problems(it))
    rate = valid / n if n else 0.0
    return {
        "n": n,
        "valid": valid,
        "invalid": n - valid,
        "pass_rate": rate,
        "cutoff": cutoff,
        "passes_cutoff": n > 0 and rate >= cutoff,
    }


def accept(
    items: Sequence[GeneratedItem],
    protected_texts: Sequence[str],
    *,
    leak_threshold: float = LEAK_THRESHOLD,
) -> Tuple[List[GeneratedItem], List[Dict]]:
    """Split into (accepted, rejected). Rejects structurally-bad items and any whose stem
    is a near-duplicate of a protected (held-out/gold) item (leakage, spec 7e/7f)."""
    leak = leakage_check(list(protected_texts), [it.stem for it in items], threshold=leak_threshold)
    leaked = {int(m["index"]) for m in leak.matches}
    accepted: List[GeneratedItem] = []
    rejected: List[Dict] = []
    for i, it in enumerate(items):
        problems = structural_problems(it)
        if i in leaked:
            problems.append("near-duplicate of a protected item (leakage)")
        if problems:
            rejected.append({"stem": it.stem, "problems": problems})
        else:
            accepted.append(it)
    return accepted, rejected
