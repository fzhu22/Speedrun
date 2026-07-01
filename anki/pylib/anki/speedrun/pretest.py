"""The Speedrun Pretest note type (brainlift v3-focused SPOV 13: pretest-first).

First exposure to new material runs as a forced "commit a guess -> reveal -> mandatory
in-session feedback" card. This is built as a *real Anki note type* using the native
type-in-the-answer field (``{{type:Answer}}``), so the whole experience lives in the
card template (the cross-platform "review" tier) and renders on desktop and any stock
review client - no desktop-only modal layered over the reviewer.

Why a template, not a dialog (SPOV 4 / brownfield): the review tier must be card-template
driven so it works on AnkiMobile/AnkiDroid; the desktop only "prepares" (creates the note
type + seeds content). Feedback is load-bearing - without it the testing effect at low
first-exposure accuracy is ~0 (Rowland, 2014) - so the back always reveals the answer plus
an explanation. The benefit is banked to the specific item (no claimed topic spillover).

No Qt imports here; the GUI drives it. No AI is used.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import anki.collection
from anki.models import NotetypeDict
from anki.notes import NoteId
from anki.speedrun.disconfirmer import TAG_PREFIX

NOTETYPE_NAME = "Speedrun Pretest"
NOTE_TAG = "speedrun_pretest"
#: Collection-config flag (default on). When off, first-exposure content is seeded as
#: plain Basic cards - the "feature-off" arm of the spec section-8 ablation.
PRETEST_ENABLED_KEY = "speedrun_pretest_enabled"

#: Field order. ``Answer`` is the type-in target; ``Explanation`` is the mandatory
#: corrective feedback shown on reveal.
FIELDS: List[str] = ["Question", "Answer", "Explanation", "Source", "ConceptFamily"]

_FRONT = """\
<div class="sr-card">
  <div class="sr-q">{{Question}}</div>
  <div class="sr-prompt">Commit your best guess, then reveal.</div>
  {{type:Answer}}
</div>
"""

_BACK = """\
{{FrontSide}}
<hr id="answer">
<div class="sr-card">
  <div class="sr-a"><span class="lbl">Answer</span>{{type:Answer}}</div>
  {{#Explanation}}<div class="sr-why"><span class="lbl">Why</span>{{Explanation}}</div>{{/Explanation}}
  {{#Source}}<div class="sr-prov">Source: {{Source}}</div>{{/Source}}
</div>
"""

_CSS = """\
.card { font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, Arial; color: inherit; }
.sr-card { max-width: 640px; margin: 0 auto; text-align: left; }
.sr-q { font-size: 20px; font-weight: 600; margin-bottom: 10px; }
.sr-prompt { font-style: italic; opacity: .75; margin-bottom: 12px; }
.sr-a { font-size: 18px; margin: 8px 0; }
.sr-why { background: rgba(84,160,255,.15); border-left: 3px solid #54a0ff; padding: 8px 10px; border-radius: 6px; margin: 10px 0; }
.sr-prov { opacity: .6; font-size: 12px; margin-top: 10px; }
.lbl { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .4px; opacity: .6; }
"""


def ensure_notetype(col: anki.collection.Collection) -> NotetypeDict:
    """Create the Speedrun Pretest note type if missing; return it (idempotent)."""
    existing = col.models.by_name(NOTETYPE_NAME)
    if existing is not None:
        return existing

    nt = col.models.new(NOTETYPE_NAME)
    for field_name in FIELDS:
        col.models.add_field(nt, col.models.new_field(field_name))
    template = col.models.new_template("Card 1")
    template["qfmt"] = _FRONT
    template["afmt"] = _BACK
    col.models.add_template(nt, template)
    nt["css"] = _CSS
    col.models.set_sort_index(nt, FIELDS.index("Question"))
    col.models.add_dict(nt)
    fetched = col.models.by_name(NOTETYPE_NAME)
    assert fetched is not None
    return fetched


def build_note(
    col: anki.collection.Collection,
    *,
    fields: Dict[str, str],
    family: str,
    deck_id: int,
) -> NoteId:
    """Create and add a Speedrun Pretest note. Returns the new note id."""
    nt = ensure_notetype(col)
    note = col.new_note(nt)
    index = {name: i for i, name in enumerate(col.models.field_names(nt))}
    for name, value in fields.items():
        if name in index:
            note.fields[index[name]] = value
    if family and "ConceptFamily" in index:
        note.fields[index["ConceptFamily"]] = family
    tags = [NOTE_TAG]
    if family:
        tags.append(f"{TAG_PREFIX}::{family}")
    note.tags = tags
    col.add_note(note, deck_id)
    return note.id


# -- ablation toggle (spec section 8) -----------------------------------------


def pretest_enabled(col: anki.collection.Collection) -> bool:
    """Whether first-exposure content uses the pretest mode (default True)."""
    val = col.get_config(PRETEST_ENABLED_KEY, default=None)
    return True if val is None else bool(val)


def set_pretest_enabled(col: anki.collection.Collection, enabled: bool) -> None:
    col.set_config(PRETEST_ENABLED_KEY, bool(enabled))
