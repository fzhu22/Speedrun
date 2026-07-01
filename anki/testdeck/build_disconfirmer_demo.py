# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: build a tiny deck of APPLICATION cards that trigger the in-review
disconfirmer prompt.

The shared Rust classifier marks a card "application" when its question contains a
reasoning marker (why / predict / compare / what would / patient / if / ...); an
application card prompts for a disconfirmer on the first Again/Hard, on both
desktop and AnkiDroid. Cards are MCAT-tagged so the desktop review scope
(`scope == "mcat"`) accepts them. Exports disconfirmer_demo.apkg.

Run with the repo's built Python from the anki repo root:
    out/pyenv/Scripts/python testdeck/build_disconfirmer_demo.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANKI_ROOT = HERE.parent
os.chdir(ANKI_ROOT)
sys.path.extend(["pylib", "qt", "out/pylib", "out/qt"])

from anki.collection import Collection, ExportAnkiPackageOptions  # noqa: E402

OUT_APKG = HERE / "disconfirmer_demo.apkg"
DECK = "Speedrun Disconfirmer Demo"

# (front, back, tag) - every front contains an application marker, so the shared
# classifier returns Application and a first Again/Hard triggers the prompt.
CARDS = [
    (
        "Why does a noncompetitive inhibitor lower Vmax but leave Km unchanged?",
        "It binds an allosteric site and lowers the amount of functional enzyme, so the "
        "maximum rate falls while the affinity of the remaining enzyme is unchanged.",
        "MCAT::BioBiochem::1A",
    ),
    (
        "A patient hyperventilates and blood pH rises; what would happen to cerebral blood flow and why?",
        "It decreases - low CO2 causes cerebral vasoconstriction (respiratory alkalosis), reducing flow.",
        "MCAT::BioBiochem::3B",
    ),
    (
        "Predict how doubling the nucleophile concentration changes the rate of an SN2 versus an SN1 reaction.",
        "SN2 rate doubles (bimolecular, depends on nucleophile); SN1 rate is unchanged (unimolecular rate-limiting step).",
        "MCAT::ChemPhys::5D",
    ),
    (
        "If you raise the temperature of an exothermic reaction at equilibrium, what happens to Keq and why?",
        "Keq decreases - heat behaves as a product, so by Le Chatelier the equilibrium shifts toward reactants.",
        "MCAT::ChemPhys::5A",
    ),
    (
        "Compare how a myelinated and an unmyelinated axon conduct an action potential.",
        "Myelinated axons use saltatory conduction (node to node), which is faster and more energy-efficient than the continuous conduction of unmyelinated axons.",
        "MCAT::BioBiochem::3A",
    ),
    (
        "Why does placing a cell in a hypertonic solution change its volume, and in which direction?",
        "The cell shrinks - water leaves down its osmotic gradient toward the higher external solute concentration.",
        "MCAT::BioBiochem::2A",
    ),
]


def main() -> None:
    tmpdir = tempfile.mkdtemp(prefix="disc_demo_")
    col = Collection(os.path.join(tmpdir, "collection.anki2"))
    try:
        basic = col.models.by_name("Basic")
        did = col.decks.id(DECK)
        for front, back, tag in CARDS:
            note = col.new_note(basic)
            note["Front"] = front
            note["Back"] = back
            note.tags = [tag]
            col.add_note(note, did)
        col.export_anki_package(
            out_path=str(OUT_APKG),
            options=ExportAnkiPackageOptions(
                with_scheduling=False,
                with_deck_configs=False,
                with_media=False,
                legacy=True,
            ),
            limit=None,
        )
    finally:
        col.close()
    print("Built", OUT_APKG, "with", len(CARDS), "application cards in deck", DECK)


if __name__ == "__main__":
    main()
