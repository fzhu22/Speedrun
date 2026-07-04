# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""A single "Speedrun" hub dialog that launches every Speedrun tool.

The Tools menu carries one "Speedrun" entry instead of a long list; pressing it opens
this panel of buttons (dashboard, add card, study features, AI tools, ...). Desktop-only,
native Qt - the tools it launches are the same ones that used to live in the menu.
"""

from __future__ import annotations

import os

import aqt
import aqt.main
from aqt.qt import *
from aqt.utils import (
    disable_help_button,
    restoreGeom,
    saveGeom,
    showInfo,
    showWarning,
    tooltip,
)

DIALOG_NAME = "SpeedrunHub"


def _add_shadow(widget) -> None:
    """A soft drop shadow so the hub buttons read as raised, like Anki's buttons."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(8)
    effect.setXOffset(0)
    effect.setYOffset(2)
    effect.setColor(QColor(0, 0, 0, 70))
    widget.setGraphicsEffect(effect)


class SpeedrunHub(QDialog):
    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        self.mw = mw
        self.setWindowTitle("Speedrun")
        disable_help_button(self)
        restoreGeom(self, "speedrunHub", default_size=(380, 460))
        self._build_ui()
        self.show()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        heading = QLabel("Speedrun")
        heading.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(heading)

        sub = QLabel("Open the dashboard, add a disconfirmer, or manage AI and study features.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: gray;")
        layout.addWidget(sub)
        layout.addSpacing(4)

        for entry in self._entries():
            if entry is None:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet("color: rgba(128,128,128,.3);")
                layout.addWidget(line)
                continue
            label, tip, func = entry
            btn = QPushButton(label)
            btn.setMinimumHeight(34)
            btn.setStyleSheet("text-align: left; padding: 6px 10px;")
            if tip:
                btn.setToolTip(tip)
            _add_shadow(btn)
            qconnect(btn.clicked, lambda _=False, f=func: self._run(f))
            layout.addWidget(btn)

        layout.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        qconnect(buttons.rejected, self.reject)
        layout.addWidget(buttons)

    def _entries(self):
        """(label, tooltip, func(mw)) rows; ``None`` is a separator. Mirrors the actions
        that used to be added directly to the Tools menu."""
        entries = [
            (
                "Dashboard",
                "Your memory, performance, and readiness scores",
                lambda mw: aqt.dialogs.open("SpeedrunDashboard", mw),
            ),
            (
                "Compute score evidence",
                "Step 1 & 2: memory calibration on held-back reviews + performance-model validation",
                _compute_evidence,
            ),
            (
                "Add disconfirmer",
                "Add a disconfirmer: the one fact that would flip a card's answer",
                lambda mw: aqt.dialogs.open("SpeedrunAuthoring", mw),
            ),
            None,
            ("AI settings...", "Set up the optional AI helper", _ai_settings),
            (
                "Generate items from source (AI)",
                "Create practice items from your own notes",
                _gen_items,
            ),
            None,
            (
                "Study features...",
                "Advanced: turn individual study features on or off (for testing)",
                _feature_settings,
            ),
        ]
        if os.environ.get("ANKIDEV"):
            entries += [
                None,
                (
                    "Classify card types (AI)",
                    "Dev: classify declarative vs application cards",
                    _classify,
                ),
                (
                    "Dev portal",
                    "Dev: internal Speedrun state and knowledge graph",
                    lambda mw: aqt.dialogs.open("SpeedrunDevPortal", mw),
                ),
            ]
        return entries

    def _run(self, func) -> None:
        try:
            func(self.mw)
        except Exception as exc:  # keep the hub usable if one tool errors
            showWarning(f"Could not open that tool: {exc}", parent=self)

    # -- dialog-manager integration ------------------------------------------

    def reject(self) -> None:
        saveGeom(self, "speedrunHub")
        aqt.dialogs.markClosed(DIALOG_NAME)
        QDialog.reject(self)

    def closeWithCallback(self, callback) -> None:
        self.reject()
        callback()


# -- lazy launchers (match the lazy imports the Tools menu used) ---------------


def _feature_settings(mw) -> None:
    from . import feature_settings

    feature_settings.show_speedrun_features(mw)


def _ai_settings(mw) -> None:
    from . import ai_ui

    ai_ui.show_ai_settings(mw)


def _gen_items(mw) -> None:
    from . import ai_ui

    ai_ui.generate_perf_items(mw)


def _classify(mw) -> None:
    from . import ai_ui

    ai_ui.classify_card_types(mw)


def _compute_evidence(mw) -> None:
    """Compute + cache the score-model evidence in the shared engine, then show it.

    Runs the engine's ``speedrun_fit_performance`` (which validates the performance model
    AND evaluates memory calibration on held-back reviews, caching both), then reads the
    dashboard so the same numbers the UI shows are reported here (spec section 9 Steps 1-2).
    """
    col = mw.col
    if col is None:
        return
    resp = col.speedrun_fit_performance()
    mw.reset()  # refresh any open dashboard

    lines = []
    dash = col.speedrun_dashboard()
    if dash.HasField("evidence") and dash.evidence.HasField("memory_rmse"):
        ev = dash.evidence
        lines += [
            "Step 1 - Memory calibration (held-back reviews):",
            f"  calibration error (RMSE): {ev.memory_rmse:.1%}",
            f"  log-loss: {ev.memory_log_loss:.3f}    reviews: {ev.memory_reviews}",
            "",
        ]
    else:
        lines += ["Step 1 - Memory calibration: not enough review history yet.", ""]

    lines += [
        "Step 2 - Performance model (predict held-out exam questions):",
        f"  out-of-sample AUC: {resp.auc_full:.3f} (full) vs {resp.auc_recall:.3f} (recall-only)",
        f"  gain: {resp.delta:+.3f} (need >= {resp.min_delta:.2f}), responses: {resp.n} (need >= {resp.min_responses})",
        (
            "  VALIDATED - Performance now shows on the dashboard."
            if resp.passed
            else "  Not yet - it must beat recall out-of-sample."
        ),
    ]
    showInfo("\n".join(lines), parent=mw, title="Speedrun: Score-model evidence")
    tooltip("Score evidence updated.", parent=mw)
