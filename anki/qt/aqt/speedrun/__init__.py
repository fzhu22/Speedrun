# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Speedrun desktop integration: the dashboard, the disconfirmer authoring dialog, and
the hooks that keep the note type present and the fading ladder updated.

Wired in from `aqt.main.AnkiQt.setupMenus` via `setup_speedrun_menu`.
"""

from __future__ import annotations

import aqt
import aqt.main
from aqt import gui_hooks
from aqt.qt import *

from .authoring import DisconfirmerDialog
from .dashboard import SpeedrunDashboard
from .dev_portal import SpeedrunDevPortal
from .hub import SpeedrunHub

__all__ = [
    "setup_speedrun_menu",
    "SpeedrunDashboard",
    "DisconfirmerDialog",
    "SpeedrunDevPortal",
    "SpeedrunHub",
]

_initialized = False


def setup_speedrun_menu(mw: aqt.main.AnkiQt) -> None:
    """Add a single "Speedrun" entry to the Tools menu (it opens the hub with buttons for
    every Speedrun tool) and register hooks/dialogs once."""
    _init_once()
    action = QAction("Speedrun", mw)
    qconnect(action.triggered, lambda: aqt.dialogs.open("SpeedrunHub", mw))
    mw.form.menuTools.addAction(action)


def _on_top_toolbar_links(links: list, toolbar) -> None:
    """Add a "Speedrun" link to the top toolbar - same target as Tools > Speedrun.

    Inserted just before Sync (kept as the rightmost item). The toolbar centers the whole
    link group, so the extra link stays centered and the short labels fit comfortably.
    """
    mw = aqt.mw
    if mw is None:
        return
    try:
        link = toolbar.create_link(
            "speedrun",
            "Speedrun",
            lambda: aqt.dialogs.open("SpeedrunHub", mw),
            tip="Speedrun tools: dashboard, disconfirmer, AI",
            id="speedrun",
        )
        links.insert(max(len(links) - 1, 0), link)
    except Exception as exc:  # never break the toolbar
        print("speedrun: toolbar link failed:", exc)


def _init_once() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True
    aqt.dialogs.register_dialog("SpeedrunDashboard", SpeedrunDashboard)
    aqt.dialogs.register_dialog("SpeedrunAuthoring", DisconfirmerDialog)
    aqt.dialogs.register_dialog("SpeedrunDevPortal", SpeedrunDevPortal)
    aqt.dialogs.register_dialog("SpeedrunHub", SpeedrunHub)
    gui_hooks.profile_did_open.append(_ensure_notetype)
    gui_hooks.reviewer_did_answer_card.append(_on_answer_card)
    gui_hooks.top_toolbar_did_init_links.append(_on_top_toolbar_links)

    # Card-type classification runs in the study loop (background, on deck open) so the
    # in-review disconfirmer gating/hints just work - no manual Tools step. Falls back to
    # the heuristic when AI is off / keyless.
    from . import autoclassify

    gui_hooks.overview_did_refresh.append(autoclassify.on_overview_refresh)

    # Surface the flagship features on the home screen (deck browser), not just Tools.
    from . import home

    gui_hooks.deck_browser_will_render_content.append(home.on_render)
    gui_hooks.webview_did_receive_js_message.append(home.on_message)

    # Question-writing guidance + AI hint in the native Add dialog.
    from . import addcards_ui

    gui_hooks.add_cards_did_init.append(addcards_ui.on_add_cards_init)
    gui_hooks.add_cards_did_change_deck.append(addcards_ui.on_deck_changed)
    gui_hooks.addcards_did_change_note_type.append(addcards_ui.on_notetype_changed)
    gui_hooks.editor_did_init_buttons.append(addcards_ui.on_editor_buttons)
    gui_hooks.add_cards_will_add_note.append(addcards_ui.on_will_add_note)


def _ensure_notetype() -> None:
    mw = aqt.mw
    if mw is None or mw.col is None:
        return
    try:
        # Note-type creation now lives in the shared Rust engine (Stage 2), so
        # desktop and AnkiDroid create identical Speedrun note types.
        mw.col.speedrun_ensure_notetypes()
    except Exception as exc:  # never break startup
        print("speedrun: ensure_notetype failed:", exc)

    try:
        _refresh_speedrun_templates(mw.col)
    except Exception as exc:  # never break startup
        print("speedrun: refresh templates failed:", exc)

    try:
        # One-time: make any pre-existing bare MCAT::<code> tags human-readable.
        from anki.speedrun import seeding

        seeding.migrate_topic_tags(mw.col)
    except Exception as exc:  # never break startup
        print("speedrun: tag migration failed:", exc)


# Canonical, fixed + compact Performance Item multiple-choice template. The engine
# (`speedrun_ensure_notetypes`) creates the note type; this refresh brings it up to date on
# profile open (so existing profiles get fixes) via the safe models API. The key fix here:
# the front script only initialises on the QUESTION side (guards on `#answer`) and stores
# the pick in sessionStorage, so revealing the answer no longer wipes the selected option.
_PERF_NOTETYPE = "Speedrun Performance Item"

_PERF_FRONT = """\
<div class="sr-card sr-perf">
  <div class="sr-stem">{{Stem}}</div>
  <div class="sr-opts">
    <button type="button" class="sr-opt" data-opt="A">A. {{OptionA}}</button>
    <button type="button" class="sr-opt" data-opt="B">B. {{OptionB}}</button>
    <button type="button" class="sr-opt" data-opt="C">C. {{OptionC}}</button>
    <button type="button" class="sr-opt" data-opt="D">D. {{OptionD}}</button>
  </div>
  <div class="sr-prompt">Pick an option, then reveal.</div>
</div>
<script>
(function () {
  if (document.getElementById("answer")) return;  // question side only; don't reset on reveal
  try { sessionStorage.setItem("srPerfPick", ""); } catch (e) {}
  window.srPerfPick = "";
  var opts = document.querySelectorAll(".sr-opt");
  for (var i = 0; i < opts.length; i++) {
    opts[i].addEventListener("click", function (ev) {
      var p = ev.currentTarget.getAttribute("data-opt");
      window.srPerfPick = p;
      try { sessionStorage.setItem("srPerfPick", p); } catch (e) {}
      for (var j = 0; j < opts.length; j++) opts[j].classList.remove("sel");
      ev.currentTarget.classList.add("sel");
    });
  }
})();
</script>
"""

_PERF_BACK = """\
{{FrontSide}}
<hr id="answer">
<div class="sr-card sr-perf">
  <div class="sr-a"><span class="lbl">Correct answer</span>{{Correct}}</div>
  {{#Rationale}}<div class="sr-why"><span class="lbl">Why</span>{{Rationale}}</div>{{/Rationale}}
  <div id="sr-verdict" class="sr-verdict"></div>
</div>
<script>
(function () {
  var correct = ("{{Correct}}" || "").trim().charAt(0).toUpperCase();
  var pick = "";
  try { pick = sessionStorage.getItem("srPerfPick") || ""; } catch (e) {}
  if (!pick && window.srPerfPick) pick = window.srPerfPick;
  var el = document.getElementById("sr-verdict");
  if (!el) return;
  var opts = document.querySelectorAll(".sr-opt");
  for (var i = 0; i < opts.length; i++) {
    var o = opts[i].getAttribute("data-opt");
    if (o === pick) opts[i].classList.add("sel");
    if (o === correct) opts[i].classList.add("correct");
  }
  if (!pick) { el.textContent = "No option picked - grade honestly."; el.className = "sr-verdict"; return; }
  var ok = pick === correct;
  el.textContent = ok
    ? ("You picked " + pick + " - correct. Press Good.")
    : ("You picked " + pick + " - incorrect (answer: " + correct + "). Press Again.");
  el.className = "sr-verdict " + (ok ? "ok" : "no");
})();
</script>
"""

_PERF_CSS = """\
.card { font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, Arial; color: inherit; }
.sr-card { max-width: 620px; margin: 0 auto; text-align: left; }
.sr-stem { font-size: 17px; font-weight: 600; margin-bottom: 10px; }
.sr-opts { display: grid; gap: 6px; margin-bottom: 8px; }
.sr-opt { text-align: left; padding: 7px 10px; border: 1px solid rgba(127,127,127,.4); border-radius: 8px; background: rgba(127,127,127,.06); color: inherit; font: inherit; cursor: pointer; }
.sr-opt.sel { border-color: #54a0ff; background: rgba(84,160,255,.15); }
.sr-opt.correct { border-color: #2ea37a; background: rgba(46,163,122,.15); }
.sr-prompt { font-style: italic; opacity: .75; font-size: .9em; }
.sr-a { font-size: 16px; margin: 6px 0; }
.sr-why { background: rgba(84,160,255,.12); border-left: 3px solid #54a0ff; padding: 6px 9px; border-radius: 6px; margin: 8px 0; }
.sr-verdict { margin: 6px 0; font-weight: 600; }
.sr-verdict.ok { color: #2ea37a; }
.sr-verdict.no { color: #d9534f; }
.lbl { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .4px; opacity: .6; }
"""


def _refresh_one(col, name: str, qfmt: str, afmt: str, css: str) -> None:
    nt = col.models.by_name(name)
    if nt is None or not nt["tmpls"]:
        return
    tmpl = nt["tmpls"][0]
    changed = False
    if tmpl.get("qfmt") != qfmt:
        tmpl["qfmt"] = qfmt
        changed = True
    if tmpl.get("afmt") != afmt:
        tmpl["afmt"] = afmt
        changed = True
    if nt.get("css") != css:
        nt["css"] = css
        changed = True
    if changed:
        col.models.update_dict(nt)


def _refresh_speedrun_templates(col) -> None:
    """Bring the Speedrun note-type templates up to date from the Python canonicals.

    Fixes reach existing profiles here (the engine only *creates* note types, it never
    overwrites them): the lenient pretest type-in and the multiple-choice reveal fix. Runs
    once per change (a schema edit), then no-ops.
    """
    from anki.speedrun import disconfirmer, pretest

    _refresh_one(
        col,
        disconfirmer.NOTETYPE_NAME,
        disconfirmer._FRONT,
        disconfirmer._BACK,
        disconfirmer._CSS,
    )
    _refresh_one(col, pretest.NOTETYPE_NAME, pretest._FRONT, pretest._BACK, pretest._CSS)
    _refresh_one(col, _PERF_NOTETYPE, _PERF_FRONT, _PERF_BACK, _PERF_CSS)


def _on_answer_card(reviewer, card, ease) -> None:
    mw = aqt.mw
    if mw is None or mw.col is None:
        return
    try:
        from . import state

        state.record_answer(mw.col, card, ease)
    except Exception as exc:  # never break review
        print("speedrun: fading update failed:", exc)

    try:
        from . import review

        review.maybe_prompt(mw, card, ease)
    except Exception as exc:  # never break review
        print("speedrun: disconfirmer prompt failed:", exc)
