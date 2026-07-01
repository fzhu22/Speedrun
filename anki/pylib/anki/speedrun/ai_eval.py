"""Held-out evaluation for the AI card-type classifier (the spec's AI gate).

Before the classifier is trusted it must (a) clear a pre-registered accuracy cutoff and
(b) beat the deterministic heuristic baseline, on a labeled gold set kept disjoint from
the few-shot prompt (leakage check). Mirrors the spec's "evaluate before students see
it + beat a simpler baseline + leakage check" rules.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from anki.speedrun.cardtype import CardType
from anki.speedrun.textutil import Document
from anki.speedrun.validation import LeakageReport, leakage_check

#: Pre-registered before looking at results.
CUTOFF = 0.80

ClassifyFn = Callable[[str, str], CardType]
GoldItem = Tuple[str, str, CardType]

#: Original labeled examples (question, answer, true type). Disjoint from the prompt
#: few-shot examples in ai.py.
CARD_TYPE_GOLD: List[GoldItem] = [
    # declarative facts
    ("How many amino acids are standard?", "20", CardType.DECLARATIVE),
    ("What is the start codon?", "AUG", CardType.DECLARATIVE),
    ("Define osmosis.", "Water moving down its concentration gradient", CardType.DECLARATIVE),
    ("Which gland secretes insulin?", "Pancreas", CardType.DECLARATIVE),
    ("Where does glycolysis occur?", "Cytoplasm", CardType.DECLARATIVE),
    ("Name the powerhouse of the cell.", "Mitochondrion", CardType.DECLARATIVE),
    ("What bond joins amino acids?", "Peptide bond", CardType.DECLARATIVE),
    ("The SI unit of force?", "Newton", CardType.DECLARATIVE),
    ("Number of chromosomes in a human gamete?", "23", CardType.DECLARATIVE),
    ("Neurotransmitter at the neuromuscular junction?", "Acetylcholine", CardType.DECLARATIVE),
    # application / reasoning
    ("Why is glycolysis oxygen-independent?", "It runs in the cytoplasm without the ETC", CardType.APPLICATION),
    ("If pH rises above a protein's pI, what is its net charge?", "Negative", CardType.APPLICATION),
    ("Predict the ATP yield if a cell loses oxygen.", "~2 ATP (glycolysis only)", CardType.APPLICATION),
    ("Which would lower total resistance: series or parallel?", "Parallel", CardType.APPLICATION),
    ("Compare SN1 and SN2 dependence on the nucleophile.", "SN2 depends on it; SN1 does not", CardType.APPLICATION),
    ("Explain how a catalyst speeds a reaction.", "It lowers the activation energy", CardType.APPLICATION),
    ("How does increasing temperature affect reaction rate?", "It increases it", CardType.APPLICATION),
    ("A patient's blood pH drops; what compensates fastest?", "Respiration (blowing off CO2)", CardType.APPLICATION),
    # application cases the heuristic tends to miss (no obvious cue + short answer)
    ("A solution at pH 3 holds a buffer with pKa 7. Is it effective there?", "No", CardType.APPLICATION),
    ("Two equal resistors end to end - total resistance vs one?", "Double", CardType.APPLICATION),
    ("Substrate far above Km does what to enzyme velocity?", "Approaches Vmax", CardType.APPLICATION),
]


def evaluate(classify_fn: ClassifyFn, gold: Optional[List[GoldItem]] = None) -> Dict[str, float]:
    items = gold if gold is not None else CARD_TYPE_GOLD
    n = len(items)
    correct = sum(1 for q, a, t in items if classify_fn(q, a) == t)
    return {
        "n": float(n),
        "accuracy": correct / n if n else 0.0,
        "wrong_rate": (n - correct) / n if n else 0.0,
    }


def compare(
    ai_fn: ClassifyFn,
    heuristic_fn: ClassifyFn,
    gold: Optional[List[GoldItem]] = None,
) -> Dict[str, float]:
    """Accuracy of the AI classifier vs the heuristic baseline (beat-a-baseline)."""
    return {
        "ai": evaluate(ai_fn, gold)["accuracy"],
        "heuristic": evaluate(heuristic_fn, gold)["accuracy"],
    }


def passes_cutoff(accuracy: float, cutoff: float = CUTOFF) -> bool:
    return accuracy >= cutoff


def fewshot_leakage(
    fewshot: List[GoldItem], gold: Optional[List[GoldItem]] = None
) -> LeakageReport:
    """Confirm the prompt's few-shot examples are not near-copies of the gold set."""
    items = gold if gold is not None else CARD_TYPE_GOLD
    corpus = [
        Document(id=f"shot{i}", text=f"{q} {a}", source="fewshot")
        for i, (q, a, _t) in enumerate(fewshot)
    ]
    test_items = [(f"gold{i}", q) for i, (q, _a, _t) in enumerate(items)]
    return leakage_check(corpus, test_items, threshold=0.8)
