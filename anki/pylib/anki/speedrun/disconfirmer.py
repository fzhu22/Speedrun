"""The Speedrun Disconfirmer note type and its authoring helpers (PRD Section 6).

This is a *real* Anki note type, so its cards review like any flashcard. The card is
active-retrieval: the front poses the reworded question and asks "what one fact would
flip this answer?", and the back reveals the answer plus the disconfirmer, principle,
trap, boundary case, and the surface perturbation.

Nothing here imports Qt; the GUI (``aqt.speedrun``) drives it. The disconfirmer field
is required and validated (a nudge the student can override), per SPOV 1.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import anki.collection
from anki.models import NotetypeDict
from anki.notes import NoteId
from anki.speedrun.aamc_outline import load_outline_graph
from anki.speedrun.models import NodeKind
from anki.speedrun.textutil import containment, token_set

NOTETYPE_NAME = "Speedrun Disconfirmer"
NOTE_TAG = "speedrun_disconfirmer"
TRANSFER_TAG = "speedrun_transfer"  # marks a held-out transfer/perturbed item
DISCONFIRMED_TAG = "speedrun_disconfirmed"  # marks an original card that now has one
ASSISTED_TAG = "speedrun_assisted"  # the disconfirmer was authored with an AI hint
DISCONFIRMER_DECK = "Speedrun Disconfirmers"
TAG_PREFIX = "MCAT"

#: Field order (SwappedCoverStory is the front question; see templates below).
FIELDS: List[str] = [
    "Principle",
    "OriginalCoverStory",
    "SwappedCoverStory",
    "Answer",
    "Trap",
    "Disconfirmer",
    "BoundaryCase",
    "Provenance",
    "ConceptFamily",
]

_FRONT = """\
<div class="sr-card">
  <div class="sr-q">{{SwappedCoverStory}}</div>
  <div class="sr-prompt">What one fact would flip this answer?</div>
</div>
"""

_BACK = """\
{{FrontSide}}
<hr id="answer">
<div class="sr-card">
  <div class="sr-a"><span class="lbl">Answer</span>{{Answer}}</div>
  {{#Disconfirmer}}<div class="sr-disc"><span class="lbl">Disconfirmer - what flips it</span>{{Disconfirmer}}</div>{{/Disconfirmer}}
  <details class="sr-more">
    <summary>More detail</summary>
    {{#Principle}}<div class="sr-row"><span class="lbl">Principle</span>{{Principle}}</div>{{/Principle}}
    {{#Trap}}<div class="sr-row"><span class="lbl">Trap</span>{{Trap}}</div>{{/Trap}}
    {{#BoundaryCase}}<div class="sr-row"><span class="lbl">Boundary case</span>{{BoundaryCase}}</div>{{/BoundaryCase}}
    {{#OriginalCoverStory}}<div class="sr-perturb"><span class="lbl">Reworded from</span>{{OriginalCoverStory}} &rarr; {{SwappedCoverStory}}</div>{{/OriginalCoverStory}}
    {{#Provenance}}<div class="sr-prov">Source: {{Provenance}}</div>{{/Provenance}}
  </details>
</div>
<script>
(function () {
  // Hide the "More detail" toggle when none of the secondary fields are filled.
  var d = document.querySelector(".sr-more");
  if (d && !d.querySelector(".sr-row, .sr-perturb, .sr-prov")) d.style.display = "none";
})();
</script>
"""

_CSS = """\
.card { font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, Arial; color: inherit; }
.sr-card { max-width: 620px; margin: 0 auto; text-align: left; }
.sr-q { font-size: 17px; font-weight: 600; margin-bottom: 10px; }
.sr-prompt { font-style: italic; opacity: .75; font-size: .9em; }
.sr-a { font-size: 16px; margin: 6px 0; }
.sr-disc { background: rgba(255,180,84,.15); border-left: 3px solid #ffb454; padding: 7px 10px; border-radius: 6px; margin: 8px 0; }
.sr-row { margin: 5px 0; }
.sr-perturb { margin: 6px 0; opacity: .85; }
.sr-prov { opacity: .6; font-size: 12px; margin-top: 8px; }
.sr-more { margin-top: 8px; }
.sr-more > summary { cursor: pointer; font-size: 12px; opacity: .7; }
.sr-more[open] > summary { margin-bottom: 6px; }
.lbl { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .4px; opacity: .6; }
"""


def ensure_notetype(col: anki.collection.Collection) -> NotetypeDict:
    """Create the Speedrun Disconfirmer note type if missing; return it (idempotent)."""
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
    # Sort by the question (SwappedCoverStory) in the browser.
    col.models.set_sort_index(nt, FIELDS.index("SwappedCoverStory"))
    col.models.add_dict(nt)
    # add_dict requires a re-fetch to get ids/ords populated.
    fetched = col.models.by_name(NOTETYPE_NAME)
    assert fetched is not None
    return fetched


def validate_disconfirmer(text: str, answer: str = "") -> Optional[str]:
    """Return a revise message if the disconfirmer is unusable, else None.

    Rejects a blank disconfirmer and one that merely restates the answer. This is a
    nudge, not an authoritative grader - the caller lets the student override.
    """
    stripped = (text or "").strip()
    if not stripped:
        return "The disconfirmer can't be empty - name the one fact that would flip the answer."
    answer_tokens = token_set(answer)
    if len(answer_tokens) >= 2:
        # If almost all of the answer's words reappear in the disconfirmer, it's
        # likely just restating the answer rather than naming what would flip it.
        if containment(answer_tokens, token_set(stripped)) >= 0.9:
            return (
                "This looks like it just restates the answer. Say what single fact, "
                "if true, would make the answer change."
            )
    return None


def build_note(
    col: anki.collection.Collection,
    *,
    fields: Dict[str, str],
    family: str,
    deck_id: int,
    transfer_item: bool = False,
) -> NoteId:
    """Create and add a Speedrun Disconfirmer note. Returns the new note id."""
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
        tags.append(topic_tag(family))
    if transfer_item:
        tags.append(TRANSFER_TAG)
    note.tags = tags
    col.add_note(note, deck_id)
    return note.id


def family_from_note(note) -> Optional[str]:
    """The concept family (content-category code) for a note: its ConceptFamily field,
    else the code parsed from an ``MCAT::`` tag. Handles both the bare ``MCAT::1A`` form
    and the readable ``MCAT::1A::<Title>`` form (returns ``1A`` for both)."""
    try:
        value = note["ConceptFamily"].strip()
        if value:
            return value
    except Exception:
        pass
    prefix = f"{TAG_PREFIX}::"
    codes = _known_codes()
    for tag in note.tags:
        if not tag.startswith(prefix):
            continue
        for part in reversed(tag.split("::")):
            if part in codes:
                return part
        return tag[len(prefix) :].split("::", 1)[0]  # unknown code: first segment
    return None


# -- topic tags (human-readable) ---------------------------------------------
#
# The coverage/mastery engine maps a card to its content category by finding the
# most-specific ``::`` segment that is exactly a known code (e.g. ``1A``). We keep that
# code as its own segment but append the AAMC title so tags read meaningfully - e.g.
# ``MCAT::1A::Structure_and_function_of_proteins...`` instead of the opaque ``MCAT::1A``.


def _content_categories() -> List[tuple]:
    graph = load_outline_graph()
    return [
        (n.id.split(":")[-1], n.title) for n in graph.nodes(NodeKind.CONTENT_CATEGORY)
    ]


def _known_codes() -> set:
    return {code for code, _title in _content_categories()}


def title_for_code(code: str) -> Optional[str]:
    for c, title in _content_categories():
        if c == code:
            return title
    return None


#: Cap the title segment so tags stay readable in the sidebar/autocomplete; the code
#: segment is the unique key, so a shortened human label is fine.
_MAX_TITLE_TAG_LEN = 48


def _tag_safe_title(title: str) -> str:
    """A title turned into one tag segment: punctuation and tag-search metacharacters
    dropped, spaces -> underscores (spaces would split the tag), capped at a word
    boundary."""
    s = re.sub(r"[\"'*:,()&/]", "", title or "")
    s = re.sub(r"\s+", "_", s.strip())
    s = re.sub(r"_+", "_", s).strip("_")
    if len(s) > _MAX_TITLE_TAG_LEN:
        s = s[:_MAX_TITLE_TAG_LEN].rsplit("_", 1)[0]  # cut on a word boundary
    return s


def topic_tag(code: str, title: Optional[str] = None) -> str:
    """The readable MCAT tag for a content-category code: ``MCAT::<code>::<Title>`` (or
    just ``MCAT::<code>`` when no title is known). The code stays its own segment so
    coverage still maps it."""
    if title is None:
        title = title_for_code(code) or ""
    tag = f"{TAG_PREFIX}::{code}"
    safe = _tag_safe_title(title)
    return f"{tag}::{safe}" if safe else tag


def upgrade_topic_tag(tag: str) -> str:
    """Upgrade a bare ``MCAT::<code>`` tag to the readable form; leave anything else
    (already-titled tags, non-topic tags, unknown codes) untouched."""
    parts = tag.split("::")
    if len(parts) == 2 and parts[0] == TAG_PREFIX and parts[1] in _known_codes():
        return topic_tag(parts[1])
    return tag
