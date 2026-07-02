# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Speedrun study-feature flags.

A small preferences dialog to turn each added Speedrun study feature on or off, for A/B
ablation testing (spec section 8). Flags are stored in the collection config, so they
sync and are read by the feature code:

- Pretest-first cards       -> ``speedrun_pretest_enabled``   (anki.speedrun.pretest)
- In-review disconfirmer    -> ``speedrun_review.enabled``     (aqt.speedrun.review)
- Per-family support-fading -> ``speedrun_fading_enabled``     (aqt.speedrun.state)
"""

from __future__ import annotations

import aqt
import aqt.main
from anki.speedrun import pretest
from aqt.qt import *
from aqt.utils import disable_help_button, tooltip

from . import review, state


def show_speedrun_features(mw: aqt.main.AnkiQt) -> None:
    """Open the Speedrun study-feature on/off dialog."""
    if mw.col is None:
        return
    col = mw.col

    dialog = QDialog(mw)
    dialog.setWindowTitle("Speedrun Study Features")
    disable_help_button(dialog)
    layout = QVBoxLayout(dialog)

    intro = QLabel(
        "Turn each Speedrun study feature on or off for A/B ablation testing "
        "(spec section 8). Changes apply to new reviews and newly seeded cards; "
        "existing cards are left as-is."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    pretest_cb = QCheckBox("Pretest-first cards (forced guess + feedback on new cards)")
    pretest_cb.setChecked(pretest.pretest_enabled(col))
    layout.addWidget(pretest_cb)

    disc_cb = QCheckBox("In-review disconfirmer prompt (fires on a miss)")
    disc_cb.setChecked(review.disconfirmer_enabled(col))
    layout.addWidget(disc_cb)

    fade_cb = QCheckBox("Per-family support-fading (the L3-L0 rung)")
    fade_cb.setChecked(state.fading_enabled(col))
    layout.addWidget(fade_cb)

    note = QLabel(
        "The AI hint lane is separate, gated by whether an API key is set "
        "(Tools > Speedrun AI Settings) - it is off with no key."
    )
    note.setWordWrap(True)
    note.setStyleSheet("QLabel { opacity: 0.7; font-size: 11px; }")
    layout.addWidget(note)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    layout.addWidget(buttons)

    def on_accept() -> None:
        pretest.set_pretest_enabled(col, pretest_cb.isChecked())
        review.set_disconfirmer_enabled(col, disc_cb.isChecked())
        state.set_fading_enabled(col, fade_cb.isChecked())
        tooltip("Speedrun feature settings saved.", parent=mw)
        dialog.accept()

    qconnect(buttons.accepted, on_accept)
    qconnect(buttons.rejected, dialog.reject)
    dialog.exec()
