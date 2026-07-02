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

__all__ = [
    "setup_speedrun_menu",
    "SpeedrunDashboard",
    "DisconfirmerDialog",
    "SpeedrunDevPortal",
]

_initialized = False


def setup_speedrun_menu(mw: aqt.main.AnkiQt) -> None:
    """Add the Speedrun actions to the Tools menu and register hooks/dialogs once."""
    _init_once()
    dashboard_action = QAction("Speedrun Dashboard", mw)
    qconnect(dashboard_action.triggered, lambda: aqt.dialogs.open("SpeedrunDashboard", mw))
    mw.form.menuTools.addAction(dashboard_action)

    add_action = QAction("Add Disconfirmer Card...", mw)
    qconnect(add_action.triggered, lambda: aqt.dialogs.open("SpeedrunAuthoring", mw))
    mw.form.menuTools.addAction(add_action)

    from . import ai_ui

    classify_action = QAction("Classify Card Types (AI)", mw)
    qconnect(classify_action.triggered, lambda: ai_ui.classify_card_types(mw))
    mw.form.menuTools.addAction(classify_action)

    eval_action = QAction("Run AI Eval", mw)
    qconnect(eval_action.triggered, lambda: ai_ui.run_ai_eval(mw))
    mw.form.menuTools.addAction(eval_action)

    settings_action = QAction("Speedrun AI Settings...", mw)
    qconnect(settings_action.triggered, lambda: ai_ui.show_ai_settings(mw))
    mw.form.menuTools.addAction(settings_action)

    from . import feature_settings

    features_action = QAction("Speedrun Study Features...", mw)
    qconnect(
        features_action.triggered, lambda: feature_settings.show_speedrun_features(mw)
    )
    mw.form.menuTools.addAction(features_action)

    portal_action = QAction("Speedrun Dev Portal", mw)
    qconnect(portal_action.triggered, lambda: aqt.dialogs.open("SpeedrunDevPortal", mw))
    mw.form.menuTools.addAction(portal_action)


def _init_once() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True
    aqt.dialogs.register_dialog("SpeedrunDashboard", SpeedrunDashboard)
    aqt.dialogs.register_dialog("SpeedrunAuthoring", DisconfirmerDialog)
    aqt.dialogs.register_dialog("SpeedrunDevPortal", SpeedrunDevPortal)
    gui_hooks.profile_did_open.append(_ensure_notetype)
    gui_hooks.reviewer_did_answer_card.append(_on_answer_card)

    # Card-type classification runs in the study loop (background, on deck open) so the
    # in-review disconfirmer gating/hints just work - no manual Tools step. Falls back to
    # the heuristic when AI is off / keyless.
    from . import autoclassify

    gui_hooks.overview_did_refresh.append(autoclassify.on_overview_refresh)


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
