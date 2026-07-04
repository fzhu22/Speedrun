# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: the one-command benchmark (spec 7h + section 10 speed/reliability targets).

Loads the large benchmark collection (see ``build_bench_deck.py``) and prints, for each
action, the median (p50), 95th percentile (p95), and worst case - never a single
hand-picked number. Actions measured against the spec targets:

  * Button press acknowledged (answer_card)      target p95 < 50 ms
  * Next card after grading (get_queued_cards)    target p95 < 100 ms
  * Dashboard load / refresh (speedrun_dashboard) target p95 < 1000 / 500 ms
  * Cold start (open collection + first dashboard) target < 5 s (desktop)
  * Memory on the 50k deck (RSS)                   target: a stated limit

Honesty note: these are *engine-call* latencies measured headless - the objective,
reproducible core of each action. True end-to-end UI paint (button flash, no >100 ms
freeze) needs an instrumented client run and is measured separately; the engine call is
the dominant cost and the fair, comparable number.

Sync (< 5 s) is measured manually against the live server per SYNC.md (7b), since it
needs the network path; it is not part of this headless harness.

Run from the anki repo root:

    out/pyenv/Scripts/python testdeck/bench.py --col testdeck/bench.anki2      # Windows
    out/pyenv/bin/python     testdeck/bench.py --col testdeck/bench.anki2      # macOS/Linux
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANKI_ROOT = HERE.parent
os.chdir(ANKI_ROOT)
sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]

from anki.collection import Collection  # noqa: E402
from anki.scheduler.v3 import CardAnswer  # noqa: E402
from anki.utils import int_time  # noqa: E402


def _percentile(sorted_ms: list[float], p: float) -> float:
    """Nearest-rank percentile of a *sorted* list (p in [0, 100])."""
    if not sorted_ms:
        return float("nan")
    k = max(1, math.ceil(p / 100.0 * len(sorted_ms)))
    return sorted_ms[k - 1]


def _row(name: str, times_ms: list[float], target: str = "") -> dict:
    s = sorted(times_ms)
    p50 = _percentile(s, 50)
    p95 = _percentile(s, 95)
    worst = s[-1] if s else float("nan")
    print(f"  {name:<34} n={len(s):>5}  p50={p50:8.2f}ms  p95={p95:8.2f}ms  worst={worst:8.2f}ms  {target}")
    return {"action": name, "n": len(s), "p50_ms": p50, "p95_ms": p95, "worst_ms": worst}


def _rss_mb() -> float:
    import psutil

    return psutil.Process().memory_info().rss / (1024 * 1024)


def _force_due_reviews(col: Collection, did: int) -> None:
    """Set every card in the deck to a review due today (queue/type=2)."""
    today = col.sched.today
    col.db.transact(
        lambda: col.db.execute(
            "update cards set queue=2, type=2, due=?, ivl=1, factor=2500, reps=0, lapses=0"
            " where did=?",
            today,
            did,
        )
    )
    col.decks.select(did)


def bench_scheduler(col: Collection, iters: int) -> tuple[list[float], list[float]]:
    """Time answer_card (button ack) and get_queued_cards (next card).

    Forces the bench-deck cards to be due reviews. Next-card cost is measured on a full
    queue (get_queued_cards is idempotent / non-consuming), giving a large sample. Button
    press is measured by grading through the real queue, which enforces top-of-queue order;
    that consumes the deck's per-day review cap, i.e. one full study session's worth of
    grades. The caller runs this on a throwaway copy, so the mutation is harmless.
    """
    did = col.decks.id("Speedrun Bench")
    _force_due_reviews(col, did)

    next_ms: list[float] = []
    for _ in range(iters):
        t = time.perf_counter()
        col.sched.get_queued_cards()
        next_ms.append((time.perf_counter() - t) * 1000)

    answer_ms: list[float] = []
    qc = col.sched.get_queued_cards()
    while qc.cards and len(answer_ms) < iters:
        top = qc.cards[0]
        answer = CardAnswer(
            card_id=top.card.id,
            current_state=top.states.current,
            new_state=top.states.good,
            rating=CardAnswer.GOOD,
            answered_at_millis=int_time(1000),
            milliseconds_taken=1500,
        )
        t = time.perf_counter()
        col.sched.answer_card(answer)
        answer_ms.append((time.perf_counter() - t) * 1000)
        qc = col.sched.get_queued_cards()
    return answer_ms, next_ms


def bench_dashboard(col: Collection, n: int) -> tuple[float, list[float]]:
    """First-load latency (cold cache in-process) + the refresh distribution."""
    t = time.perf_counter()
    col.speedrun_dashboard()
    first_ms = (time.perf_counter() - t) * 1000
    refresh: list[float] = []
    for _ in range(n):
        t = time.perf_counter()
        col.speedrun_dashboard()
        refresh.append((time.perf_counter() - t) * 1000)
    return first_ms, refresh


def bench_cold_start(col_path: str, runs: int) -> list[float]:
    """Open the collection + first dashboard in a *fresh* process, ``runs`` times.

    Runs against a temporary copy so it never contends with the parent's open handle.
    """
    import shutil
    import tempfile

    code = (
        "import sys,time;"
        "sys.path[:0]=['pylib','qt','out/pylib','out/qt'];"
        "from anki.collection import Collection;"
        "t=time.perf_counter();"
        "c=Collection(sys.argv[1]);"
        "c.speedrun_dashboard();"
        "print((time.perf_counter()-t)*1000);"
        "c.close()"
    )
    out: list[float] = []
    for _ in range(runs):
        tmp = Path(tempfile.mkdtemp()) / "cold.anki2"
        shutil.copy(col_path, tmp)
        res = subprocess.run(
            [sys.executable, "-c", code, str(tmp)],
            cwd=str(ANKI_ROOT),
            capture_output=True,
            text=True,
        )
        try:
            out.append(float(res.stdout.strip().splitlines()[-1]))
        except Exception:
            print("  cold-start run failed:", res.stderr.strip()[:400])
        finally:
            try:
                tmp.unlink()
                tmp.parent.rmdir()
            except OSError:
                pass
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--col", default=str(HERE / "bench.anki2"))
    ap.add_argument("--answers", type=int, default=1000)
    ap.add_argument("--dashboard-iters", type=int, default=30)
    ap.add_argument("--cold-runs", type=int, default=5)
    args = ap.parse_args()

    import shutil
    import tempfile

    col_path = str(Path(args.col).resolve())
    if not Path(col_path).exists():
        print(f"benchmark collection not found; building it first ({col_path}) ...")
        subprocess.run(
            [sys.executable, str(HERE / "build_bench_deck.py"), "--out", col_path],
            cwd=str(ANKI_ROOT),
            check=True,
        )

    # Work on a throwaway copy: the scheduler bench mutates cards, and cold-start opens
    # the file in child processes; both must not disturb the pristine source.
    work_dir = Path(tempfile.mkdtemp(prefix="speedrun_bench_"))
    work_path = str(work_dir / "bench.anki2")
    shutil.copy(col_path, work_path)

    open_t = time.perf_counter()
    col = Collection(work_path)
    open_ms = (time.perf_counter() - open_t) * 1000
    try:
        n_cards = col.card_count()
        n_rev = col.db.scalar("select count() from revlog") or 0
        print(f"\n=== Speedrun benchmark (7h / section 10) ===")
        print(f"collection: {col_path}")
        print(f"cards: {n_cards:,}   revlog rows: {n_rev:,}   warm open: {open_ms:.0f}ms\n")

        rss_before = _rss_mb()
        answer_ms, next_ms = bench_scheduler(col, args.answers)
        first_dash, refresh_ms = bench_dashboard(col, args.dashboard_iters)
        rss_after = _rss_mb()

        print("Latency (engine calls):")
        rows = []
        rows.append(_row("Button press (answer_card)", answer_ms, "[target p95<50ms]"))
        rows.append(_row("Next card (get_queued_cards)", next_ms, "[target p95<100ms]"))
        rows.append(_row("Dashboard refresh", refresh_ms, "[target p95<500ms]"))
        print(f"  {'Dashboard first load':<34} n=    1  {'':10} single ={first_dash:8.2f}ms          [target p95<1000ms]")

        print("\nCold start (fresh process: open + first dashboard):")
        cold = bench_cold_start(col_path, args.cold_runs)
        _row("Cold start", cold, "[target <5000ms desktop]")

        print("\nMemory / footprint:")
        print(f"  RSS after load+dashboard : {rss_after:8.1f} MB  on {n_cards:,} cards  [state a limit, e.g. <1500MB]")
        print(f"  RSS delta during bench   : {rss_after - rss_before:8.1f} MB")

        worst = max(
            [x for x in (answer_ms + next_ms + refresh_ms) if not math.isnan(x)] or [0.0]
        )
        print("\nResponsiveness:")
        print(f"  worst single engine call : {worst:8.2f}ms  [target: nothing freezes >100ms]")
        print("\nSync of a normal session (<5s): measured manually vs the live server (SYNC.md 7b).")
        print("Note: engine-call latencies (headless). UI paint measured separately.\n")
    finally:
        col.close()
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
