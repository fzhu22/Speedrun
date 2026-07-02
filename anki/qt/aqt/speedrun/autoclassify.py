# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Automatic, background card-type classification when a deck is opened.

Folds the AI's "does this card warrant a disconfirmer?" decision into the study loop:
on the deck Overview screen, uncached MCAT cards in that deck are classified in the
background (AI if enabled, else heuristic) and cached as a tag, so by the time the
student misses a card the gating already reflects the decision - no Tools step, no
mid-review lag.
"""

from __future__ import annotations

import aqt
import aqt.main
from anki.speedrun import ai, cardcache
from anki.speedrun.disconfirmer import NOTETYPE_NAME, TAG_PREFIX

MAX_PER_RUN = 60  # bound cost/time; later Overview refreshes pick up the rest

_running = False


def on_overview_refresh(overview) -> None:
    mw = aqt.mw
    if mw is None or mw.col is None:
        return
    global _running
    if _running:
        return
    col = mw.col
    try:
        deck_name = col.decks.name_if_exists(col.decks.get_current_id())
    except Exception:
        return
    if not deck_name:
        return

    search = (
        f'deck:"{deck_name}" tag:{TAG_PREFIX}::* '
        f'-tag:{cardcache.CTYPE_TAG_PREFIX}::* -note:"{NOTETYPE_NAME}"'
    )
    items = cardcache.uncached_items(col, search, MAX_PER_RUN)
    if not items:
        return

    client = ai.resolve_client(col)
    model = ai.get_config(col)["model"]
    gate_cached = ai.classifier_gate(col).get(model)
    _running = True

    def task():
        # Network only (gate eval + classification) - no collection writes off-thread.
        return ai.classify_items(client, items, gate_cached)

    def on_done(fut) -> None:
        global _running
        _running = False
        try:
            gate_result, labelled = fut.result()
            if gate_result is not None:  # first eval for this model -> cache the verdict
                ai.cache_classifier_gate(col, model, gate_result)
            for nid, card_type, prov in labelled:
                cardcache.set_cached_card_type(
                    col, col.get_note(nid), card_type, source=prov.source
                )
        except Exception as exc:  # never break the overview
            print("speedrun: auto-classify failed:", exc)

    mw.taskman.run_in_background(task, on_done)
