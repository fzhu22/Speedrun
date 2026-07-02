# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Card-authoring help in Anki's native Add dialog.

Two additions, both optional (gated by the ``speedrun_authoring_guide_enabled`` flag):
- a guidance panel with a topic picker (MCAT content categories, or Auto from the
  tags/deck) that shows deterministic question-writing tips, and
- an "AI hint" editor-toolbar button that sends the draft card to the AI lane and shows
  advice on what else to add (falls back to a fixed checklist when AI is off).

Wired via gui_hooks from ``speedrun/__init__``; no core Anki files are edited.
"""

from __future__ import annotations

import weakref
from html import escape
from typing import Optional, Tuple

import aqt
import aqt.main
from anki.speedrun import ai, question_guidance
from anki.speedrun.disconfirmer import topic_tag
from anki.utils import strip_html
from aqt.qt import *
from aqt.utils import showInfo

from . import state

#: Open Add dialogs that carry a guidance panel, so the deck-change hook (which only
#: receives a deck id) can refresh them.
_dialogs: "weakref.WeakSet" = weakref.WeakSet()


class GuidancePanel(QWidget):
    """Topic picker + question-writing tips + AI-hint output, shown atop the Add fields."""

    def __init__(self, addcards) -> None:
        super().__init__()
        self._ac = weakref.ref(addcards)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 6)

        row = QHBoxLayout()
        row.addWidget(QLabel("Topic:"))
        self.combo = QComboBox()
        self.combo.addItem("Auto (from tags/deck)", None)
        for code, title in question_guidance.content_categories():
            self.combo.addItem(f"{code} - {title}", (code, title))
        row.addWidget(self.combo, 1)
        layout.addLayout(row)

        self.guidance = QLabel()
        self.guidance.setWordWrap(True)
        self.guidance.setTextFormat(Qt.TextFormat.RichText)
        self.guidance.setStyleSheet(
            "QLabel { background: rgba(110,168,254,.12);"
            " border: 1px solid rgba(110,168,254,.4); border-radius: 8px; padding: 8px; }"
        )
        layout.addWidget(self.guidance)

        self.advice = QLabel()
        self.advice.setWordWrap(True)
        self.advice.setTextFormat(Qt.TextFormat.RichText)
        self.advice.setStyleSheet("QLabel { font-style: italic; opacity: .9; padding: 2px; }")
        self.advice.setVisible(False)
        layout.addWidget(self.advice)

        qconnect(self.combo.currentIndexChanged, lambda _i: self.refresh())
        self.refresh()

    def selected_topic(self) -> Optional[Tuple[str, str]]:
        """The chosen (code, title), or - when the picker is on Auto - the topic inferred
        from the current note's tags + target deck (None if nothing matches)."""
        data = self.combo.currentData()
        if data:
            return data
        addcards = self._ac()
        if addcards is None:
            return None
        note = getattr(addcards.editor, "note", None)
        tags = list(note.tags) if note else []
        deck = ""
        try:
            deck = addcards.deck_chooser.selected_deck_name()
        except Exception:
            pass
        return question_guidance.infer_topic(tags, deck)

    def refresh(self) -> None:
        topic = self.selected_topic()
        code, title = topic if topic else (None, None)
        lines = question_guidance.guidance_for_topic(code, title)
        bullets = "".join(f"<li>{escape(t)}</li>" for t in lines[1:])
        self.guidance.setText(
            f"<b>{escape(lines[0])}</b>"
            f"<ul style='margin:4px 0 0 0; padding-left:18px;'>{bullets}</ul>"
        )

    def show_advice(self, text: str, source: str) -> None:
        label = "AI hint" if source.startswith("AI") else "Hint"
        self.advice.setText(f"<b>{escape(label)}:</b> {escape(text)}")
        self.advice.setVisible(True)


# -- hooks --------------------------------------------------------------------


def on_add_cards_init(addcards) -> None:
    col = getattr(addcards, "col", None)
    if col is None or not state.authoring_guide_enabled(col):
        return
    try:
        panel = GuidancePanel(addcards)
        addcards.form.verticalLayout_3.insertWidget(1, panel)
        addcards._sr_guide = panel
        _dialogs.add(addcards)
    except Exception as exc:  # never break the Add dialog
        print("speedrun: add-cards guidance init failed:", exc)


def on_deck_changed(_deck_id: int) -> None:
    for addcards in list(_dialogs):
        panel = getattr(addcards, "_sr_guide", None)
        if panel is not None:
            panel.refresh()


def on_notetype_changed(addcards, _old, _new) -> None:
    panel = getattr(addcards, "_sr_guide", None)
    if panel is not None:
        panel.refresh()


def on_will_add_note(problem: Optional[str], note) -> Optional[str]:
    """Tag the note with its chosen topic (``MCAT::<code>::<Title>``) as it's added, so
    the topic picker also drives coverage/mastery - the user doesn't have to hand-type
    the tag. Runs after the editor has saved, matching the dialog by its live note."""
    for addcards in list(_dialogs):
        panel = getattr(addcards, "_sr_guide", None)
        if panel is None or getattr(addcards.editor, "note", None) is not note:
            continue
        topic = panel.selected_topic()
        if topic:
            tag = topic_tag(topic[0], topic[1])
            if tag not in note.tags:
                note.tags.append(tag)
        break
    return problem


def on_editor_buttons(buttons, editor) -> None:
    if not getattr(editor, "addMode", False):
        return
    mw = editor.mw
    if mw is None or mw.col is None or not state.authoring_guide_enabled(mw.col):
        return
    buttons.append(
        editor.addButton(
            icon=None,
            cmd="srCardAdvice",
            func=_on_advice,
            tip="AI hint: what else should go on this card",
            label="AI hint",
            keys="Ctrl+Shift+I",
        )
    )


def _on_advice(editor) -> None:
    """Send the (already-saved) draft to the AI lane and show the advice in the panel."""
    mw = editor.mw
    col = mw.col if mw else None
    note = getattr(editor, "note", None)
    if col is None or note is None:
        return
    question = strip_html(note.fields[0]) if note.fields else ""
    answer = strip_html(note.fields[1]) if len(note.fields) > 1 else ""

    panel = getattr(editor.parentWindow, "_sr_guide", None)
    topic = panel.selected_topic() if panel is not None else None
    topic_label = f"{topic[0]} - {topic[1]}" if topic else ""
    client = ai.resolve_client(col)

    def task():
        # Blank draft -> suggest concepts to make cards about; otherwise critique the draft.
        if not question and not answer:
            return ai.topic_card_ideas(client, topic_label)
        return ai.card_advice(client, question, answer, topic_label)

    def on_done(fut) -> None:
        mw.progress.finish()
        text, prov = fut.result()
        if panel is not None:
            panel.show_advice(text, prov.source)
        else:
            label = "AI hint" if prov.source.startswith("AI") else "Hint"
            showInfo(f"{label}: {text}", parent=mw, title="AI hint")

    mw.progress.start(label="Getting a hint...")
    mw.taskman.run_in_background(task, on_done)
