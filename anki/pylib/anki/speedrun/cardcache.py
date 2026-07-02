"""Per-card card-type cache (stored as a tag) so the disconfirmer gating is instant.

The type is decided once (AI when enabled, else heuristic) and cached as a
``speedrun_ctype::<type>`` tag; review-time gating just reads it. Pure collection logic
(no Qt) so it ships in the anki library and is unit-testable.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from anki.speedrun.cardtype import CardType
from anki.utils import strip_html

CTYPE_TAG_PREFIX = "speedrun_ctype"
#: Named source of the cached label ("AI_<model>" or "heuristic"), so every AI output
#: traces back to a source right on the card.
CTYPE_SRC_TAG_PREFIX = "speedrun_ctype_src"


def cached_card_type(note) -> Optional[CardType]:
    prefix = f"{CTYPE_TAG_PREFIX}::"
    for tag in note.tags:
        if tag.startswith(prefix):
            try:
                return CardType(tag[len(prefix) :])
            except ValueError:
                return None
    return None


def _tag_safe(text: str) -> str:
    """Make a source string usable as a single tag (no spaces; keep it readable)."""
    return "".join(c if (c.isalnum() or c in "-.") else "_" for c in text)


def set_cached_card_type(col, note, card_type: CardType, source: Optional[str] = None) -> None:
    tprefix = f"{CTYPE_TAG_PREFIX}::"
    sprefix = f"{CTYPE_SRC_TAG_PREFIX}::"
    note.tags = [
        t for t in note.tags if not t.startswith(tprefix) and not t.startswith(sprefix)
    ]
    note.tags.append(f"{tprefix}{card_type.value}")
    if source:
        note.tags.append(f"{sprefix}{_tag_safe(source)}")
    col.update_note(note)


def uncached_items(col, search: str, limit: int = 60) -> List[Tuple[int, str, str]]:
    """(note_id, question, answer) for notes matching ``search``, capped at ``limit``."""
    items: List[Tuple[int, str, str]] = []
    for nid in col.find_notes(search)[:limit]:
        note = col.get_note(nid)
        question = strip_html(note.fields[0]) if note.fields else ""
        answer = strip_html(note.fields[1]) if len(note.fields) > 1 else ""
        items.append((nid, question, answer))
    return items
