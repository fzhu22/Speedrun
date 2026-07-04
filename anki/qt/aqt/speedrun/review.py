# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""In-review disconfirmer: when a card is missed (Again/Hard), require the student to
write a disconfirmer for that exact card before moving on (the miss -> card loop, made
part of studying rather than an optional side tool).
"""

from __future__ import annotations

import html

import aqt
import aqt.main
from anki.cards import Card
from anki.speedrun import ai, anticrutch
from anki.speedrun.cardtype import STRUGGLE_THRESHOLD
from anki.utils import strip_html
from aqt.qt import *
from aqt.utils import askUser, disable_help_button, showWarning, tooltip

from . import state

CONFIG_KEY = "speedrun_review"
# On by default: the in-review disconfirmer is part of the study loop (it fires during
# review on a miss), not a separate Tools action. Can be turned off in config.
_DEFAULTS = {
    "enabled": True,
    "trigger": "again_hard",
    "scope": "mcat",
    "struggle_after": STRUGGLE_THRESHOLD,
}

#: Per-card count of "Again" presses in this app session (resets on a clear pass or once
#: we prompt). Combined with the card's persistent lapses to gauge how stuck the student
#: is. In-memory by design: "struggling in this session" is the signal we care about.
_again_streak: dict[int, int] = {}


def get_review_config(col) -> dict:
    stored = col.get_config(CONFIG_KEY, default=None) or {}
    return {**_DEFAULTS, **stored}


def disconfirmer_enabled(col) -> bool:
    """Whether the in-review disconfirmer prompt fires (default True). Off = ablation arm."""
    return bool(get_review_config(col).get("enabled", False))


def set_disconfirmer_enabled(col, enabled: bool) -> None:
    stored = col.get_config(CONFIG_KEY, default=None) or {}
    stored["enabled"] = bool(enabled)
    col.set_config(CONFIG_KEY, stored)


def _question(note) -> str:
    return strip_html(note.fields[0]) if note.fields else ""


def _answer(note) -> str:
    return strip_html(note.fields[1]) if len(note.fields) > 1 else ""


def maybe_prompt(mw: aqt.main.AnkiQt, card: Card, ease: int) -> None:
    """If this was a miss on an eligible card, require a disconfirmer for it.

    All gating (the ablation toggle, trigger, MCAT scope, note-type and
    already-disconfirmed skips, and the card-type/struggle heuristic) lives in the
    shared Rust engine's ``speedrun_should_prompt_disconfirmer``, so desktop and
    AnkiDroid decide identically. Here we only track the in-session Again-streak (a
    UI-local signal) and show the modal when the engine says to.
    """
    col = mw.col
    if col is None:
        return

    # Track the in-session miss streak (fed to the engine as session_misses; it
    # adds the card's persistent lapses). Updated on every answer, before gating.
    cid = card.id
    if ease == 1:  # Again = failed to recall
        _again_streak[cid] = _again_streak.get(cid, 0) + 1
    elif ease >= 3:  # Good/Easy = recalled it -> no longer struggling
        _again_streak.pop(cid, None)
    # Hard (ease 2) leaves the streak unchanged: a soft miss, not a clean recall.

    session_misses = _again_streak.get(cid, 0)
    decision = col.speedrun_should_prompt_disconfirmer(
        card_id=card.id, rating=ease, session_misses=session_misses
    )
    if not decision.should_prompt:
        return

    struggling = decision.struggling
    _again_streak.pop(cid, None)  # don't immediately re-prompt the same card

    # Defer so the reviewer finishes transitioning before the modal appears.
    QTimer.singleShot(50, lambda: _show(mw, card, struggling))


def _show(mw: aqt.main.AnkiQt, card: Card, struggling: bool = False) -> None:
    MissDisconfirmerPrompt(mw, card, struggling).exec()


class MissDisconfirmerPrompt(QDialog):
    """A focused, required prompt to capture a disconfirmer for a missed card."""

    def __init__(self, mw: aqt.main.AnkiQt, card: Card, struggling: bool = False) -> None:
        QDialog.__init__(self, mw)
        self.mw = mw
        self.col = mw.col
        self.card = card
        self.setWindowTitle("What one fact would flip this answer?")
        self.setModal(True)
        disable_help_button(self)
        self.setMinimumWidth(520)

        note = card.note()
        self._question = _question(note)
        self._answer = _answer(note)
        self._assisted = False

        layout = QVBoxLayout(self)
        if struggling:
            intro_text = (
                "This one keeps coming back. Study the card below, then name the one fact "
                "that would flip the answer."
            )
        else:
            intro_text = (
                "You found this hard - study the card below, then name the one fact that "
                "would flip the answer."
            )
        intro = QLabel(intro_text)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        card_label = QLabel(
            f"<b>Q:</b> {html.escape(self._question)}<br><b>A:</b> {html.escape(self._answer)}"
        )
        card_label.setWordWrap(True)
        card_label.setTextFormat(Qt.TextFormat.RichText)
        card_label.setStyleSheet(
            "QLabel { background: rgba(127,127,127,.12); border-radius: 8px; padding: 10px; }"
        )
        layout.addWidget(card_label)

        layout.addWidget(QLabel("The one fact that would flip it:"))
        self.disc = QPlainTextEdit()
        self.disc.setFixedHeight(72)
        self.disc.setPlaceholderText("e.g. 'If X were true instead, the answer would become Y'")
        layout.addWidget(self.disc)

        if anticrutch.should_offer_ai_hints(state.load_crutch(self.col)):
            self.hint_btn = QPushButton("Get a hint")
            qconnect(self.hint_btn.clicked, self._on_hint)
            layout.addWidget(self.hint_btn)
            self.hint_label = QLabel()
            self.hint_label.setWordWrap(True)
            self.hint_label.setStyleSheet("QLabel { font-style: italic; opacity: .85; }")
            layout.addWidget(self.hint_label)

        layout.addWidget(QLabel("Key idea (optional): in your own words"))
        self.principle = QLineEdit()
        layout.addWidget(self.principle)

        buttons = QDialogButtonBox()
        save = buttons.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)
        skip = buttons.addButton("Skip", QDialogButtonBox.ButtonRole.RejectRole)
        qconnect(save.clicked, self._on_save)
        qconnect(skip.clicked, self.reject)
        layout.addWidget(buttons)

    def _on_hint(self) -> None:
        client = ai.resolve_client(self.col)
        hint, prov = ai.disconfirmer_hint(client, self._question, self._answer)
        label = "AI hint" if prov.source.startswith("AI") else "Hint"
        self.hint_label.setText(f"{label}: {hint}")
        self._assisted = True

    def _on_save(self) -> None:
        disconfirmer = self.disc.toPlainText().strip()
        if not disconfirmer:
            tooltip("Write your answer, or click Skip.", parent=self)
            return
        problem = self.col.speedrun_validate_disconfirmer(
            text=disconfirmer, answer=self._answer
        )
        if problem and not askUser(f"{problem}\n\nSave anyway?", parent=self, defaultno=True):
            return
        try:
            self.col.speedrun_create_disconfirmer(
                card_id=self.card.id,
                disconfirmer=disconfirmer,
                principle=self.principle.text().strip(),
                assisted=self._assisted,
            )
        except Exception as exc:
            showWarning(f"Sorry, couldn't save that card: {exc}", parent=self)
            return
        tooltip("Saved.", parent=self.mw)
        self.accept()
