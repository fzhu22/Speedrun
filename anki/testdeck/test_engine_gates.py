"""Prove the ablation toggles gate the shared engine (throwaway collection).

Both the disconfirmer prompt and support-fading must obey the synced collection-config
flags in the ENGINE, so desktop and mobile behave identically. Read-only w.r.t. your
real data (uses a temp collection).

    out\\pyenv\\Scripts\\python testdeck\\test_engine_gates.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]

from anki.collection import Collection  # noqa: E402

col = Collection(str(Path(tempfile.mkdtemp()) / "c.anki2"))
ok = True
try:
    basic = col.models.by_name("Basic")
    deck = col.decks.id("MCAT")
    note = col.new_note(basic)
    note["Front"] = "Why does a competitive inhibitor raise Km but not Vmax?"
    note["Back"] = "It competes at the active site; excess substrate overcomes it."
    note.tags = ["MCAT::1A"]
    col.add_note(note, deck)
    cid = col.card_ids_of_note(note.id)[0]

    def prompts() -> bool:
        return col.speedrun_should_prompt_disconfirmer(
            card_id=cid, rating=1, session_misses=0
        ).should_prompt

    # Disconfirmer: default on -> prompts; toggle off -> silent; on -> prompts.
    from aqt.speedrun import review, state

    d0 = prompts()
    review.set_disconfirmer_enabled(col, False)
    d1 = prompts()
    review.set_disconfirmer_enabled(col, True)
    d2 = prompts()
    print(f"disconfirmer: default={d0} off={d1} on={d2} -> {'OK' if (d0 and not d1 and d2) else 'FAIL'}")
    ok = ok and d0 and not d1 and d2

    # Fading: default on writes a rung; toggle off is a no-op.
    def fading_changes() -> bool:
        # transfer tag + application card so a success would advance the ladder
        n = col.get_note(note.id)
        return bool(col.speedrun_record_review(card_id=cid, rating=3).family)

    state.set_fading_enabled(col, True)
    f_on = fading_changes()
    state.set_fading_enabled(col, False)
    f_off = fading_changes()
    print(f"fading: on_writes_family={f_on} off_is_noop={not f_off} -> {'OK' if (f_on and not f_off) else 'FAIL'}")
    ok = ok and f_on and not f_off

    print("result:", "ALL OK" if ok else "FAIL")
finally:
    col.close()
