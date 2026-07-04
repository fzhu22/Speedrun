import os, sys

sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]
from anki.collection import Collection

c = Collection(r"extra/speedrun-base/User 1/collection.anki2")
try:
    print("=== decks (total cards / new / lrn / rev-due / suspended / buried) ===")
    today = c.sched.today
    for d in sorted(c.decks.all_names_and_ids(), key=lambda x: x.name):
        did = d.id
        if d.name == "Default":
            continue
        total = c.db.scalar("select count() from cards where did=?", did) or 0
        if total == 0:
            print(f"  {d.name:<32} EMPTY (0 cards)")
            continue
        new = c.db.scalar("select count() from cards where did=? and queue=0", did) or 0
        lrn = c.db.scalar("select count() from cards where did=? and queue in (1,3)", did) or 0
        rev_due = c.db.scalar("select count() from cards where did=? and queue=2 and due<=?", did, today) or 0
        rev_future = c.db.scalar("select count() from cards where did=? and queue=2 and due>?", did, today) or 0
        susp = c.db.scalar("select count() from cards where did=? and queue=-1", did) or 0
        buried = c.db.scalar("select count() from cards where did=? and queue in (-2,-3)", did) or 0
        print(f"  {d.name:<32} total={total} new={new} lrn={lrn} rev_due={rev_due} rev_future={rev_future} susp={susp} buried={buried}")
    print("\ntoday (day number):", today)
    print("total cards:", c.card_count())
    print("total revlog:", c.db.scalar("select count() from revlog"))
finally:
    c.close()
