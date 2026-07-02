# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Collection-side glue for the fading ladder: persist per-family counters and map
a reviewed card back to its concept family. Pure-logic lives in anki.speedrun.fading.
"""

from __future__ import annotations

from typing import Dict, Optional

from anki.speedrun import anticrutch, fading
from anki.speedrun.cardtype import CardType, heuristic_classify
from anki.speedrun.disconfirmer import (
    ASSISTED_TAG,
    NOTETYPE_NAME,
    TAG_PREFIX,
    TRANSFER_TAG,
    family_from_note,
)
from anki.utils import strip_html

CONFIG_KEY = "speedrun_fading"
CRUTCH_KEY = "speedrun_ai_crutch"
#: Collection-config flag (default on). When off, per-family support-fading updates are
#: skipped - the "feature-off" arm of the spec section-8 ablation.
FADING_ENABLED_KEY = "speedrun_fading_enabled"
#: Per-family fading rung, written as a syncable tag on reviewed application notes so the
#: cross-platform review tier can read it (SPOV 4: desktop prepare -> syncable artifact).
RUNG_TAG_PREFIX = "speedrun_rung"


def load_state(col) -> Dict:
    return col.get_config(CONFIG_KEY, default={}) or {}


def save_state(col, state: Dict) -> None:
    col.set_config(CONFIG_KEY, state)


def fading_enabled(col) -> bool:
    """Whether per-family support-fading runs (default True). Off = ablation arm."""
    val = col.get_config(FADING_ENABLED_KEY, default=None)
    return True if val is None else bool(val)


def set_fading_enabled(col, enabled: bool) -> None:
    col.set_config(FADING_ENABLED_KEY, bool(enabled))


def load_crutch(col) -> Dict:
    return col.get_config(CRUTCH_KEY, default=None) or anticrutch.empty_state()


def save_crutch(col, state: Dict) -> None:
    col.set_config(CRUTCH_KEY, state)


def average_recall_for_family(col, family: str) -> Optional[float]:
    """Per-family average FSRS recall from the Rust mastery query (None if unknown)."""
    res = col.topic_mastery(tag_prefix=TAG_PREFIX, min_cards_for_average=1)
    for topic in res.topics:
        tag = topic.tag
        code = tag.split("::")[-1] if "::" in tag else tag
        if code == family and topic.HasField("average_recall"):
            return topic.average_recall
    return None


def rung_for_family(col, family: str) -> fading.Rung:
    state = load_state(col)
    return fading.current_rung(state, family, average_recall_for_family(col, family))


def _note_is_declarative(note) -> bool:
    """Item-level rote check (SPOV 10 excludes declarative recall from fading).

    Disconfirmer cards are discrimination/application by construction, so they are never
    treated as declarative; everything else is judged by the deterministic heuristic.
    """
    if note.note_type()["name"] == NOTETYPE_NAME:
        return False
    question = strip_html(note.fields[0]) if note.fields else ""
    answer = strip_html(note.fields[1]) if len(note.fields) > 1 else ""
    return heuristic_classify(question, answer) is CardType.DECLARATIVE


def _tag_note_rung(col, note, rung: fading.Rung) -> None:
    prefix = f"{RUNG_TAG_PREFIX}::"
    new_tags = [t for t in note.tags if not t.startswith(prefix)]
    new_tags.append(f"{prefix}{rung.value}")
    if new_tags != note.tags:
        note.tags = new_tags
        col.update_note(note)


def record_answer(col, card, ease: int) -> None:
    """On any review: update the fading ladder (and, for disconfirmers, anti-crutch).

    The fading ladder is driven by **real study-card reviews** per concept-family, not
    only disconfirmer cards; declarative items are excluded (SPOV 10). The resulting rung
    is written back as a syncable tag so the review tier can read it.
    """
    note = card.note()
    success = ease >= 2  # Again=1 is the only "failed to recall" grade
    is_disconfirmer = note.note_type()["name"] == NOTETYPE_NAME

    # Anti-crutch: scoped to disconfirmer reviews (AI-assisted vs not).
    if is_disconfirmer:
        crutch = load_crutch(col)
        anticrutch.record_outcome(crutch, assisted=ASSISTED_TAG in note.tags, correct=success)
        save_crutch(col, crutch)

    # Per-family support-fading (SPOV 10). Skippable for the section-8 ablation arm.
    if not fading_enabled(col):
        return

    # The fading ladder now lives in the shared Rust engine (Stage 2): it
    # normalises the family key to the AAMC content-category code the dashboard
    # reads - fixing the desktop key-mismatch bug where the ladder never advanced
    # visibly - excludes declarative items, and writes both the config state and
    # the syncable ``speedrun_rung::Lx`` tag in one undoable step. Desktop and
    # AnkiDroid now share this one implementation.
    col.speedrun_record_review(card_id=card.id, rating=ease)
