# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Speedrun AI Tools: settings, batch card-type classification, and the AI eval gate.

Network work runs off the main thread; collection writes happen back on the main thread.
"""

from __future__ import annotations

import aqt
import aqt.main
from anki.speedrun import ai, ai_eval, ai_items, cardcache
from anki.speedrun.cardtype import heuristic_classify
from anki.speedrun.disconfirmer import NOTETYPE_NAME, TAG_PREFIX
from anki.utils import strip_html
from aqt.qt import *
from aqt.utils import showInfo, tooltip

PERF_NOTETYPE = "Speedrun Performance Item"


def show_ai_settings(mw: aqt.main.AnkiQt) -> None:
    cfg = ai.get_config(mw.col)
    dlg = QDialog(mw)
    dlg.setWindowTitle("Speedrun AI settings")
    form = QFormLayout(dlg)

    enabled = QCheckBox("Enable AI hints")
    enabled.setChecked(bool(cfg["enabled"]))
    form.addRow(enabled)

    # No API key lives in the app: requests route through our server, which holds the
    # real key. Nothing to configure here beyond on/off.
    status = "on" if ai.ai_available(mw.col) else "off"
    form.addRow(
        QLabel(
            "AI is optional; the key/proxy is configured outside the app (an environment\n"
            f"variable or a local config file - see docs/aiproxy). Currently {status}."
        )
    )

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    form.addRow(buttons)
    qconnect(buttons.accepted, dlg.accept)
    qconnect(buttons.rejected, dlg.reject)
    if dlg.exec():
        ai.set_config(mw.col, enabled=enabled.isChecked())
        tooltip("Saved Speedrun AI settings.", parent=mw)


def classify_card_types(mw: aqt.main.AnkiQt) -> None:
    """Classify MCAT cards' type (AI if it cleared the cutoff, else heuristic) and cache
    it as a tag with its source."""
    col = mw.col
    client = ai.resolve_client(col)
    model = ai.get_config(col)["model"]
    gate_cached = ai.classifier_gate(col).get(model)
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
        # Network only (gate eval + classification) - collection writes happen in on_done.
        return ai.classify_items(client, items, gate_cached)

    def on_done(fut) -> None:
        mw.progress.finish()
        gate_result, labelled = fut.result()
        if gate_result is not None:
            ai.cache_classifier_gate(col, model, gate_result)
        for nid, card_type, prov in labelled:
            cardcache.set_cached_card_type(
                col, col.get_note(nid), card_type, source=prov.source
            )
        mw.reset()
        how = "AI" if ai.classifier_passes_gate(col) else "heuristic"
        tooltip(f"Classified {len(labelled)} cards ({how}).", parent=mw)

    mw.progress.start(label="Classifying card types...")
    mw.taskman.run_in_background(task, on_done)


def run_ai_eval(mw: aqt.main.AnkiQt) -> None:
    """Evaluate the AI classifier vs the heuristic baseline on the held-out gold set."""
    col = mw.col
    client = ai.resolve_client(col)
    available = ai.ai_available(col)

    def task():
        vector_fn = ai_eval.make_vector_baseline(ai.FEWSHOT_EXAMPLES)
        scores = ai_eval.compare(
            lambda q, a: ai.classify_card_type(client, q, a),
            heuristic_classify,
            vector_fn=vector_fn,
        )
        leak = ai_eval.fewshot_leakage(ai.FEWSHOT_EXAMPLES)
        return scores, leak

    def on_done(fut) -> None:
        mw.progress.finish()
        scores, leak = fut.result()
        ai_acc, base_acc = scores["ai"], scores["heuristic"]
        vec_acc = scores.get("vector", 0.0)
        beats = ai_acc > base_acc and ai_acc >= vec_acc
        lines = [
            f"AI enabled: {available}",
            "",
            f"AI classifier accuracy : {ai_acc:.0%}",
            f"Keyword baseline       : {base_acc:.0%}",
            f"Vector baseline        : {vec_acc:.0%}",
            f"Cutoff ({ai_eval.CUTOFF:.0%}): {'PASS' if ai_eval.passes_cutoff(ai_acc) else 'FAIL'}",
            f"Beats baselines        : {'yes' if beats else 'no (tie/worse)'}",
            f"Leakage check          : {'CLEAN' if leak.clean else 'LEAK FOUND'}",
        ]
        if not available:
            lines.append("")
            lines.append("(AI off: the 'AI classifier' is the heuristic fallback.)")
        showInfo("\n".join(lines), parent=mw, title="Speedrun AI eval")

    mw.progress.start(label="Running AI eval...")
    mw.taskman.run_in_background(task, on_done)


def generate_perf_items(mw: aqt.main.AnkiQt) -> None:
    """Generate exam-style items from a pasted source, behind the spec 7f gate.

    AI-off -> disabled (no fabrication). Items are added only if the batch clears the
    structural cutoff, and each item is dropped if it leaks (near-duplicates a held-out
    item) or is structurally invalid. Accepted items are held-out performance items.
    """
    col = mw.col
    client = ai.resolve_client(col)
    if client is None:
        showInfo(
            "AI is off. Item generation is disabled; the app still runs with AI off. "
            "Enable it in Tools > Speedrun > AI settings (an AI key or proxy must be configured).",
            parent=mw,
            title="Speedrun: Generate items",
        )
        return
    import random

    from anki.speedrun.sample_content import SOURCE_PASSAGES

    passage = random.choice(SOURCE_PASSAGES)
    source = passage["text"]
    source_name = passage["title"]
    nt = col.models.by_name(PERF_NOTETYPE)
    if nt is None:
        col.speedrun_ensure_notetypes()
        nt = col.models.by_name(PERF_NOTETYPE)
    if nt is None:
        showInfo("Performance Item note type is missing.", parent=mw)
        return

    def task():
        items = ai_items.generate_items(client, source, n=5, source_name=source_name)
        protected = []
        for nid in col.find_notes(f'note:"{PERF_NOTETYPE}"'):
            note = col.get_note(nid)
            protected.append(strip_html(note.fields[1]) if len(note.fields) > 1 else "")
        ev = ai_items.evaluate(items)
        accepted, rejected = ai_items.accept(items, protected)
        return ev, accepted, rejected

    def on_done(fut) -> None:
        mw.progress.finish()
        ev, accepted, rejected = fut.result()
        added = 0
        if ev["passes_cutoff"] and accepted:
            did = col.decks.id("MCAT::Generated")
            index = {f: i for i, f in enumerate(col.models.field_names(nt))}
            for it in accepted:
                note = col.new_note(nt)
                note.fields[index["ConceptId"]] = "generated"
                note.fields[index["Stem"]] = it.stem
                note.fields[index["OptionA"]] = it.options["A"]
                note.fields[index["OptionB"]] = it.options["B"]
                note.fields[index["OptionC"]] = it.options["C"]
                note.fields[index["OptionD"]] = it.options["D"]
                note.fields[index["Correct"]] = it.correct
                note.fields[index["Rationale"]] = it.rationale
                note.fields[index["Variant"]] = "1"
                note.tags = ["MCAT::Generated", "holdout::performance", "speedrun_generated"]
                col.add_note(note, did)
                added += 1
            mw.reset()
        lines = [
            f"Source: {source_name}",
            "",
            f"Generated {ev['n']}; structurally valid {ev['valid']} ({ev['pass_rate']:.0%}).",
            f"Cutoff {ev['cutoff']:.0%}: {'PASS' if ev['passes_cutoff'] else 'FAIL - nothing added'}.",
            f"Accepted (valid + no leakage): {len(accepted)}; rejected: {len(rejected)}.",
            f"Added to MCAT::Generated: {added}.",
        ]
        showInfo("\n".join(lines), parent=mw, title="Speedrun: Generate items")

    mw.progress.start(label="Generating items...")
    mw.taskman.run_in_background(task, on_done)
