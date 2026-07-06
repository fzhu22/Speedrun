# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Automated two-way sync test (spec 7b) - no second physical device needed.

Spins up the bundled Anki sync server as a subprocess on localhost, then drives TWO
separate collections (``desktop.anki2`` and ``phone.anki2``) through the same account,
exactly as the desktop and phone builds would:

  1. Seed: build a deck on "desktop", full-upload it, full-download it onto "phone" so both
     start identical (the same cards on the shared engine).
  2. Merge (the core 7b claim): offline, answer 10 cards on the phone and 10 DIFFERENT
     cards on the desktop, then sync both. Assert all 20 reviews land exactly once on each
     side - none lost, none double-counted (the revlog merge is append-by-id).
  3. Conflict: offline, answer the SAME card differently on both, then sync. Anki merges at
     the object level with last-writer-wins by modification time (a deterministic winner),
     while BOTH revlog rows are kept. Assert the two collections converge and the later
     review wins - no forced Upload/Download is needed for a plain review divergence.

Writes ``docs/eval-artifacts/sync-test.json`` so the result is reproducible evidence.

Run from the anki repo root:

    out/pyenv/Scripts/python testdeck/sync_test.py
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANKI_ROOT = HERE.parent
os.chdir(ANKI_ROOT)
sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import _artifacts  # noqa: E402
from anki.collection import Collection  # noqa: E402
from anki.sync import SyncAuth  # noqa: E402

USER, PASS = "user", "pass"
N_NOTES = 24  # 10 for desktop + 10 for phone + spares (incl. the conflict card)


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _wait_health(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def _start_server(port: int, base: str) -> subprocess.Popen:
    env = {
        **os.environ,
        "SYNC_HOST": "127.0.0.1",
        "SYNC_PORT": str(port),
        "SYNC_BASE": base,
        "SYNC_USER1": f"{USER}:{PASS}",
        "PYTHONPATH": os.pathsep.join(["pylib", "out/pylib"]),
    }
    return subprocess.Popen(
        [sys.executable, "-m", "anki.syncserver"],
        env=env,
        cwd=str(ANKI_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _seed_desktop(col: Collection, n: int) -> None:
    basic = col.models.by_name("Basic")
    did = col.decks.id("Speedrun Sync")
    for i in range(n):
        note = col.new_note(basic)
        note["Front"] = f"[Sync] card {i}"
        note["Back"] = f"answer {i}"
        note.tags = ["MCAT::BioBiochem::1A"]
        col.add_note(note, did)


def _auth(col: Collection, url: str) -> SyncAuth:
    hkey = col.sync_login(USER, PASS, url).hkey
    return SyncAuth(hkey=hkey, endpoint=url)


def _full(col: Collection, auth: SyncAuth, *, upload: bool) -> None:
    col.close_for_full_sync()
    col.full_upload_or_download(auth=auth, server_usn=None, upload=upload)
    col.reopen(after_full_sync=True)


def _normal_sync(col: Collection, auth: SyncAuth) -> int:
    """A normal (merging) sync; returns the ``required`` code the server asked for."""
    out = col.sync_collection(auth, False)
    req = out.required
    if req == out.FULL_UPLOAD:
        _full(col, auth, upload=True)
    elif req == out.FULL_DOWNLOAD:
        _full(col, auth, upload=False)
    return req


def _review(col: Collection, cids: list[int], ease: int) -> None:
    """Answer specific cards by id (ease 1=Again .. 4=Easy). Each writes one revlog row."""
    for cid in cids:
        card = col.get_card(cid)
        card.start_timer()  # we bypass the reviewer, so set the answer timer ourselves
        col.sched.answerCard(card, ease)


def _revlog_count(col: Collection) -> int:
    return col.db.scalar("select count() from revlog") or 0


def _revlog_distinct(col: Collection) -> int:
    return col.db.scalar("select count(distinct id) from revlog") or 0


def _revlog_for(col: Collection, cid: int) -> int:
    return col.db.scalar("select count() from revlog where cid=?", cid) or 0


def main() -> int:
    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    tmp = Path(tempfile.mkdtemp(prefix="speedrun-sync-"))
    server_base = tmp / "server"
    server_base.mkdir()
    proc = _start_server(port, str(server_base))

    results: dict = {}
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        checks.append((name, bool(cond), detail))
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))

    desktop = phone = None
    try:
        print(f"=== Speedrun two-way sync test (7b) ===\nserver: {url}")
        if not _wait_health(url + "health"):
            raise RuntimeError("sync server did not become healthy")
        print("server healthy")

        desktop = Collection(str(tmp / "desktop.anki2"))
        phone = Collection(str(tmp / "phone.anki2"))

        # 1) Seed: desktop uploads a deck, phone downloads it -> identical start.
        _seed_desktop(desktop, N_NOTES)
        auth_d = _auth(desktop, url)
        auth_p = _auth(phone, url)
        up = desktop.sync_collection(auth_d, False)
        check("desktop first sync asks for a full upload",
              up.required in (up.FULL_UPLOAD, up.FULL_SYNC), f"required={up.required}")
        _full(desktop, auth_d, upload=True)
        down = phone.sync_collection(auth_p, False)
        check("phone first sync asks for a full download",
              down.required in (down.FULL_DOWNLOAD, down.FULL_SYNC), f"required={down.required}")
        _full(phone, auth_p, upload=False)

        cids = desktop.db.list("select id from cards order by id")
        pcids = phone.db.list("select id from cards order by id")
        check("both devices hold the same cards after seed",
              cids == pcids and len(cids) >= 21, f"{len(cids)} cards each")

        # 2) Merge: 10 different reviews on each side, offline, then sync both ways.
        desk_cards = cids[0:10]
        phone_cards = cids[10:20]
        _review(desktop, desk_cards, 3)  # Good
        _review(phone, phone_cards, 3)
        check("desktop recorded 10 reviews offline", _revlog_count(desktop) == 10)
        check("phone recorded 10 reviews offline", _revlog_count(phone) == 10)

        _normal_sync(phone, auth_p)     # push phone's 10
        req_merge = _normal_sync(desktop, auth_d)  # pull phone's 10, push desktop's 10
        _normal_sync(phone, auth_p)     # pull desktop's 10 -> phone now has all 20

        d_total, d_distinct = _revlog_count(desktop), _revlog_distinct(desktop)
        p_total, p_distinct = _revlog_count(phone), _revlog_distinct(phone)
        check("desktop has all 20 reviews, none doubled",
              d_total == 20 and d_distinct == 20, f"total={d_total} distinct={d_distinct}")
        check("phone has all 20 reviews, none doubled",
              p_total == 20 and p_distinct == 20, f"total={p_total} distinct={p_distinct}")
        # A completed normal sync returns NO_CHANGES (0) or NORMAL_SYNC (1); a forced full
        # sync would be FULL_SYNC (2) / FULL_DOWNLOAD (3) / FULL_UPLOAD (4).
        check("the merge was a normal two-way sync (no forced full sync)",
              req_merge in (0, 1), f"required={req_merge}")

        # 3) Conflict: same card, answered differently on both offline; last write wins.
        conflict = cids[20]
        _review(phone, [conflict], 3)      # phone: Good
        time.sleep(1.2)                    # ensure desktop's mtime is strictly later
        _review(desktop, [conflict], 1)    # desktop: Again (the later, winning write)
        desk_win_mod = desktop.get_card(conflict).mod

        req_conf = _normal_sync(phone, auth_p)      # push phone's answer
        _normal_sync(desktop, auth_d)               # merge: desktop's later write wins
        _normal_sync(phone, auth_p)                 # pull the winner back to phone

        check("same-card conflict resolved by a normal sync (object-level merge)",
              req_conf in (0, 1), f"required={req_conf}")
        check("both revlog rows for the conflicted card are kept (none dropped)",
              _revlog_for(desktop, conflict) == 2 and _revlog_for(phone, conflict) == 2,
              f"desktop={_revlog_for(desktop, conflict)} phone={_revlog_for(phone, conflict)}")
        check("last-writer-wins: the later desktop review wins on BOTH devices",
              desktop.get_card(conflict).mod == phone.get_card(conflict).mod == desk_win_mod,
              f"desktop={desktop.get_card(conflict).mod} phone={phone.get_card(conflict).mod}")

        results = {
            "cards_each": len(cids),
            "desktop_revlog": d_total,
            "phone_revlog": p_total,
            "merge_required_code": int(req_merge),
            "conflict_required_code": int(req_conf),
        }
    finally:
        for c in (desktop, phone):
            try:
                if c is not None:
                    c.close()
            except Exception:
                pass
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)

    all_pass = all(ok for _n, ok, _d in checks)
    print(f"\nOVERALL: {'PASS' if all_pass else 'FAIL'}")

    nulls = [
        "A plain review divergence (same card, different answers) is resolved by Anki's "
        "object-level last-writer-wins merge, NOT the forced Upload/Download full sync - "
        "that only triggers on a schema divergence (e.g. a notetype change on both sides). "
        "Both revlog rows are always kept, so no review is ever lost or double-counted.",
        "This runs two collections on one machine against the bundled server; it proves the "
        "engine's sync/merge, not device-specific transport (which the phone build exercises "
        "over the same protocol).",
    ]
    if not all_pass:
        nulls.append("One or more sync checks FAILED this run - see the table.")

    _artifacts.write_artifact(
        "sync-test",
        {
            "title": "Two-way sync + conflict resolution (offline, then merge)",
            "spec": "spec 7b",
            "command": "just sync-test  (sync_test.py)",
            "model": _artifacts.OFFLINE_MODEL,
            "summary": [
                "Bundled sync server on localhost; two collections (desktop + phone) on one "
                "account, seeded identically via full upload/download.",
                "Merge: 10 reviews on phone + 10 DIFFERENT on desktop, offline; after syncing "
                f"both, each side holds **{results.get('desktop_revlog', '?')}** reviews with "
                "none lost and none double-counted (revlog merge is append-by-id).",
                "Conflict: the same card answered differently on both offline resolves to a "
                "deterministic last-writer-wins winner on both devices, and BOTH revlog rows "
                "are kept.",
            ],
            "table": {
                "headers": ["Check", "Result"],
                "rows": [[name, "PASS" if ok else "FAIL"] for name, ok, _d in checks],
            },
            "metrics": {
                "checks_total": len(checks),
                "checks_passed": sum(1 for _n, ok, _d in checks if ok),
                "all_pass": all_pass,
                **results,
            },
            "verdict": ("PASS - two-way sync merges cleanly; conflict has a clear winner"
                        if all_pass else "FAIL - see checks"),
            "nulls": nulls,
        },
    )
    print("wrote artifact: docs/eval-artifacts/sync-test.json")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
