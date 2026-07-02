"""Read-only diagnostic: why does the Speedrun dashboard Memory abstain?

Opens your desktop collection and reports whether FSRS is producing a memory state
on your MCAT cards (the thing the Memory score needs). READ-ONLY - it makes no
changes. Close Anki before running it (Anki locks the collection).

Run from the anki/ folder:
    out\\pyenv\\Scripts\\python testdeck\\diagnose_collection.py
"""

from __future__ import annotations

import os
import sys

sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]

from anki.collection import Collection  # noqa: E402
from anki.consts import CARD_TYPE_REV, QUEUE_TYPE_REV  # noqa: E402

path = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(os.environ["APPDATA"], "Anki2", "User 1", "collection.anki2")
)
print(f"opening: {path}\n")

col = Collection(path)
try:
    # --- FSRS status (best-effort across versions) ---
    print("=== FSRS ===")
    try:
        print("  collection config 'fsrs':", col.get_config("fsrs", None))
    except Exception as e:
        print("  (could not read config fsrs:", e, ")")
    try:
        for dc in col.decks.all_config():
            keys = {k: dc[k] for k in dc if "fsrs" in k.lower()}
            print(f"  preset {dc.get('name')!r}: {keys}")
    except Exception as e:
        print("  (could not read deck presets:", e, ")")

    # --- Cards with an FSRS memory state anywhere ---
    all_cids = col.find_cards("")
    total_mem = sum(1 for cid in all_cids if col.get_card(cid).memory_state is not None)
    print(f"\n=== cards ({len(all_cids)} total) ===")
    print(f"  with an FSRS memory_state (whole collection): {total_mem}")

    # --- Reviewed today ---
    reviewed_today = col.db.scalar(
        "select count() from revlog where id > ?",
        (col.sched.day_cutoff - 86400) * 1000,
    )
    print(f"  reviews logged in the last 24h: {reviewed_today}")

    # --- MCAT-tagged cards ---
    mcat = col.find_cards("tag:MCAT::*")
    rev = mem = 0
    for cid in mcat:
        c = col.get_card(cid)
        if c.type == CARD_TYPE_REV:
            rev += 1
        if c.memory_state is not None:
            mem += 1
    print(f"\n=== MCAT-tagged cards ({len(mcat)}) ===")
    print(f"  in Review state (type=REV): {rev}")
    print(f"  with an FSRS memory_state:  {mem}")
    print("  sample:")
    for cid in list(mcat)[:6]:
        c = col.get_card(cid)
        print(
            f"    cid={cid} type={c.type} queue={c.queue} "
            f"mem={'yes' if c.memory_state else 'NO'} tags={c.note().tags}"
        )

    # --- What the dashboard returns ---
    res = col.speedrun_dashboard()
    print("\n=== speedrun_dashboard sections ===")
    for s in res.sections:
        mval = f"{round(s.memory*100)}%" if s.HasField("memory") else "ABSTAIN"
        print(f"  {s.abbrev:<12} coverage={round(s.coverage*100)}% memory={mval} n={s.reviewed_cards}")
    print(f"  readiness: {res.readiness_status}")
finally:
    col.close()
