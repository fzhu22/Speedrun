# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The guided 'Miss -> Card' disconfirmer authoring dialog (PRD Section 6.2).

The student converts a miss into a Speedrun Disconfirmer note: the deep principle, a
surface perturbation (original -> swapped cover-story), the trap, and the required
disconfirmer. Scaffolding shown depends on the concept-family's fading rung; the
disconfirmer is validated before the card is created.
"""

from __future__ import annotations

import aqt
import aqt.main
from anki.speedrun import ai, fading, load_outline_graph
from anki.speedrun.disconfirmer import ASSISTED_TAG, build_note, validate_disconfirmer
from anki.speedrun.models import NodeKind
from aqt.deckchooser import DeckChooser
from aqt.qt import *
from aqt.utils import (
    askUser,
    disable_help_button,
    restoreGeom,
    saveGeom,
    showInfo,
    tooltip,
)

from . import state

DIALOG_NAME = "SpeedrunAuthoring"


class DisconfirmerDialog(QDialog):
    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        self.mw = mw
        self.col = mw.col
        self._assisted = False
        self.setWindowTitle("Add disconfirmer")
        disable_help_button(self)
        restoreGeom(self, "speedrunAuthoringV2", default_size=(560, 470))
        self._build_ui()
        self._on_family_changed()
        self.show()

    # -- ui -------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Plain-English explainer for the term (shown on first use, per UX review).
        explainer = QLabel(
            "A disconfirmer is the one fact that, if true, would flip this card's answer."
        )
        explainer.setWordWrap(True)
        explainer.setStyleSheet("QLabel { font-style: italic; opacity: .8; }")
        layout.addWidget(explainer)

        # Deck + concept family
        top = QFormLayout()
        self.deck_widget = QWidget()
        self.deck_chooser = DeckChooser(self.mw, self.deck_widget)
        top.addRow("Deck:", self.deck_widget)

        self.family = QComboBox()
        for code, title in self._content_categories():
            self.family.addItem(f"{code} - {title}", code)
        qconnect(self.family.currentIndexChanged, lambda _i: self._on_family_changed())
        top.addRow("Topic:", self.family)
        layout.addLayout(top)

        # One-line fading guidance for the selected family (details in tooltips).
        self.guidance = QLabel()
        self.guidance.setWordWrap(True)
        self.guidance.setTextFormat(Qt.TextFormat.RichText)
        self.guidance.setStyleSheet(
            "QLabel { background: rgba(110,168,254,.12);"
            " border: 1px solid rgba(110,168,254,.4); border-radius: 8px; padding: 8px; }"
        )
        layout.addWidget(self.guidance)

        # Core fields: the reworded question, its answer, and the disconfirmer.
        form = QFormLayout()
        self.swapped = QPlainTextEdit()
        self.swapped.setPlaceholderText("A reworded, exam-style version of the question")
        self.swapped.setFixedHeight(56)
        form.addRow("Question:", self.swapped)

        self.answer = QLineEdit()
        form.addRow("Answer:", self.answer)

        self.disconfirmer = QPlainTextEdit()
        self.disconfirmer.setPlaceholderText("What ONE fact, if true, would flip the answer?")
        self.disconfirmer.setFixedHeight(56)
        form.addRow("One fact that flips it*:", self.disconfirmer)

        self.hint_btn = QPushButton("Get a hint")
        self.hint_btn.setFlat(True)
        qconnect(self.hint_btn.clicked, self._on_hint)
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("QLabel { font-style: italic; opacity: .85; }")
        form.addRow(self.hint_btn, self.hint_label)
        layout.addLayout(form)

        # Optional details - collapsed by default so the dialog stays short.
        self.more_btn = QToolButton()
        self.more_btn.setText("More options")
        self.more_btn.setCheckable(True)
        self.more_btn.setArrowType(Qt.ArrowType.RightArrow)
        self.more_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.more_btn.setStyleSheet("QToolButton { border: none; padding: 2px; }")
        qconnect(self.more_btn.toggled, self._on_toggle_more)
        layout.addWidget(self.more_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.more = QWidget()
        more_form = QFormLayout(self.more)
        more_form.setContentsMargins(0, 0, 0, 0)
        self.principle = QLineEdit()
        self.principle.setPlaceholderText("The key idea in your own words")
        more_form.addRow("Key idea:", self.principle)
        self.trap = QLineEdit()
        self.trap.setPlaceholderText("The common mistake this catches")
        more_form.addRow("Common trap:", self.trap)
        self.boundary = QLineEdit()
        self.boundary.setPlaceholderText("An edge case where the idea breaks")
        more_form.addRow("Edge case:", self.boundary)
        self.provenance = QLineEdit()
        self.provenance.setPlaceholderText("Your own reference (don't paste copyrighted questions)")
        more_form.addRow("Source:", self.provenance)
        self.more.setVisible(False)
        layout.addWidget(self.more)

        self.transfer = QCheckBox("Practice-test item (held out from study)")
        layout.addWidget(self.transfer)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        add_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if add_btn is not None:
            add_btn.setText("Add card")
        qconnect(buttons.accepted, self._on_accept)
        qconnect(buttons.rejected, self.reject)
        layout.addWidget(buttons)

    def _on_toggle_more(self, checked: bool) -> None:
        self.more.setVisible(checked)
        self.more_btn.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
        if not checked:  # shrink back to fit when collapsing
            self.adjustSize()

    def _content_categories(self):
        graph = load_outline_graph()
        cats = [
            (n.id.split(":")[-1], n.title)
            for n in graph.nodes(NodeKind.CONTENT_CATEGORY)
        ]
        cats.sort(key=lambda c: (len(c[0]), c[0]))  # 1A, 1B, ... 10A
        return cats

    def _on_family_changed(self) -> None:
        family = self.family.currentData()
        if not family:
            self.guidance.setText("")
            return
        rung = state.rung_for_family(self.col, family)
        info = fading.RUNG_GUIDANCE[rung]
        self.guidance.setText(f"<b>{info['label']}</b> &mdash; {info['summary']}")
        # Keep the panel to one line: the perturbation checklist and worked example
        # live as hover tooltips on the Question box instead of always-on text.
        tip_parts = []
        if info.get("show_exemplar"):
            tip_parts.append("Example - " + fading.EXEMPLAR)
        if info.get("show_checklist"):
            tip_parts.append(
                "Change at least one thing from the original: "
                + ", ".join(fading.PERTURBATION_CHECKLIST)
            )
        self.swapped.setToolTip("\n\n".join(tip_parts))

    # -- actions --------------------------------------------------------------

    def _on_hint(self) -> None:
        client = ai.resolve_client(self.col)
        hint, prov = ai.disconfirmer_hint(
            client, self.swapped.toPlainText().strip(), self.answer.text().strip()
        )
        label = "AI hint" if prov.source.startswith("AI") else "Hint"
        self.hint_label.setText(f"{label}: {hint}")
        self._assisted = True

    def _on_accept(self) -> None:
        question = self.swapped.toPlainText().strip()
        answer = self.answer.text().strip()
        disc = self.disconfirmer.toPlainText().strip()
        if not question or not answer:
            showInfo("Please fill in at least the question and the answer.", parent=self)
            return

        problem = validate_disconfirmer(disc, answer)
        if problem and not askUser(
            f"{problem}\n\nAdd the card anyway?", parent=self, defaultno=True
        ):
            return

        fields = {
            "SwappedCoverStory": question,
            "Answer": answer,
            "Principle": self.principle.text().strip(),
            "Trap": self.trap.text().strip(),
            "Disconfirmer": disc,
            "BoundaryCase": self.boundary.text().strip(),
            "Provenance": self.provenance.text().strip(),
        }
        new_id = build_note(
            self.col,
            fields=fields,
            family=self.family.currentData(),
            deck_id=self.deck_chooser.selected_deck_id,
            transfer_item=self.transfer.isChecked(),
        )
        if self._assisted:
            note = self.col.get_note(new_id)
            note.tags.append(ASSISTED_TAG)
            self.col.update_note(note)
            self._assisted = False
        self.mw.reset()
        tooltip("Card added.", parent=self.mw)
        self.hint_label.setText("")
        self._clear_fields()

    def _clear_fields(self) -> None:
        self.swapped.setPlainText("")
        self.disconfirmer.setPlainText("")
        for w in (self.answer, self.principle, self.trap, self.boundary, self.provenance):
            w.setText("")
        self.transfer.setChecked(False)
        self.swapped.setFocus()

    # -- dialog-manager integration ------------------------------------------

    def reject(self) -> None:
        saveGeom(self, "speedrunAuthoringV2")
        self.deck_chooser.cleanup()
        aqt.dialogs.markClosed(DIALOG_NAME)
        QDialog.reject(self)

    def closeWithCallback(self, callback) -> None:
        self.reject()
        callback()
