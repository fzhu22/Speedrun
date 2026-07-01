# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Speedrun AI Tools: settings, batch card-type classification, and the AI eval gate.

Network work runs off the main thread; collection writes happen back on the main thread.
"""

from __future__ import annotations

import os

import aqt
import aqt.main
from anki.speedrun import ai, ai_eval, cardcache
from anki.speedrun.cardtype import heuristic_classify
from anki.speedrun.disconfirmer import NOTETYPE_NAME, TAG_PREFIX
from anki.utils import strip_html
from aqt.qt import *
from aqt.utils import showInfo, tooltip


KEY_FILENAME = "speedrun_ai_key"  # stored in the profile folder; NOT synced


def _key_path(mw: aqt.main.AnkiQt) -> str:
    return os.path.join(mw.pm.profileFolder(), KEY_FILENAME)


def load_profile_key(mw: aqt.main.AnkiQt) -> None:
    """On startup, load a locally-stored key into the session (if env isn't set)."""
    if ai.api_key():
        return
    try:
        path = _key_path(mw)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                ai.set_runtime_key(fh.read().strip())
    except Exception as exc:
        print("speedrun ai: could not load key file:", exc)


def save_profile_key(mw: aqt.main.AnkiQt, key: str) -> None:
    with open(_key_path(mw), "w", encoding="utf-8") as fh:
        fh.write(key.strip())
    ai.set_runtime_key(key)


def show_ai_settings(mw: aqt.main.AnkiQt) -> None:
    cfg = ai.get_config(mw.col)
    dlg = QDialog(mw)
    dlg.setWindowTitle("Speedrun AI settings")
    form = QFormLayout(dlg)

    enabled = QCheckBox("Enable AI features (classification + hints)")
    enabled.setChecked(bool(cfg["enabled"]))
    model = QLineEdit(cfg["model"])
    base = QLineEdit(cfg["base_url"])

    key_edit = QLineEdit()
    key_edit.setEchoMode(QLineEdit.EchoMode.Password)
    key_edit.setPlaceholderText(
        "key already set - leave blank to keep" if ai.api_key() else "paste API key (stored locally, never synced)"
    )
    load_btn = QPushButton("Load from file...")

    def on_load() -> None:
        path, _ = QFileDialog.getOpenFileName(dlg, "Choose an API key file")
        if path:
            try:
                with open(path, encoding="utf-8") as fh:
                    key_edit.setText(fh.read().strip())
            except Exception as exc:
                showInfo(f"Could not read file: {exc}", parent=dlg)

    qconnect(load_btn.clicked, on_load)
    key_row = QHBoxLayout()
    key_row.addWidget(key_edit)
    key_row.addWidget(load_btn)
    key_widget = QWidget()
    key_widget.setLayout(key_row)

    form.addRow(enabled)
    form.addRow("Model:", model)
    form.addRow("Base URL:", base)
    form.addRow("API key:", key_widget)
    form.addRow(
        QLabel(
            f"Status: {'key set' if ai.api_key() else 'no key'} "
            f"(env {ai.KEY_ENV_VAR} or a local profile file)."
        )
    )

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    form.addRow(buttons)
    qconnect(buttons.accepted, dlg.accept)
    qconnect(buttons.rejected, dlg.reject)
    if dlg.exec():
        ai.set_config(
            mw.col,
            enabled=enabled.isChecked(),
            model=model.text().strip() or None,
            base_url=base.text().strip() or None,
        )
        if key_edit.text().strip():
            save_profile_key(mw, key_edit.text())
        tooltip("Saved Speedrun AI settings.", parent=mw)


def classify_card_types(mw: aqt.main.AnkiQt) -> None:
    """Classify MCAT cards' type (AI if enabled, else heuristic) and cache as a tag."""
    col = mw.col
    client = ai.resolve_client(col)
    search = f'tag:{TAG_PREFIX}::* -tag:{cardcache.CTYPE_TAG_PREFIX}::* -note:"{NOTETYPE_NAME}"'
    items = []
    for nid in col.find_notes(search):
        note = col.get_note(nid)
        q = strip_html(note.fields[0]) if note.fields else ""
        a = strip_html(note.fields[1]) if len(note.fields) > 1 else ""
        items.append((nid, q, a))

    if not items:
        tooltip("No new cards to classify.", parent=mw)
        return

    def task():
        # Network/classification only - no collection writes here.
        return [(nid, ai.classify_card_type(client, q, a)) for nid, q, a in items]

    def on_done(fut) -> None:
        mw.progress.finish()
        results = fut.result()
        for nid, card_type in results:
            cardcache.set_cached_card_type(col, col.get_note(nid), card_type)
        mw.reset()
        how = "AI" if client is not None else "heuristic"
        tooltip(f"Classified {len(results)} cards ({how}).", parent=mw)

    mw.progress.start(label="Classifying card types...")
    mw.taskman.run_in_background(task, on_done)


def run_ai_eval(mw: aqt.main.AnkiQt) -> None:
    """Evaluate the AI classifier vs the heuristic baseline on the held-out gold set."""
    col = mw.col
    client = ai.resolve_client(col)
    available = ai.ai_available(col)

    def task():
        scores = ai_eval.compare(
            lambda q, a: ai.classify_card_type(client, q, a), heuristic_classify
        )
        leak = ai_eval.fewshot_leakage(ai.FEWSHOT_EXAMPLES)
        return scores, leak

    def on_done(fut) -> None:
        mw.progress.finish()
        scores, leak = fut.result()
        ai_acc, base_acc = scores["ai"], scores["heuristic"]
        lines = [
            f"AI enabled: {available}",
            "",
            f"AI classifier accuracy : {ai_acc:.0%}",
            f"Heuristic baseline     : {base_acc:.0%}",
            f"Cutoff ({ai_eval.CUTOFF:.0%}): {'PASS' if ai_eval.passes_cutoff(ai_acc) else 'FAIL'}",
            f"Beats baseline         : {'yes' if ai_acc > base_acc else 'no (tie/worse)'}",
            f"Leakage check          : {'CLEAN' if leak.clean else 'LEAK FOUND'}",
        ]
        if not available:
            lines.append("")
            lines.append("(AI off: the 'AI classifier' is the heuristic fallback.)")
        showInfo("\n".join(lines), parent=mw, title="Speedrun AI eval")

    mw.progress.start(label="Running AI eval...")
    mw.taskman.run_in_background(task, on_done)
