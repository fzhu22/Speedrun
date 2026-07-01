# Copyright: Speedrun (AGPL-3.0-or-later)
"""Seed an isolated dev collection with a default MCAT deck.

    python tools/seed_mcat.py [BASE_DIR]

Creates BASE_DIR/User 1/collection.anki2 (the path Anki's default profile opens)
pre-populated with a small MCAT deck whose notes are tagged by AAMC content category
(MCAT::<section>::<cc>), so the app opens with content ready to review and the cards
line up with the concept knowledge graph. Idempotent: re-running does nothing once the
deck is present. Uses an isolated base so your real Anki collection is never touched.
"""

from __future__ import annotations

import os
import sys

# Make the built anki package importable (same paths as tools/run.py).
sys.path.extend(["pylib", "qt", "out/pylib", "out/qt"])

from anki.collection import Collection  # noqa: E402

DECK_NAME = "MCAT Speedrun"
MODEL_NAME = "Speedrun MCAT Basic"
SEED_TAG = "speedrun_seed"

# (content_category_id, front, back)
CARDS = [
    ("1A", "How do the 20 standard amino acids differ from one another?", "By their side chains (R groups)"),
    ("1A", "Which standard amino acid is achiral?", "Glycine (its R group is a hydrogen)"),
    ("1B", "Transcription produces what molecule from a DNA template?", "messenger RNA (pre-mRNA)"),
    ("1B", "Which codon is the start codon, and what amino acid does it specify?", "AUG -> methionine"),
    ("1C", "During which phase of meiosis does crossing over occur?", "Prophase I"),
    ("1D", "Net ATP produced by glycolysis (substrate-level)?", "2 ATP (per glucose)"),
    ("1D", "What is the terminal electron acceptor of the electron transport chain?", "Oxygen (O2)"),
    ("1D", "Where does the citric acid (Krebs) cycle occur in eukaryotes?", "The mitochondrial matrix"),
    ("2A", "What is the role of tight junctions between cells?", "Form a watertight seal preventing paracellular leakage"),
    ("2B", "Gram-positive bacteria stain what color, and why?", "Purple - thick peptidoglycan cell wall"),
    ("2C", "What is the process by which a cell becomes specialized?", "Differentiation"),
    ("3A", "What neurotransmitter acts at the neuromuscular junction?", "Acetylcholine"),
    ("3A", "Which pancreatic cells secrete insulin?", "Beta cells (islets of Langerhans)"),
    ("3B", "What is the functional unit of the kidney?", "The nephron"),
    ("4A", "Work done by a constant force equals what?", "W = F d cos(theta)"),
    ("4B", "In Poiseuille's law, flow rate scales with radius to what power?", "The fourth power (r^4)"),
    ("4C", "A galvanic (voltaic) cell has what sign of cell potential?", "Positive (the reaction is spontaneous)"),
    ("4D", "Index of refraction is defined as n = c / ?", "v, the speed of light in the medium"),
    ("4E", "Beta-minus decay converts a neutron into what particles?", "A proton + an electron (+ antineutrino)"),
    ("5A", "Why does water have an unusually high boiling point?", "Extensive hydrogen bonding"),
    ("5B", "What is the strongest intermolecular force between neutral molecules?", "Hydrogen bonding"),
    ("5C", "Which technique separates compounds by polarity on a stationary phase?", "Chromatography (TLC / column)"),
    ("5D", "What is the hybridization of a carbonyl carbon?", "sp2"),
    ("5E", "A reaction with a negative delta G is described as what?", "Spontaneous (exergonic)"),
    ("5E", "Catalysts speed up reactions by lowering what?", "The activation energy"),
    ("6A", "Where in the eye does transduction of light occur?", "The retina (rods and cones)"),
    ("6B", "Bottom-up processing begins with what?", "Raw sensory input / stimuli"),
    ("6C", "The fight-or-flight response is mediated by which nervous system?", "The sympathetic nervous system"),
    ("7A", "Who described classical conditioning?", "Ivan Pavlov"),
    ("7B", "How does helping behavior change as bystander group size grows?", "It decreases (the bystander effect)"),
    ("8A", "What term describes our overall evaluation of self-worth?", "Self-esteem"),
    ("8B", "Over-attributing others' behavior to disposition is called what?", "The fundamental attribution error"),
    ("9A", "What is a society's stable pattern of social relationships called?", "Social structure"),
    ("10A", "Unequal distribution of resources across a society is called what?", "Social inequality / stratification"),
]


def _section_for(cc: str) -> str:
    num = int("".join(ch for ch in cc if ch.isdigit()))
    if num <= 3:
        return "Bio_Biochem"
    if num <= 5:
        return "Chem_Phys"
    return "Psych_Soc"


def _get_or_create_model(col: Collection):
    mm = col.models
    existing = mm.by_name(MODEL_NAME)
    if existing:
        return existing
    m = mm.new(MODEL_NAME)
    mm.add_field(m, mm.new_field("Front"))
    mm.add_field(m, mm.new_field("Back"))
    tmpl = mm.new_template("Card 1")
    tmpl["qfmt"] = "{{Front}}"
    tmpl["afmt"] = '{{FrontSide}}\n\n<hr id="answer">\n\n{{Back}}'
    mm.add_template(m, tmpl)
    mm.add(m)
    return mm.by_name(MODEL_NAME)


def seed(base_dir: str) -> int:
    col_path = os.path.join(base_dir, "User 1", "collection.anki2")
    os.makedirs(os.path.dirname(col_path), exist_ok=True)

    col = Collection(col_path)
    try:
        if col.find_notes(f"tag:{SEED_TAG}"):
            print(f"MCAT deck already present in {col_path} - nothing to do.")
            return 0

        model = _get_or_create_model(col)
        deck_id = col.decks.id(DECK_NAME)
        added = 0
        for cc, front, back in CARDS:
            note = col.new_note(model)
            note["Front"] = front
            note["Back"] = back
            note.tags = ["Speedrun", SEED_TAG, f"MCAT::{_section_for(cc)}::{cc}"]
            col.add_note(note, deck_id)
            added += 1
        # note: saving is automatic in modern Anki; close() below flushes.
        print(f"Seeded {added} MCAT cards into deck '{DECK_NAME}' at {col_path}")
        return 0
    finally:
        col.close()


def main() -> int:
    base_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.getcwd(), "extra", "speedrun-base"
    )
    return seed(base_dir)


if __name__ == "__main__":
    raise SystemExit(main())
