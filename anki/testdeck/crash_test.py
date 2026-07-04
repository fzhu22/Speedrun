# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: crash + offline resilience (spec 7g / section 10 reliability).

Two checks:

  1. CRASH: kill a process 20 times in a row while it is in the middle of a review
     (continuously answering cards, i.e. writing the collection), then reopen and run the
     database integrity check. Expect zero corrupted collections. SQLite's journalling is
     what protects us; this proves it holds under a hard kill (TerminateProcess / SIGKILL)
     mid-write.

  2. OFFLINE / AI-OFF: with no AI (client=None) and with a client that returns broken
     output, the AI features must turn off cleanly - no fabrication, deterministic
     fallbacks with provenance - while the app keeps working and the dashboard still
     produces a score.

Run from the anki repo root:

    out/pyenv/Scripts/python testdeck/crash_test.py
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANKI_ROOT = HERE.parent
os.chdir(ANKI_ROOT)
sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]

from anki.collection import Collection  # noqa: E402

# Child: open the collection and hammer the review loop (continuous writes) until killed.
_CHILD = r"""
import sys, time
sys.path[:0] = ['pylib', 'qt', 'out/pylib', 'out/qt']
from anki.collection import Collection
from anki.scheduler.v3 import CardAnswer
from anki.utils import int_time
c = Collection(sys.argv[1])
did = c.decks.id('Speedrun Bench')
today = c.sched.today
c.db.transact(lambda: c.db.execute(
    "update cards set queue=2, type=2, due=?, ivl=1, factor=2500, reps=0, lapses=0 where did=?",
    today, did))
c.decks.select(did)
print("child-ready", flush=True)
while True:
    qc = c.sched.get_queued_cards()
    if not qc.cards:
        c.db.transact(lambda: c.db.execute(
            "delete from revlog where cid in (select id from cards where did=?)", did))
        c.db.transact(lambda: c.db.execute(
            "update cards set queue=2, type=2, due=?, ivl=1 where did=?", today, did))
        continue
    top = qc.cards[0]
    ans = CardAnswer(card_id=top.card.id, current_state=top.states.current,
                     new_state=top.states.good, rating=CardAnswer.GOOD,
                     answered_at_millis=int_time(1000), milliseconds_taken=1000)
    c.sched.answer_card(ans)
"""


def build_base(path: str, n: int = 300) -> None:
    col = Collection(path)
    try:
        basic = col.models.by_name("Basic")
        did = col.decks.id("Speedrun Bench")
        for i in range(n):
            note = col.new_note(basic)
            note["Front"] = f"[Crash] card {i}"
            note["Back"] = f"answer {i}"
            note.tags = ["MCAT::1A"]
            col.add_note(note, did)
    finally:
        col.close()


def run_crash_test(base_path: str, iterations: int = 20) -> tuple[int, int]:
    print(f"\n=== Crash test: {iterations} hard kills mid-review ===")
    ok_count = 0
    for i in range(1, iterations + 1):
        work_dir = Path(tempfile.mkdtemp(prefix="speedrun_crash_"))
        work_path = str(work_dir / "c.anki2")
        shutil.copy(base_path, work_path)
        proc = subprocess.Popen(
            [sys.executable, "-c", _CHILD, work_path],
            cwd=str(ANKI_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        # Wait until the child is actively reviewing, then let it write for a random
        # short spell before a hard kill so we land in the middle of an operation.
        if proc.stdout is not None:
            proc.stdout.readline()  # "child-ready"
        time.sleep(random.uniform(0.03, 0.30))
        proc.kill()
        proc.wait()

        try:
            col = Collection(work_path)
            _msg, ok = col.fix_integrity()
            col.close()
        except Exception as exc:
            ok = False
            _msg = f"reopen failed: {exc}"
        ok_count += 1 if ok else 0
        print(f"  kill {i:>2}/{iterations}: {'OK - collection intact' if ok else 'CORRUPT -> ' + _msg[:80]}")
        shutil.rmtree(work_dir, ignore_errors=True)
    print(f"  result: {ok_count}/{iterations} collections intact after hard kill")
    return ok_count, iterations


def run_offline_test(base_path: str) -> bool:
    print("\n=== Offline / AI-off test ===")
    from anki.speedrun import ai, ai_items

    passed = True

    # AI OFF (client=None): no fabrication, deterministic fallbacks with provenance.
    items = ai_items.generate_items(None, "some source text", n=5)
    ok_no_fab = items == []
    advice, prov_a = ai.card_advice(None, "Q", "A", "topic")
    ok_advice = prov_a.source == "template" and bool(advice)
    hint, prov_h = ai.disconfirmer_hint(None, "Q", "A")
    ok_hint = prov_h.source == "template" and bool(hint)
    ideas, prov_i = ai.topic_card_ideas(None, "topic")
    ok_ideas = prov_i.source == "template" and bool(ideas)
    print(f"  AI-off no fabrication (generate=[])   : {'OK' if ok_no_fab else 'FAIL'}")
    print(f"  AI-off advice/hint/ideas -> template  : {'OK' if (ok_advice and ok_hint and ok_ideas) else 'FAIL'}")

    # Broken / rate-limited / offline service: a client that errors or returns garbage
    # must not crash callers - they fall back.
    class Boom:
        def complete(self, system: str, user: str) -> str:
            raise RuntimeError("simulated network error / rate limit")

    class Garbage:
        def complete(self, system: str, user: str) -> str:
            return "%%% not json at all %%%"

    boom_items = ai_items.generate_items(Boom(), "src", n=3)
    garbage_items = ai_items.generate_items(Garbage(), "src", n=3)
    advice_boom, prov_b = ai.card_advice(Boom(), "Q", "A")
    ok_broken = boom_items == [] and garbage_items == [] and prov_b.source == "template"
    print(f"  broken/garbage AI output -> safe []    : {'OK' if ok_broken else 'FAIL'}")

    # The dashboard/score still works fully offline.
    col = Collection(base_path)
    try:
        dash = col.speedrun_dashboard()
        ok_dash = dash is not None
    except Exception as exc:
        ok_dash = False
        print("   dashboard error:", exc)
    finally:
        col.close()
    print(f"  dashboard/score works offline          : {'OK' if ok_dash else 'FAIL'}")

    passed = ok_no_fab and ok_advice and ok_hint and ok_ideas and ok_broken and ok_dash
    print(f"  result: {'ALL OK' if passed else 'FAIL'}")
    return passed


def main() -> None:
    base_dir = Path(tempfile.mkdtemp(prefix="speedrun_crash_base_"))
    base_path = str(base_dir / "base.anki2")
    print("Speedrun crash + offline resilience (spec 7g)")
    print("building a small base collection ...")
    build_base(base_path, n=300)

    ok, total = run_crash_test(base_path, iterations=20)
    offline_ok = run_offline_test(base_path)

    shutil.rmtree(base_dir, ignore_errors=True)
    print("\n=== Summary ===")
    print(f"  crash test : {ok}/{total} intact  -> {'PASS' if ok == total else 'FAIL'}")
    print(f"  offline    : {'PASS' if offline_ok else 'FAIL'}")
    print("\nMobile note: on Android the equivalent is an adb kill loop -")
    print("  for i in $(seq 20); do adb shell am start -n com.ichi2.anki/.IntentHandler;")
    print("  sleep 3; adb shell am force-stop com.ichi2.anki; done")
    print("  then reopen the app and run Check Database (Tools) -> expect no errors.")


if __name__ == "__main__":
    main()
