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
    topic_tag,
    upgrade_topic_tag,
)
from anki.speedrun.sample_content import (
    DISCONFIRMER_SEED,
    PERFORMANCE_SEED,
    PRETEST_SEED,
    SAMPLE_CARDS,
)

SAMPLE_DECK = "Speedrun MCAT (sample)"
SAMPLE_TAG = "speedrun_sample"
DISC_SEED_TAG = "speedrun_disc_seed"
PRETEST_DECK = "Speedrun Pretest (sample)"
PRETEST_SEED_TAG = "speedrun_pretest_seed"
PERF_DECK = "Speedrun Qbank (sample)"
PERF_NOTETYPE = "Speedrun Performance Item"
PERF_SEED_TAG = "speedrun_perf_seed"


def _covered_codes(col) -> set:
    """Content-category codes that already have at least one card, using the same
    tag->category rule as the dashboard (the most-specific ``::`` part that is a known
    code). Lets seeding top up only the categories that are still missing."""
    known = set(SAMPLE_CARDS.keys())
    covered: set = set()
    for nid in col.find_notes(f"tag:{TAG_PREFIX}::*"):
        for tag in col.get_note(nid).tags:
            for part in reversed(tag.split("::")):
                if part in known:
                    covered.add(part)
                    break
    return covered


def seed_sample_deck(col) -> int:
    """Create or top up the original sample deck so every AAMC content category has at
    least one card. Idempotent per-category: re-running adds only the categories that
    are still missing (e.g. a collection seeded from an older, smaller set, or one that
    imported only a partial deck), so coverage can reach 100%. Returns cards added."""
    deck_id = col.decks.id(SAMPLE_DECK)
    model = col.models.by_name("Basic") or col.models.current()
    covered = _covered_codes(col)
    added = 0
    for code, qas in SAMPLE_CARDS.items():
        if code in covered:
            continue
        tag = topic_tag(code)
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
            note.tags = [topic_tag(item["family"]), PRETEST_SEED_TAG]
            col.add_note(note, deck_id)
            added += 1
    return added


def seed_performance_deck(col) -> int:
    """Seed the sample exam-style Qbank (SPOV 3 / memory->performance). Returns count.

    Items use the shared ``Speedrun Performance Item`` note type (created in the Rust
    engine so the interactive MC template matches), are tagged with their AAMC
    content-category code so they roll up per section (and recall links to the sample
    memory cards of the same code), and are ``holdout::performance``. Idempotent.
    """
    if col.find_notes(f"tag:{PERF_SEED_TAG}"):
        return 0
    # Ensure the shared note type exists (Rust engine; idempotent).
    try:
        col.speedrun_ensure_notetypes()
    except Exception:
        pass
    nt = col.models.by_name(PERF_NOTETYPE)
    if nt is None:
        return 0
    deck_id = col.decks.id(PERF_DECK)
    index = {f: i for i, f in enumerate(col.models.field_names(nt))}
    added = 0
    for item in PERFORMANCE_SEED:
        note = col.new_note(nt)
        note.fields[index["ConceptId"]] = item.get("concept", "")
        note.fields[index["Stem"]] = item["stem"]
        note.fields[index["OptionA"]] = item["options"]["A"]
        note.fields[index["OptionB"]] = item["options"]["B"]
        note.fields[index["OptionC"]] = item["options"]["C"]
        note.fields[index["OptionD"]] = item["options"]["D"]
        note.fields[index["Correct"]] = item["correct"]
        note.fields[index["Rationale"]] = item.get("rationale", "")
        note.fields[index["Variant"]] = "1"
        note.tags = [
            topic_tag(item["family"]),
            f"concept::{item.get('concept', '')}",
            "holdout::performance",
            "perf::paraphrase",
            PERF_SEED_TAG,
        ]
        col.add_note(note, deck_id)
        added += 1
    return added


TAG_TITLES_MIGRATED_KEY = "speedrun_tag_titles_migrated"


def migrate_topic_tags(col) -> int:
    """One-time upgrade of existing bare ``MCAT::<code>`` tags to the readable
    ``MCAT::<code>::<Title>`` form, so a collection seeded before this change reads
    meaningfully. Additive (the code stays its own segment, so coverage is unchanged)
    and idempotent (guarded by a config flag). Returns the number of notes updated."""
    if col.get_config(TAG_TITLES_MIGRATED_KEY, default=False):
        return 0
    updated = 0
    for nid in col.find_notes(f"tag:{TAG_PREFIX}::*"):
        note = col.get_note(nid)
        new_tags = [upgrade_topic_tag(t) for t in note.tags]
        if new_tags != note.tags:
            note.tags = new_tags
            col.update_note(note)
            updated += 1
    col.set_config(TAG_TITLES_MIGRATED_KEY, True)
    return updated


def seed_all(col) -> Tuple[int, int, int, int]:
    """Seed all sample decks.

    Returns (sample, disconfirmer, pretest, qbank) card counts.
    """
    migrate_topic_tags(col)  # make any pre-existing MCAT tags human-readable
    return (
        seed_sample_deck(col),
        seed_disconfirmer_deck(col),
        seed_pretest_deck(col),
        seed_performance_deck(col),
    )
