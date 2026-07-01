# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: build the MCAT test deck (.apkg) from the source files in this folder.

Run with the repo's built Python environment from the anki repo root, e.g.:

    out/pyenv/Scripts/python testdeck/build_deck.py      # Windows
    out/pyenv/bin/python testdeck/build_deck.py          # macOS/Linux

It defines two custom note types (Speedrun Performance Item, Speedrun Disconfirmer),
loads the memory CSVs, the held-out performance items, and the disconfirmer cards,
adds them with their tags into section subdecks, and exports mcat_test_deck.apkg.

This is a development test fixture (the product ships no deck). All content is
originally authored; no copyrighted stems are stored.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANKI_ROOT = HERE.parent

# Import the in-tree `anki` package exactly the way tools/run.py does: the package
# is a namespace merged from the source (pylib) and generated (out/pylib) trees.
os.chdir(ANKI_ROOT)
sys.path.extend(["pylib", "qt", "out/pylib", "out/qt"])

from anki.collection import Collection, ExportAnkiPackageOptions  # noqa: E402

OUT_APKG = HERE / "mcat_test_deck.apkg"

CSV_TO_DECK = {
    "memory_bio_biochem.csv": "MCAT::BioBiochem",
    "memory_chem_phys.csv": "MCAT::ChemPhys",
    "memory_psych_soc.csv": "MCAT::PsychSoc",
}

PERF_NOTETYPE = "Speedrun Performance Item"
DISC_NOTETYPE = "Speedrun Disconfirmer"


def ensure_performance_notetype(col: Collection):
    mm = col.models
    existing = mm.by_name(PERF_NOTETYPE)
    if existing:
        return existing
    nt = mm.new(PERF_NOTETYPE)
    for field in ["ConceptId", "Stem", "OptionA", "OptionB", "OptionC", "OptionD", "Correct", "Rationale", "Variant"]:
        mm.add_field(nt, mm.new_field(field))
    tmpl = mm.new_template("Card 1")
    tmpl["qfmt"] = (
        "{{Stem}}<br><br>"
        "A) {{OptionA}}<br>B) {{OptionB}}<br>C) {{OptionC}}<br>D) {{OptionD}}"
    )
    tmpl["afmt"] = (
        "{{FrontSide}}<hr id=answer>"
        "<b>Correct: {{Correct}}</b><br>{{Rationale}}"
    )
    mm.add_template(nt, tmpl)
    mm.add_dict(nt)
    return mm.by_name(PERF_NOTETYPE)


def ensure_disconfirmer_notetype(col: Collection):
    mm = col.models
    existing = mm.by_name(DISC_NOTETYPE)
    if existing:
        return existing
    nt = mm.new(DISC_NOTETYPE)
    for field in ["Provenance", "Principle", "OriginalCoverStory", "SwappedCoverStory", "Trap", "Disconfirmer", "BoundaryCase"]:
        mm.add_field(nt, mm.new_field(field))
    tmpl = mm.new_template("Card 1")
    tmpl["qfmt"] = (
        "<b>Principle:</b> {{Principle}}<br><br>"
        "<b>Scenario:</b> {{SwappedCoverStory}}<br><br>"
        "What one fact would flip this answer?"
    )
    tmpl["afmt"] = (
        "{{FrontSide}}<hr id=answer>"
        "<b>Disconfirmer:</b> {{Disconfirmer}}<br><br>"
        "<b>Trap:</b> {{Trap}}<br>"
        "<b>Boundary case:</b> {{BoundaryCase}}<br><br>"
        "<i>Provenance: {{Provenance}}</i>"
    )
    mm.add_template(nt, tmpl)
    mm.add_dict(nt)
    return mm.by_name(DISC_NOTETYPE)


def load_memory_cards(col: Collection) -> int:
    basic = col.models.by_name("Basic")
    count = 0
    for filename, deck_name in CSV_TO_DECK.items():
        did = col.decks.id(deck_name)
        with open(HERE / filename, encoding="utf-8") as fh:
            rows = [line for line in fh if not line.startswith("#")]
        for front, back, tags in csv.reader(rows):
            note = col.new_note(basic)
            note["Front"] = front
            note["Back"] = back
            note.tags = tags.split()
            col.add_note(note, did)
            count += 1
    return count


def load_performance_items(col: Collection) -> int:
    nt = ensure_performance_notetype(col)
    did = col.decks.id("MCAT::Performance")
    data = json.loads((HERE / "performance_items.json").read_text(encoding="utf-8"))
    count = 0
    for concept in data["concepts"]:
        cid = concept["concept_id"]
        section_tag = concept["section_tag"]
        for item in concept["items"]:
            note = col.new_note(nt)
            note["ConceptId"] = cid
            note["Stem"] = item["stem"]
            note["OptionA"] = item["options"]["A"]
            note["OptionB"] = item["options"]["B"]
            note["OptionC"] = item["options"]["C"]
            note["OptionD"] = item["options"]["D"]
            note["Correct"] = item["correct"]
            note["Rationale"] = item["rationale"]
            note["Variant"] = str(item["variant"])
            note.tags = [
                section_tag,
                f"concept::{cid}",
                "perf::paraphrase",
                "holdout::performance",
                f"variant::{item['variant']}",
            ]
            col.add_note(note, did)
            count += 1
    return count


def load_disconfirmer_cards(col: Collection) -> int:
    nt = ensure_disconfirmer_notetype(col)
    did = col.decks.id("MCAT::Disconfirmer")
    data = json.loads((HERE / "disconfirmer_cards.json").read_text(encoding="utf-8"))
    count = 0
    for card in data["cards"]:
        note = col.new_note(nt)
        note["Provenance"] = card["provenance"]
        note["Principle"] = card["principle"]
        note["OriginalCoverStory"] = card["original_cover_story"]
        note["SwappedCoverStory"] = card["swapped_cover_story"]
        note["Trap"] = card["trap"]
        note["Disconfirmer"] = card["disconfirmer"]
        note["BoundaryCase"] = card["boundary_case"]
        validity = "disconfirmer::valid" if card.get("expected_validation") == "pass" else "disconfirmer::invalid"
        note.tags = [card["section_tag"], "notetype::disconfirmer", validity]
        col.add_note(note, did)
        count += 1
    return count


def coverage_summary() -> str:
    outline = json.loads((HERE / "mcat_outline.json").read_text(encoding="utf-8"))
    total = covered = 0
    lines = []
    for section in outline["sections"]:
        cats = section["content_categories"]
        sec_total = len(cats)
        sec_covered = sum(1 for c in cats if c["covered"])
        total += sec_total
        covered += sec_covered
        lines.append(f"  {section['id']}: {sec_covered}/{sec_total} categories")
    pct = 100.0 * covered / total if total else 0.0
    lines.append(f"  overall: {covered}/{total} = {pct:.0f}% coverage")
    return "\n".join(lines)


def main() -> None:
    tmpdir = tempfile.mkdtemp(prefix="mcat_testdeck_")
    col_path = os.path.join(tmpdir, "collection.anki2")
    col = Collection(col_path)
    try:
        n_mem = load_memory_cards(col)
        n_perf = load_performance_items(col)
        n_disc = load_disconfirmer_cards(col)

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

    print("Built", OUT_APKG)
    print(f"  memory cards:        {n_mem}")
    print(f"  performance items:   {n_perf} (held-out)")
    print(f"  disconfirmer cards:  {n_disc}")
    print(f"  total notes:         {n_mem + n_perf + n_disc}")
    print("Coverage vs MCAT outline:")
    print(coverage_summary())


if __name__ == "__main__":
    main()
