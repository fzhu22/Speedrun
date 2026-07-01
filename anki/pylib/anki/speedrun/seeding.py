# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Seed the original sample MCAT deck and a disconfirmer deck (so the fade has data).

All content is original and labelled `[Sample]`; nothing copyrighted is shipped. Both
seeders are idempotent (guarded by a marker tag). Pure collection logic - no Qt - so
it ships in the anki library and is unit-testable.
"""

from __future__ import annotations

from typing import Tuple

from anki.speedrun import pretest
from anki.speedrun.disconfirmer import (
    DISCONFIRMER_DECK,
    TAG_PREFIX,
    build_note,
    ensure_notetype,
)
from anki.speedrun.sample_content import (
    DISCONFIRMER_SEED,
    PRETEST_SEED,
    SAMPLE_CARDS,
)

SAMPLE_DECK = "Speedrun MCAT (sample)"
SAMPLE_TAG = "speedrun_sample"
DISC_SEED_TAG = "speedrun_disc_seed"
PRETEST_DECK = "Speedrun Pretest (sample)"
PRETEST_SEED_TAG = "speedrun_pretest_seed"


def seed_sample_deck(col) -> int:
    """Create the original sample content deck. Returns the number of cards added."""
    if col.find_notes(f"tag:{SAMPLE_TAG}"):
        return 0
    deck_id = col.decks.id(SAMPLE_DECK)
    model = col.models.by_name("Basic") or col.models.current()
    added = 0
    for code, qas in SAMPLE_CARDS.items():
        tag = f"{TAG_PREFIX}::{code}"
        for front, back in qas:
            note = col.new_note(model)
            note.fields[0] = front
            note.fields[1] = back
            note.tags = [tag, SAMPLE_TAG]
            col.add_note(note, deck_id)
            added += 1
    return added


def seed_disconfirmer_deck(col) -> int:
    """Create seed Speedrun Disconfirmer cards (incl. transfer items). Returns count."""
    if col.find_notes(f"tag:{DISC_SEED_TAG}"):
        return 0
    ensure_notetype(col)
    deck_id = col.decks.id(DISCONFIRMER_DECK)
    added = 0
    for spec in DISCONFIRMER_SEED:
        new_id = build_note(
            col,
            fields=dict(spec["fields"]),
            family=spec["family"],
            deck_id=deck_id,
            transfer_item=bool(spec.get("transfer")),
        )
        note = col.get_note(new_id)
        if DISC_SEED_TAG not in note.tags:
            note.tags.append(DISC_SEED_TAG)
            col.update_note(note)
        added += 1
    return added


def seed_pretest_deck(col) -> int:
    """Seed the pretest-first sample deck (SPOV 13). Returns the number of cards added.

    Honors the ``speedrun_pretest_enabled`` toggle: when on, content is seeded as
    ``Speedrun Pretest`` type-in cards (forced guess -> reveal -> feedback); when off,
    the same content is seeded as plain Basic cards - the section-8 ablation arm.
    """
    if col.find_notes(f"tag:{PRETEST_SEED_TAG}"):
        return 0
    deck_id = col.decks.id(PRETEST_DECK)
    enabled = pretest.pretest_enabled(col)
    added = 0
    if enabled:
        pretest.ensure_notetype(col)
        for item in PRETEST_SEED:
            new_id = pretest.build_note(
                col,
                fields={
                    "Question": item["question"],
                    "Answer": item["answer"],
                    "Explanation": item.get("explanation", ""),
                    "Source": item.get("source", ""),
                },
                family=item["family"],
                deck_id=deck_id,
            )
            note = col.get_note(new_id)
            if PRETEST_SEED_TAG not in note.tags:
                note.tags.append(PRETEST_SEED_TAG)
                col.update_note(note)
            added += 1
    else:
        basic = col.models.by_name("Basic") or col.models.current()
        for item in PRETEST_SEED:
            note = col.new_note(basic)
            note.fields[0] = item["question"]
            back = item["answer"]
            if item.get("explanation"):
                back = f"{back}<br><br>{item['explanation']}"
            note.fields[1] = back
            note.tags = [f"{TAG_PREFIX}::{item['family']}", PRETEST_SEED_TAG]
            col.add_note(note, deck_id)
            added += 1
    return added


def seed_all(col) -> Tuple[int, int, int]:
    """Seed all sample decks.

    Returns (sample_cards_added, disconfirmer_cards_added, pretest_cards_added).
    """
    return (
        seed_sample_deck(col),
        seed_disconfirmer_deck(col),
        seed_pretest_deck(col),
    )
