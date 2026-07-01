# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: Python-calls-Rust test for the shared review-time backend.

Exercises the Stage 2 methods that moved from desktop-only Python into the shared
Rust engine: the support-fading ladder (with the family-key bug fix) and the
disconfirmer gating decision."""

from tests.shared import getEmptyCol


def _add_mcat_card(col, front, back, tags):
    note = col.newNote()
    note["Front"] = front
    note["Back"] = back
    note.tags = tags
    col.addNote(note)
    return note


def test_speedrun_record_review_normalises_family_and_tags_rung():
    col = getEmptyCol()

    note = _add_mcat_card(
        col,
        "Why does raising the pH above the pKa shift the equilibrium?",
        "The conjugate base dominates across the buffer region.",
        ["MCAT::BioBiochem::1A::AminoAcids", "speedrun_transfer"],
    )
    card_id = col.card_ids_of_note(note.id)[0]

    # The returned family is the AAMC content-category CODE the dashboard reads
    # ("1A"), not the raw MCAT:: tag suffix - the fix for the key-mismatch bug.
    res = col.speedrun_record_review(card_id=card_id, rating=3)
    assert res.family == "1A"
    assert res.rung in {"L3", "L2", "L1", "L0"}

    # The rung is written back as a syncable tag on the note.
    reloaded = col.get_note(note.id)
    assert any(t.startswith("speedrun_rung::") for t in reloaded.tags)

    # The persisted fading state is keyed by the cc code (so the dashboard rung
    # and the recorded rung agree), never by the raw suffix.
    state = col.get_config("speedrun_fading", default={})
    assert "1A" in state
    assert "BioBiochem::1A::AminoAcids" not in state

    col.close()


def test_speedrun_should_prompt_disconfirmer():
    col = getEmptyCol()

    application = _add_mcat_card(
        col,
        "Why does myoglobin hold oxygen more tightly than hemoglobin at low pO2?",
        "Its hyperbolic binding curve gives a higher affinity across partial pressures.",
        ["MCAT::BioBiochem::1A"],
    )
    declarative = _add_mcat_card(
        col, "How many amino acids are proteinogenic?", "20", ["MCAT::BioBiochem::1A"]
    )
    app_card = col.card_ids_of_note(application.id)[0]
    decl_card = col.card_ids_of_note(declarative.id)[0]

    # Application card, first miss (Again) -> prompt, not yet struggling.
    decision = col.speedrun_should_prompt_disconfirmer(
        card_id=app_card, rating=1, session_misses=0
    )
    assert decision.should_prompt
    assert not decision.struggling

    # Declarative card, first miss -> re-study, no prompt.
    decision = col.speedrun_should_prompt_disconfirmer(
        card_id=decl_card, rating=1, session_misses=0
    )
    assert not decision.should_prompt

    # Declarative but clearly struggling (repeated in-session misses) -> prompt.
    decision = col.speedrun_should_prompt_disconfirmer(
        card_id=decl_card, rating=1, session_misses=2
    )
    assert decision.should_prompt
    assert decision.struggling

    col.close()


def test_speedrun_validate_and_create_disconfirmer():
    col = getEmptyCol()

    note = _add_mcat_card(
        col,
        "Why does raising the pH above the pKa shift the equilibrium?",
        "The conjugate base dominates.",
        ["MCAT::BioBiochem::1A::AminoAcids"],
    )
    card_id = col.card_ids_of_note(note.id)[0]

    # A blank disconfirmer is rejected; a genuine one is accepted ("").
    assert col.speedrun_validate_disconfirmer(text="", answer="conjugate base") != ""
    assert (
        col.speedrun_validate_disconfirmer(
            text="If the pH dropped below the pKa, the acid form would dominate instead.",
            answer="the conjugate base dominates",
        )
        == ""
    )

    # Creating a disconfirmer from the missed card returns a new note id, tags the
    # original as disconfirmed, and lands the new card in the disconfirmer deck.
    new_id = col.speedrun_create_disconfirmer(
        card_id=card_id,
        disconfirmer="If the pH dropped below the pKa, the acid form would dominate instead.",
        principle="Henderson-Hasselbalch",
    )
    assert new_id
    new_note = col.get_note(new_id)
    assert "speedrun_disconfirmer" in new_note.tags
    assert "speedrun_disconfirmed" in col.get_note(note.id).tags

    col.close()
