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
        "Turn each study feature on or off. Changes apply to new reviews and new "
        "cards; existing cards are left as-is."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    pretest_cb = QCheckBox("Guess-first on new cards (a quick attempt before the answer)")
    pretest_cb.setChecked(pretest.pretest_enabled(col))
    layout.addWidget(pretest_cb)

    disc_cb = QCheckBox('After a miss, ask "what would change your mind?"')
    disc_cb.setChecked(review.disconfirmer_enabled(col))
    layout.addWidget(disc_cb)

    fade_cb = QCheckBox("Fade guidance as you improve on a topic")
    fade_cb.setChecked(state.fading_enabled(col))
    layout.addWidget(fade_cb)

    grade_cb = QCheckBox('Set "Again" apart from Hard / Good / Easy when grading')
    grade_cb.setChecked(state.grading_split_enabled(col))
    layout.addWidget(grade_cb)

    guide_cb = QCheckBox("Question-writing guidance + AI hint when adding cards")
    guide_cb.setChecked(state.authoring_guide_enabled(col))
    layout.addWidget(guide_cb)

    note = QLabel(
        "AI hints are controlled separately, under Tools > Speedrun AI Settings."
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
        state.set_grading_split_enabled(col, grade_cb.isChecked())
        state.set_authoring_guide_enabled(col, guide_cb.isChecked())
        tooltip("Speedrun feature settings saved.", parent=mw)
        dialog.accept()

    qconnect(buttons.accepted, on_accept)
    qconnect(buttons.rejected, dialog.reject)
    dialog.exec()
