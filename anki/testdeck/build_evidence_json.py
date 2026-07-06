# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Generate a single ``speedrun-evidence.json`` (the exact payload the in-app Evidence view
consumes) and bundle it into the AnkiDroid app assets, so the MOBILE dashboard's Evidence tab
works on-device.

The desktop serves this payload dynamically from ``qt/aqt/mediasrv.py``
(``speedrun_evidence``), reading the live ``docs/eval-artifacts/*.json``. The phone has no
mediasrv and no repo files, so we freeze the same payload into an asset at build time. Run it
after the eval harnesses (``just eval`` calls it); re-run to refresh the mobile evidence.

    out/pyenv/Scripts/python testdeck/build_evidence_json.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ANKI_ROOT = _HERE.parent
ARTIFACT_DIR = ANKI_ROOT / "docs" / "eval-artifacts"
#: The AnkiDroid app asset the mobile Evidence tab reads (see SpeedrunPage.handlePostRequest).
DEFAULT_OUT = (
    ANKI_ROOT.parent
    / "Anki-Android"
    / "AnkiDroid"
    / "src"
    / "main"
    / "assets"
    / "speedrun-evidence.json"
)

#: Section order, matching the desktop handler so both platforms show the same sequence.
ORDER = [
    "speed-bench", "memory-calibration", "performance", "score-mapping", "ai-eval",
    "ai-card-check", "leakage", "injection-redteam", "ablation", "crash-test", "sync-test",
]

#: Standing methodological caveats (kept identical to the desktop mediasrv handler).
STANDING_NULLS = [
    "The feature->MCAT-score link is observational, not proven (the Anki-to-exam "
    "literature is non-randomized; the one applied study is null - Wothe et al., Step 2 "
    "CK, p=0.440). Everything here grades the bridge steps, never a validated exam gain.",
    "Per-family fading (SPOV 6) is a bet: a large field RCT reversed it for high-ability "
    "learners, so it is instrumented with a disable-if-fixed-wins rule.",
    "The readiness score mapping is an unvalidated display-layer index (real-score "
    "anchoring is section 9 Step 4, out of scope).",
]


def build_payload() -> dict:
    loaded: dict = {}
    if ARTIFACT_DIR.is_dir():
        for p in ARTIFACT_DIR.glob("*.json"):
            try:
                loaded[p.stem] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    artifacts: list = []
    for name in sorted(loaded, key=lambda n: (ORDER.index(n) if n in ORDER else len(ORDER), n)):
        a = loaded[name]
        chart = a.get("chart")
        if chart:
            svg_path = ARTIFACT_DIR / chart
            if svg_path.exists():
                try:
                    a = {**a, "chart_svg": svg_path.read_text(encoding="utf-8")}
                except Exception:
                    pass
        artifacts.append(a)
    return {
        "available": bool(artifacts),
        "artifacts": artifacts,
        "standing_nulls": STANDING_NULLS,
    }


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    payload = build_payload()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload), encoding="utf-8")
    print(f"wrote {out} ({len(payload['artifacts'])} artifacts, {out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
