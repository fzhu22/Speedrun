"""Smoke-test the dev portal's HTML builder against the real collection (read-only).

Close Anki first. Run from the anki/ folder:
    out\\pyenv\\Scripts\\python testdeck\\test_dev_portal.py
"""

from __future__ import annotations

import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]

from anki.collection import Collection  # noqa: E402

path = os.path.join(os.environ["APPDATA"], "Anki2", "User 1", "collection.anki2")
col = Collection(path)
try:
    from aqt.speedrun.dev_portal import build_html

    doc = build_html(col)
    print("build_html OK - length:", len(doc))
    for needle in (
        "Speedrun Dev Portal",
        "Content categories",
        "Study plan (live",
        "Prerequisite edges",
        "Graph model status",
    ):
        print(f"  contains {needle!r}: {needle in doc}")
except Exception:
    traceback.print_exc()
finally:
    col.close()
