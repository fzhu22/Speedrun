"""Smoke-test the Speedrun ablation flags + settings import (throwaway collection).

Run from the anki/ folder (does not touch your real collection):
    out\\pyenv\\Scripts\\python testdeck\\test_feature_flags.py
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
try:
    from anki.speedrun import pretest
    from aqt.speedrun import feature_settings, review, state  # noqa: F401

    checks = [
        ("pretest", pretest.pretest_enabled, pretest.set_pretest_enabled),
        ("disconfirmer", review.disconfirmer_enabled, review.set_disconfirmer_enabled),
        ("fading", state.fading_enabled, state.set_fading_enabled),
    ]
    all_ok = True
    for name, getter, setter in checks:
        default = getter(col)
        setter(col, False)
        off = getter(col)
        setter(col, True)
        on = getter(col)
        good = default is True and off is False and on is True
        all_ok = all_ok and good
        print(f"  {name:<13} default={default} off={off} on={on} -> {'OK' if good else 'FAIL'}")
    print("feature_settings import: OK")
    print("result:", "ALL OK" if all_ok else "FAIL")
finally:
    col.close()
