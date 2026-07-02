# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The Speedrun dashboard dialog.

Loads the shared SvelteKit ``speedrun`` page - the same page the phone build shows -
which calls the Rust ``speedrun_dashboard`` RPC for coverage, the three scores, and the
prerequisite-aware next-best plan. The desktop side is just the window shell plus the
seed / author / refresh buttons.
"""

from __future__ import annotations

import aqt
import aqt.main
from anki.speedrun import seeding
from aqt.qt import *
from aqt.utils import disable_help_button, restoreGeom, saveGeom, tooltip
from aqt.webview import AnkiWebView, AnkiWebViewKind

DIALOG_NAME = "SpeedrunDashboard"


class SpeedrunDashboard(QDialog):
    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        self.mw = mw
        self.setWindowTitle("Speedrun Dashboard")
        disable_help_button(self)
        restoreGeom(self, "speedrunDashboard", default_size=(900, 720))

        layout = QVBoxLayout(self)
        buttons = QHBoxLayout()
        self.seed_btn = QPushButton("Load sample MCAT deck")
        qconnect(self.seed_btn.clicked, self.on_seed)
        self.add_btn = QPushButton("Add disconfirmer card")
        qconnect(self.add_btn.clicked, lambda: aqt.dialogs.open("SpeedrunAuthoring", self.mw))
        self.refresh_btn = QPushButton("Refresh")
        qconnect(self.refresh_btn.clicked, self.refresh)
        buttons.addWidget(self.seed_btn)
        buttons.addWidget(self.add_btn)
        buttons.addWidget(self.refresh_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        # SPEEDRUN kind grants the page backend API access (for the speedrun_dashboard
        # RPC); without it the request is rejected with 403.
        self.web = AnkiWebView(self, kind=AnkiWebViewKind.SPEEDRUN)
        layout.addWidget(self.web)

        self._ready = False
        self.refresh()
        self.show()
        self._ready = True

    def event(self, evt: QEvent) -> bool:
        # Auto-refresh when the user switches back to the dashboard, so reviews done in
        # the main window are reflected without having to press Refresh.
        if (
            evt is not None
            and evt.type() == QEvent.Type.WindowActivate
            and getattr(self, "_ready", False)
            and self.web is not None
        ):
            self.refresh()
        return super().event(evt)

    def refresh(self) -> None:
        # Speedrun: render the shared SvelteKit dashboard page - the same page the
        # phone loads - which calls the Rust speedrun_dashboard RPC.
        self.web.load_sveltekit_page("speedrun")

    def on_seed(self) -> None:
        sample, disc, pre, perf = seeding.seed_all(self.mw.col)
        tooltip(
            f"Loaded {sample} sample + {disc} disconfirmer + {pre} pretest + {perf} Qbank cards."
            if (sample or disc or pre or perf)
            else "Sample decks already present.",
            parent=self,
        )
        self.mw.reset()
        self.refresh()

    def reject(self) -> None:
        saveGeom(self, "speedrunDashboard")
        self.web = None  # type: ignore[assignment]
        aqt.dialogs.markClosed(DIALOG_NAME)
        QDialog.reject(self)

    def closeWithCallback(self, callback) -> None:
        self.reject()
        callback()
