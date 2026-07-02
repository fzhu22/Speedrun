"""The Speedrun Pretest note type (brainlift v3-focused SPOV 13: pretest-first).

First exposure to new material runs as a forced "commit a guess -> reveal -> mandatory
in-session feedback" card. This is built as a *real Anki note type* with a custom type-in
that matches **leniently** (case-, punctuation-, accent-, and near-miss-tolerant) instead
of Anki's strict native diff, so the whole experience lives in the card template (the
cross-platform "review" tier) and renders on desktop and any stock review client - no
desktop-only modal layered over the reviewer.

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
from anki.speedrun.disconfirmer import topic_tag

NOTETYPE_NAME = "Speedrun Pretest"
NOTE_TAG = "speedrun_pretest"
#: Collection-config flag (default on). When off, first-exposure content is seeded as
#: plain Basic cards - the "feature-off" arm of the spec section-8 ablation.
PRETEST_ENABLED_KEY = "speedrun_pretest_enabled"

#: Field order. ``Answer`` is the type-in target; ``Explanation`` is the mandatory
#: corrective feedback shown on reveal.
FIELDS: List[str] = ["Question", "Answer", "Explanation", "Source", "ConceptFamily"]

# A custom type-in with LENIENT matching (Anki's native {{type:Answer}} flags every
# case/spacing/punctuation difference). The front captures the typed guess; the back
# normalises both sides (lowercase, strip punctuation/accents/articles, collapse
# whitespace) and accepts an exact match OR a near-match (small edit distance), so
# capitals and common deviations are not flagged. The grade the student presses is still
# the recorded outcome; the verdict is guidance.
_FRONT = """\
<div class="sr-card">
  <div class="sr-q">{{Question}}</div>
  <div class="sr-prompt">Type your best guess, then reveal.</div>
  <input id="sr-type" class="sr-input" autocomplete="off" autocapitalize="off" autocorrect="off"
         spellcheck="false" oninput="window.srTyped = this.value;"
         onkeydown="if (event.key === 'Enter') { pycmd('ans'); }">
</div>
"""

_BACK = r"""{{FrontSide}}
<hr id="answer">
<div class="sr-card">
  <div class="sr-a"><span class="lbl">Answer</span><span id="sr-answer">{{Answer}}</span></div>
  <div id="sr-verdict" class="sr-verdict"></div>
  {{#Explanation}}<div class="sr-why"><span class="lbl">Why</span>{{Explanation}}</div>{{/Explanation}}
  {{#Source}}<div class="sr-prov">Source: {{Source}}</div>{{/Source}}
</div>
<script>
(function () {
  function norm(s) {
    return (s || "").toString().toLowerCase()
      .replace(/<[^>]*>/g, " ")
      .replace(/&nbsp;/g, " ")
      .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9%\s]/g, " ")
      .replace(/\b(a|an|the)\b/g, " ")
      .replace(/\s+/g, " ").trim();
  }
  function lev(a, b) {
    var m = a.length, n = b.length, i, j;
    if (!m) return n; if (!n) return m;
    var prev = [], cur = [];
    for (j = 0; j <= n; j++) prev[j] = j;
    for (i = 1; i <= m; i++) {
      cur[0] = i;
      for (j = 1; j <= n; j++) {
        var c = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1;
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + c);
      }
      for (j = 0; j <= n; j++) prev[j] = cur[j];
    }
    return prev[n];
  }
  var typed = window.srTyped || "";
  var ansEl = document.getElementById("sr-answer");
  var answer = ansEl ? ansEl.textContent : "";
  var inp = document.getElementById("sr-type");
  if (inp) { inp.value = typed; inp.readOnly = true; }
  var el = document.getElementById("sr-verdict");
  if (!el) return;
  var nt = norm(typed), na = norm(answer);
  if (!nt) { el.textContent = "No answer typed - grade honestly."; el.className = "sr-verdict"; return; }
  var ok = nt === na;
  var close = !ok && na.length > 0 && lev(nt, na) <= Math.max(1, Math.floor(na.length / 6));
  if (ok) {
    el.textContent = "You typed '" + typed + "' - correct. Press Good.";
    el.className = "sr-verdict ok";
  } else if (close) {
    el.textContent = "You typed '" + typed + "' - close enough (counts as correct). Press Good.";
    el.className = "sr-verdict ok";
  } else {
    el.textContent = "You typed '" + typed + "' - not a match. Press Again.";
    el.className = "sr-verdict no";
  }
})();
</script>
"""

_CSS = """\
.card { font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, Arial; color: inherit; }
.sr-card { max-width: 620px; margin: 0 auto; text-align: left; }
.sr-q { font-size: 17px; font-weight: 600; margin-bottom: 8px; }
.sr-prompt { font-style: italic; opacity: .75; font-size: .9em; margin-bottom: 8px; }
.sr-input { font: inherit; padding: 6px 10px; min-width: 240px; color: inherit;
  border: 1px solid rgba(127,127,127,.5); border-radius: 8px; background: rgba(127,127,127,.06); }
.sr-a { font-size: 16px; margin: 6px 0; }
.sr-verdict { margin: 6px 0; font-weight: 600; }
.sr-verdict.ok { color: #2ea37a; }
.sr-verdict.no { color: #d9534f; }
.sr-why { background: rgba(84,160,255,.15); border-left: 3px solid #54a0ff; padding: 6px 9px; border-radius: 6px; margin: 8px 0; }
.sr-prov { opacity: .6; font-size: 12px; margin-top: 8px; }
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
        tags.append(topic_tag(family))
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
