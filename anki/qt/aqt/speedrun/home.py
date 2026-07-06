# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun on the home screen (deck browser).

The Speedrun dashboard is the app's home screen by default (see ``_speedrunState`` in
``aqt/main.py``), so the deck list is only seen when the user taps "Decks" from the
dashboard, or has turned the Speedrun-as-home setting off. Either way this panel is just a
single, unmissable link back to Speedrun - not a second copy of its buttons.

Injected via ``deck_browser_will_render_content``; the link (namespaced ``speedrun:*``
pycmd messages) is handled via ``webview_did_receive_js_message``.
"""

from __future__ import annotations

from typing import Any, Tuple

import aqt
import aqt.main
from aqt.utils import tooltip

_STYLE = """\
<style>
/* One centered pill linking back to Speedrun home - not a second copy of its buttons,
   since the dashboard (with its own onboarding + Study now) is the app's home screen. */
.speedrun-home {
  box-sizing: border-box; width: min(420px, 96%); margin: 0.4em auto 0.2em;
  padding: 9px 12px; text-align: center;
  border: 1px solid var(--border-subtle); border-radius: var(--border-radius-medium, 12px);
  background: var(--canvas-glass, var(--canvas-elevated));
}
.speedrun-home .sr-hint { font-size: .85em; color: var(--fg-subtle); margin: 0 0 8px; }
.speedrun-home .sr-row { display: flex; justify-content: center; align-items: center; }
.speedrun-home .sr-btn {
  -webkit-appearance: none; cursor: pointer; font: inherit; font-weight: 600; font-size: .95em;
  box-sizing: border-box; text-align: center; white-space: nowrap;
  padding: 6px 22px; border-radius: var(--border-radius-large, 15px);
  border: 1px solid var(--button-primary-bg); background: var(--button-primary-bg); color: #fff;
}
.speedrun-home .sr-btn:hover {
  border-color: var(--button-primary-gradient-end);
  background: linear-gradient(180deg, var(--button-primary-gradient-start) 0%, var(--button-primary-gradient-end) 100%);
}
</style>
"""


def _btn(cls: str, cmd: str, tip: str, label: str) -> str:
    return (
        f'<button class="{cls}" title="{tip}" '
        f"onclick=\"pycmd('speedrun:{cmd}'); return false;\">{label}</button>"
    )


def _panel(first_run: bool) -> str:
    """Build the home panel: a single link back to Speedrun (its own dashboard carries the
    onboarding call-to-action, the study plan, and every other action)."""
    hint = (
        '<div class="sr-hint">New to Speedrun? Open it to load the starter deck and see '
        "your coverage, memory, and study plan.</div>"
        if first_run
        else ""
    )
    buttons = _btn(
        "sr-btn",
        "dashboard",
        "Open Speedrun: your scores, study plan, and Study now",
        "Open Speedrun",
    )
    return (
        _STYLE
        + '<div class="speedrun-home">'
        + hint
        + '<div class="sr-row">'
        + buttons
        + "</div></div>"
    )


def _has_speedrun_content(col) -> bool:
    """Whether the collection already has any Speedrun/MCAT cards (drives the first-run
    hint). Bounded, indexed search; on any error assume yes (hide the hint)."""
    try:
        search = (
            'tag:MCAT::* OR note:"Speedrun Disconfirmer" '
            'OR note:"Speedrun Pretest" OR note:"Speedrun Performance Item"'
        )
        return bool(col.find_cards(search))
    except Exception:
        return True


def on_render(deck_browser, content) -> None:
    """Add the Speedrun panel below the deck list (after the stats line)."""
    if aqt.mw is None or aqt.mw.col is None:
        return
    try:
        first_run = not _has_speedrun_content(aqt.mw.col)
        content.stats = content.stats + _panel(first_run)
    except Exception as exc:  # never break the home screen
        print("speedrun: home panel failed:", exc)


def on_message(handled: Tuple[bool, Any], message: str, context: Any) -> Tuple[bool, Any]:
    """Handle the panel's ``speedrun:*`` button clicks."""
    if not message.startswith("speedrun:"):
        return handled
    mw = aqt.mw
    if mw is None or mw.col is None:
        return (True, None)
    cmd = message.split(":", 1)[1]
    try:
        if cmd == "hub":
            aqt.dialogs.open("SpeedrunHub", mw)
        elif cmd == "dashboard":
            mw.moveToState("speedrun")
        elif cmd == "add":
            aqt.dialogs.open("SpeedrunAuthoring", mw)
        elif cmd == "decks":
            # "Decks" affordance on the dashboard: hop to Anki's deck list (one tap away).
            mw.moveToState("deckBrowser")
        elif cmd.startswith("studyTopic:"):
            # The core loop: "Study now" / a plan item -> a focused review of that topic.
            _study_topic(mw, cmd.split(":", 1)[1])
        elif cmd == "seed":
            from anki.speedrun import seeding

            counts = seeding.seed_all(mw.col)
            mw.reset()
            total = sum(counts)
            tooltip(
                f"Loaded sample decks ({total} cards)." if total else "Sample decks already present.",
                parent=mw,
            )
            # The onboarding "Load the starter deck" button lives on the dashboard itself;
            # re-enter the state so it reloads with the newly-seeded scores/plan instead of
            # staying on the stale empty-collection view.
            if mw.state == "speedrun":
                mw.moveToState("speedrun")
    except Exception as exc:  # never break the webview
        print("speedrun: home action failed:", exc)
    return (True, None)


def _study_topic(mw: aqt.main.AnkiQt, code: str) -> None:
    """Build (reusing one deck) a filtered deck of a topic's cards and drop into review.

    Powers the dashboard's "Study now" and clickable plan items so studying is one tap from
    the scores, instead of hunting for the right deck. Reuses a single "Speedrun study"
    filtered deck so we never accumulate one deck per topic.
    """
    from anki.decks import DeckId

    code = "".join(c for c in code if c.isalnum())  # sanitised; used in a tag search
    if not code:
        return
    col = mw.col
    name = "Speedrun study"
    existing = col.decks.by_name(name)
    deck = col.sched.get_or_create_filtered_deck(DeckId(existing["id"] if existing else 0))
    deck.name = name
    deck.config.reschedule = True  # keep the cards' real scheduling; this is just a lens
    del deck.config.search_terms[:]
    term = deck.config.search_terms.add()
    # Match the content-category code as a full tag segment, plus its finer children.
    term.search = f'"tag:*::{code}" OR "tag:*::{code}::*"'
    term.limit = 200
    out = col.sched.add_or_update_filtered_deck(deck)
    col.decks.select(DeckId(out.id))
    col.startTimebox()
    mw.moveToState("review")
