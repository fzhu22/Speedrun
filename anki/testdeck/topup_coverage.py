"""Top up the Speedrun sample deck so every AAMC content category is covered.

Adds original ``[Sample]`` cards for any content category your collection is still
missing, raising the dashboard coverage (and lifting the readiness coverage veto).
Idempotent - safe to run more than once. Close Anki first (it locks the collection).

Run from the anki/ folder:
    out\\pyenv\\Scripts\\python testdeck\\topup_coverage.py
"""

from __future__ import annotations

import os
import sys

sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]

from anki.collection import Collection  # noqa: E402
from anki.speedrun import seeding  # noqa: E402

path = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(os.environ["APPDATA"], "Anki2", "User 1", "collection.anki2")
)
print(f"opening: {path}\n")

col = Collection(path)
try:
    before = col.speedrun_dashboard()
    added = seeding.seed_sample_deck(col)
    after = col.speedrun_dashboard()

    print(f"sample cards added (missing categories): {added}")
    print(
        f"coverage: {round(before.overall_coverage * 100)}% "
        f"({before.covered_leaves}/{before.total_leaves})  ->  "
        f"{round(after.overall_coverage * 100)}% "
        f"({after.covered_leaves}/{after.total_leaves})"
    )
    print("\nper-section coverage now:")
    for s in after.sections:
        print(f"  {s.abbrev:<12} {round(s.coverage * 100)}%")
    print(f"\nreadiness: {after.readiness_status}")
finally:
    col.close()
