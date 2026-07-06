"""Held-out evaluation for the AI card-type classifier (the spec's AI gate).

Before the classifier is trusted it must (a) clear a pre-registered accuracy cutoff and
(b) beat the deterministic heuristic baseline, on a labeled gold set kept disjoint from
the few-shot prompt (leakage check). Mirrors the spec's "evaluate before students see
it + beat a simpler baseline + leakage check" rules.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from anki.speedrun.cardtype import CardType
from anki.speedrun.textutil import Document, bag_of_words, cosine
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
    # --- expanded held-out set (still disjoint from FEWSHOT_EXAMPLES) ---
    # more declarative facts
    ("What is the pH of pure water at 25C?", "7", CardType.DECLARATIVE),
    ("What organelle performs photosynthesis?", "Chloroplast", CardType.DECLARATIVE),
    ("What is the charge of an electron?", "Negative", CardType.DECLARATIVE),
    ("What molecule carries amino acids to the ribosome?", "tRNA", CardType.DECLARATIVE),
    ("What is the first product of the citric acid cycle?", "Citrate", CardType.DECLARATIVE),
    ("What vitamin is ascorbic acid?", "Vitamin C", CardType.DECLARATIVE),
    ("What is the SI unit of electric current?", "Ampere", CardType.DECLARATIVE),
    ("What ion is most concentrated inside a resting neuron?", "Potassium", CardType.DECLARATIVE),
    # more application / reasoning
    ("Predict the effect of a competitive inhibitor on apparent Km.", "It rises", CardType.APPLICATION),
    ("If a gas is compressed at constant temperature, what happens to its pressure?", "It rises", CardType.APPLICATION),
    ("Why does ice float on water?", "Ice is less dense than liquid water", CardType.APPLICATION),
    ("A weak acid is titrated past its pKa; how does buffering change?", "It weakens", CardType.APPLICATION),
    ("How does adding a catalyst change the equilibrium constant?", "It does not change it", CardType.APPLICATION),
    ("If sodium channels are blocked, what happens to the action potential?", "It cannot fire", CardType.APPLICATION),
    ("Predict the sign of delta G for a spontaneous reaction.", "Negative", CardType.APPLICATION),
    ("Doubling the distance between two charges does what to the force?", "Quarters it", CardType.APPLICATION),
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


def make_vector_baseline(prototypes: List[GoldItem]) -> ClassifyFn:
    """A keyword/vector baseline: label a card by its nearest labeled prototype under
    bag-of-words cosine similarity - the no-embedding-model stand-in for 'vector search'.
    The AI classifier must beat this (and the heuristic) to clear the gate."""
    protos = [(bag_of_words(f"{q} {a}"), t) for q, a, t in prototypes]

    def classify(question: str, answer: str = "") -> CardType:
        vec = bag_of_words(f"{question} {answer}")
        best_type, best_sim = CardType.DECLARATIVE, -1.0
        for pvec, ptype in protos:
            sim = cosine(vec, pvec)
            if sim > best_sim:
                best_sim, best_type = sim, ptype
        return best_type

    return classify


#: A labeled prototype set for the offline reference classifier. Disjoint from both the
#: few-shot prompt examples and CARD_TYPE_GOLD (so the offline stand-in is not tuned to the
#: gold it is scored on). These are original, generic Q/A/label triples.
REFERENCE_PROTOTYPES: List[GoldItem] = [
    ("What is the powerhouse of the cell?", "Mitochondrion", CardType.DECLARATIVE),
    ("What gas do plants take in for photosynthesis?", "Carbon dioxide", CardType.DECLARATIVE),
    ("What is the monomer of a protein?", "Amino acid", CardType.DECLARATIVE),
    ("What is the charge on a proton?", "Positive", CardType.DECLARATIVE),
    ("What is the base pair of adenine in DNA?", "Thymine", CardType.DECLARATIVE),
    ("What organ produces bile?", "Liver", CardType.DECLARATIVE),
    ("What is the unit of frequency?", "Hertz", CardType.DECLARATIVE),
    ("What is the most electronegative element?", "Fluorine", CardType.DECLARATIVE),
    ("Why does sweating cool the body?", "Evaporation removes heat", CardType.APPLICATION),
    ("Predict the effect of raising temperature on enzyme rate past its optimum.", "Rate falls (denatures)", CardType.APPLICATION),
    ("How would removing product shift a reversible reaction?", "Toward the products", CardType.APPLICATION),
    ("If resistance rises at constant voltage, what happens to current?", "It falls", CardType.APPLICATION),
    ("Explain why oxygen is the final electron acceptor.", "It is highly electronegative", CardType.APPLICATION),
    ("Compare diffusion rates of a small vs large molecule.", "Small diffuses faster", CardType.APPLICATION),
    ("What happens to blood pH if breathing slows?", "It falls (acidosis)", CardType.APPLICATION),
    ("Predict solubility of a nonpolar gas as temperature rises.", "It decreases", CardType.APPLICATION),
]


def reference_classifier() -> ClassifyFn:
    """A deterministic OFFLINE stand-in for the AI classifier, so the harness (comparison,
    cutoff, leakage) runs with no key and the report is reproducible. It combines the
    keyword heuristic with a nearest-labeled-prototype vote over REFERENCE_PROTOTYPES (a
    richer signal than the 2-shot 'vector' baseline). It is NOT a real LLM and NOT tuned to
    the gold set; whatever accuracy it earns is reported honestly (offline it may or may not
    beat the keyword baseline - that is itself an honest result). The decisive AI-beats-a-
    simpler-method evidence comes from the real model when an api-key is configured."""
    from anki.speedrun.cardtype import heuristic_classify

    nn = make_vector_baseline(REFERENCE_PROTOTYPES)
    proto_vecs = [(bag_of_words(f"{q} {a}"), t) for q, a, t in REFERENCE_PROTOTYPES]

    def classify(question: str, answer: str = "") -> CardType:
        vec = bag_of_words(f"{question} {answer}")
        best_sim = max((cosine(vec, pv) for pv, _t in proto_vecs), default=0.0)
        heur = heuristic_classify(question, answer)
        # Trust the prototype vote only when it is a confident match; otherwise the cue
        # heuristic. When either confidently signals application, prefer application (the
        # costlier miss is suppressing a useful disconfirmer).
        if best_sim >= 0.5:
            nn_label = nn(question, answer)
            if nn_label == CardType.APPLICATION or heur == CardType.APPLICATION:
                return CardType.APPLICATION
            return CardType.DECLARATIVE
        return heur

    return classify


def compare(
    ai_fn: ClassifyFn,
    heuristic_fn: ClassifyFn,
    gold: Optional[List[GoldItem]] = None,
    vector_fn: Optional[ClassifyFn] = None,
) -> Dict[str, float]:
    """Accuracy of the AI classifier vs simpler baselines (beat-a-baseline). Always
    includes the keyword heuristic; includes the vector baseline when provided."""
    result = {
        "ai": evaluate(ai_fn, gold)["accuracy"],
        "heuristic": evaluate(heuristic_fn, gold)["accuracy"],
    }
    if vector_fn is not None:
        result["vector"] = evaluate(vector_fn, gold)["accuracy"]
    return result


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
