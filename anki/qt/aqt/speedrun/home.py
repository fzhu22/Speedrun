# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun on the home screen (deck browser).

Surfaces the flagship features - the readiness dashboard, the miss->card authoring flow,
the study-feature toggles, and sample-deck seeding - as a panel at the top of the deck
list, so they are one click away instead of buried in the Tools menu.

Injected via ``deck_browser_will_render_content``; the button clicks (namespaced
``speedrun:*`` pycmd messages) are handled via ``webview_did_receive_js_message``. The
panel is intentionally query-free so it never slows the home screen; the live numbers
live one click away in the dashboard.
"""

from __future__ import annotations

from typing import Any, Tuple

import aqt
import aqt.main
from aqt.utils import tooltip

_PANEL = """\
<style>
/* A centered row of equal-size pill buttons, matching Anki's bottom-bar buttons. Every
   button is the same fixed width and height; the row centers and wraps (never overflows)
   if the window is too narrow to hold all four. */
.speedrun-home {
  display: flex; justify-content: center; align-items: center; flex-wrap: wrap;
  gap: 10px; box-sizing: border-box;
  width: min(660px, 96%); margin: 0.4em auto 0.2em; padding: 10px 12px;
  border: 1px solid var(--border-subtle); border-radius: var(--border-radius-medium, 12px);
  background: var(--canvas-glass, var(--canvas-elevated));
}
.speedrun-home .sr-btn {
  -webkit-appearance: none; cursor: pointer; font: inherit; font-size: .95em;
  box-sizing: border-box; flex: 0 0 auto; width: 128px; text-align: center;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  padding: 6px 12px; border-radius: var(--border-radius-large, 15px);
  border: 1px solid var(--border-subtle); border-bottom-color: var(--shadow);
  background: var(--button-bg); color: var(--fg);
}
.speedrun-home .sr-btn:hover {
  background: linear-gradient(180deg, var(--button-gradient-start) 0%, var(--button-gradient-end) 100%);
  border: 1px solid var(--shadow);
}
/* Transparent (not removed) border keeps the primary button the same height as the rest. */
.speedrun-home .sr-btn.primary { border: 1px solid var(--button-primary-bg); background: var(--button-primary-bg); color: #fff; }
.speedrun-home .sr-btn.primary:hover {
  border-color: var(--button-primary-gradient-end);
  background: linear-gradient(180deg, var(--button-primary-gradient-start) 0%, var(--button-primary-gradient-end) 100%);
}
</style>
<div class="speedrun-home">
  <button class="sr-btn primary" title="Open the readiness dashboard" onclick="pycmd('speedrun:dashboard'); return false;">Dashboard</button>
  <button class="sr-btn" title="Turn a missed card into a disconfirmer" onclick="pycmd('speedrun:add'); return false;">Disconfirmer</button>
  <button class="sr-btn" title="Toggle study features (ablation)" onclick="pycmd('speedrun:features'); return false;">Features</button>
  <button class="sr-btn" title="Seed the sample MCAT decks" onclick="pycmd('speedrun:seed'); return false;">Sample decks</button>
</div>
"""


def on_render(deck_browser, content) -> None:
    """Add the Speedrun panel below the deck list (after the stats line)."""
    if aqt.mw is None or aqt.mw.col is None:
        return
    try:
        content.stats = content.stats + _PANEL
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
        if cmd == "dashboard":
            aqt.dialogs.open("SpeedrunDashboard", mw)
        elif cmd == "add":
            aqt.dialogs.open("SpeedrunAuthoring", mw)
        elif cmd == "features":
            from . import feature_settings

            feature_settings.show_speedrun_features(mw)
        elif cmd == "seed":
            from anki.speedrun import seeding

            counts = seeding.seed_all(mw.col)
            mw.reset()
            total = sum(counts)
            tooltip(
                f"Loaded sample decks ({total} cards)." if total else "Sample decks already present.",
                parent=mw,
            )
    except Exception as exc:  # never break the webview
        print("speedrun: home action failed:", exc)
    return (True, None)
