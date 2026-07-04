# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun on the home screen (deck browser).

Surfaces the core features - the readiness dashboard, the miss->card disconfirmer flow,
and sample-deck seeding - as a compact panel below the deck list, one click away instead
of buried in the Tools menu. Before any Speedrun content exists it shows a short first-run
hint that points at "Load sample deck".

Injected via ``deck_browser_will_render_content``; the button clicks (namespaced
``speedrun:*`` pycmd messages) are handled via ``webview_did_receive_js_message``.
"""

from __future__ import annotations

from typing import Any, Tuple

import aqt
import aqt.main
from aqt.utils import tooltip

_STYLE = """\
<style>
/* A centered row of equal-size pill buttons (matching Anki's bottom-bar buttons), with an
   optional first-run hint above. Buttons share one fixed width/height, center, and wrap
   (never overflow) if the window is too narrow. */
.speedrun-home {
  box-sizing: border-box; width: min(660px, 96%); margin: 0.4em auto 0.2em;
  padding: 9px 12px; text-align: center;
  border: 1px solid var(--border-subtle); border-radius: var(--border-radius-medium, 12px);
  background: var(--canvas-glass, var(--canvas-elevated));
}
.speedrun-home .sr-hint { font-size: .85em; color: var(--fg-subtle); margin: 0 0 8px; }
.speedrun-home .sr-row { display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 10px; }
.speedrun-home .sr-btn {
  -webkit-appearance: none; cursor: pointer; font: inherit; font-size: .95em;
  box-sizing: border-box; flex: 0 0 auto; width: 150px; text-align: center;
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
"""

_DISC_TIP = "A disconfirmer is the one fact that, if true, would flip the answer."


def _btn(cls: str, cmd: str, tip: str, label: str) -> str:
    return (
        f'<button class="{cls}" title="{tip}" '
        f"onclick=\"pycmd('speedrun:{cmd}'); return false;\">{label}</button>"
    )


def _panel(first_run: bool) -> str:
    """Build the home panel. On first run (no Speedrun content yet) it shows a hint and
    makes "Load sample deck" the primary call to action; afterwards "Dashboard" is."""
    hint = (
        '<div class="sr-hint">New to Speedrun? Load the sample deck to see coverage, '
        "memory, and your study plan.</div>"
        if first_run
        else ""
    )
    buttons = (
        _btn(
            "sr-btn" if first_run else "sr-btn primary",
            "dashboard",
            "Open the readiness dashboard",
            "Dashboard",
        )
        + _btn("sr-btn", "add", _DISC_TIP, "Add disconfirmer")
        + _btn(
            "sr-btn primary" if first_run else "sr-btn",
            "seed",
            "Load the sample MCAT, disconfirmer, pretest, and Qbank decks",
            "Load sample deck",
        )
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
        if cmd == "dashboard":
            aqt.dialogs.open("SpeedrunDashboard", mw)
        elif cmd == "add":
            aqt.dialogs.open("SpeedrunAuthoring", mw)
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
