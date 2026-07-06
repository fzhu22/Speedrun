# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Generate ``docs/eval-results.md`` from the JSON artifacts in ``docs/eval-artifacts/``.

Every harness (calibration, performance, AI eval, AI card check, leakage, injection
red-team, ablation, score mapping, and - when run - the speed bench + crash test) writes a
self-describing JSON artifact. This script renders them into one report, so the numbers in
the report are GENERATED, never hand-typed. A closing "Results that did not work" section
aggregates each artifact's honest ``nulls`` plus the standing methodological caveats.

Run after the harnesses (``just eval`` does this):

    out/pyenv/Scripts/python testdeck/build_report.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from _artifacts import ARTIFACT_DIR, ANKI_ROOT, load_artifacts

REPORT_PATH = ANKI_ROOT / "docs" / "eval-results.md"
#: Snapshot of the artifacts bundled into the shared Svelte page, so the in-app Evidence
#: panel works on mobile too (AnkiDroid has no docs/eval-artifacts folder and no
#: /_anki/speedrunEvidence handler). Same shape the desktop endpoint returns; SVGs inlined.
TS_EVIDENCE_BUNDLE = ANKI_ROOT / "ts" / "routes" / "speedrun" / "evidence-data.json"

#: Section order in the report (by artifact name). Unknown artifacts append after these.
ORDER = [
    "speed-bench",
    "memory-calibration",
    "performance",
    "score-mapping",
    "ai-eval",
    "ai-card-check",
    "leakage",
    "injection-redteam",
    "ablation",
    "ablation-disconfirmer",
    "crash-test",
    "sync-test",
]

#: Standing honest negatives that are true regardless of a given run (methodology /
#: literature), always listed in "Results that did not work".
STANDING_NULLS = [
    "The feature->MCAT-score link is observational, not proven: the Anki-to-exam "
    "literature is non-randomized and the one applied study that measured it directly is "
    "null (Wothe et al., Step 2 CK, 252.5 vs 247.0, p=0.440). Everything here grades the "
    "*bridge steps*, never a validated exam gain.",
    "Per-family support-fading (SPOV 6) is a bet, not a settled win: a large field RCT "
    "reversed adaptive-vs-fixed for high-ability learners (the MCAT population), so it is "
    "instrumented with a 'disable if fixed wins for high-ability' disconfirmer.",
    "Readiness score mapping is an unvalidated display-layer index (section 9 Step 4, "
    "anchoring to real MCAT scores, needs longitudinal data and is out of scope).",
]


def _fmt_meta(a: dict) -> str:
    bits = []
    if a.get("model"):
        bits.append(f"model `{a['model']}`")
    if a.get("seed") is not None:
        bits.append(f"seed {a['seed']}")
    if a.get("git_commit"):
        bits.append(f"commit `{a['git_commit']}`")
    if a.get("generated_at"):
        bits.append(a["generated_at"])
    return " - ".join(bits)


def _render_section(a: dict) -> List[str]:
    out: List[str] = []
    title = a.get("title", a.get("name", "section"))
    spec = a.get("spec", "")
    heading = f"## {title}" + (f"  ({spec})" if spec else "")
    out.append(heading)
    out.append("")
    meta = _fmt_meta(a)
    if meta:
        out.append(f"*{meta}*")
        out.append("")
    if a.get("command"):
        out.append(f"Reproduce: `{a['command']}`")
        out.append("")
    for line in a.get("summary", []):
        out.append(f"- {line}")
    if a.get("summary"):
        out.append("")
    table = a.get("table")
    if table and table.get("headers"):
        out.append("| " + " | ".join(str(h) for h in table["headers"]) + " |")
        out.append("| " + " | ".join("---" for _ in table["headers"]) + " |")
        for row in table.get("rows", []):
            out.append("| " + " | ".join(str(c) for c in row) + " |")
        out.append("")
    if a.get("verdict"):
        out.append(f"**Verdict: {a['verdict']}**")
        out.append("")
    chart = a.get("chart")
    if chart and (ARTIFACT_DIR / chart).exists():
        out.append(f"![{title}](eval-artifacts/{chart})")
        out.append("")
    return out


#: Stubs for sections produced by separate commands, so the report keeps the section (with
#: a "run this" note) instead of silently dropping it when that harness has not been run.
STUBS = {
    "speed-bench": {
        "title": "Speed + reliability benchmark",
        "spec": "spec 7h / section 10",
        "command": "just bench",
        "summary": ["Not generated in this run - run `just bench` (builds the 50k deck) to "
                    "populate p50/p95/worst latency + memory."],
    },
    "crash-test": {
        "title": "Crash + offline resilience",
        "spec": "spec 7g",
        "command": "just crash-test",
        "summary": ["Not generated in this run - run `just crash-test` to populate the "
                    "20x-kill integrity + offline/AI-off result."],
    },
    "sync-test": {
        "title": "Two-way sync + conflict resolution",
        "spec": "spec 7b",
        "command": "just sync-test",
        "summary": ["Not generated in this run - run `just sync-test` to populate the "
                    "10+10 offline merge + same-card last-writer-wins result."],
    },
}


def write_web_bundle() -> int:
    """Emit the real artifacts (SVGs inlined) as a static JSON the shared Svelte page can
    bundle, matching the desktop ``speedrun_evidence`` endpoint's payload. This is what lets
    the in-app Evidence panel render on AnkiDroid, which has neither the endpoint nor the
    filesystem artifacts. Returns the artifact count written."""
    arts = load_artifacts()  # real artifacts only (no stubs)
    names = [n for n in ORDER if n in arts] + [n for n in arts if n not in ORDER]
    out_artifacts: List[dict] = []
    for name in names:
        a = dict(arts[name])
        chart = a.get("chart")
        if chart and (ARTIFACT_DIR / chart).exists():
            try:
                a["chart_svg"] = (ARTIFACT_DIR / chart).read_text(encoding="utf-8")
            except Exception:
                pass
        out_artifacts.append(a)
    payload = {
        "available": len(out_artifacts) > 0,
        "artifacts": out_artifacts,
        "standing_nulls": STANDING_NULLS,
    }
    TS_EVIDENCE_BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    TS_EVIDENCE_BUNDLE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return len(out_artifacts)


def main() -> None:
    artifacts = load_artifacts()
    for name, stub in STUBS.items():
        artifacts.setdefault(name, {"name": name, **stub})

    ordered: List[dict] = []
    seen = set()
    for name in ORDER:
        if name in artifacts:
            ordered.append(artifacts[name])
            seen.add(name)
    for name, a in artifacts.items():
        if name not in seen:
            ordered.append(a)

    lines: List[str] = []
    lines.append("# Speedrun evaluation results (spec 7 / 8 / 9 / 10)")
    lines.append("")
    lines.append("> Generated by `testdeck/build_report.py` from the JSON artifacts in "
                 "[eval-artifacts/](eval-artifacts/). Do not hand-edit numbers here - re-run "
                 "`just eval` (and `just bench` / `just crash-test`) to regenerate.")
    lines.append("")
    lines.append("Every figure is reproducible from the repo. Offline/synthetic runs need no "
                 "API key (deterministic stand-ins); the AI columns use the real model only "
                 "when an `api-key` / proxy token is configured, and each artifact records "
                 "which `model` produced it. Synthetic review logs and simulated responses "
                 "are labelled as such; no real-student exam validation is claimed "
                 "(section 9 Step 4).")
    lines.append("")
    lines.append("```")
    lines.append("just eval        # calibration, performance, score mapping, AI eval + card")
    lines.append("                 # check, leakage, injection red-team, ablation, this report")
    lines.append("just bench       # 7h + section 10 speed/memory on the 50k deck")
    lines.append("just crash-test  # 7g crash (20x kill) + offline/AI-off")
    lines.append("```")
    lines.append("")

    if not ordered:
        lines.append("_No artifacts found yet. Run `just eval` to generate them._")
        lines.append("")
    for a in ordered:
        lines.extend(_render_section(a))

    # Results that did not work: per-artifact nulls + standing caveats.
    lines.append("## Results that did not work (honest reporting, spec section 8)")
    lines.append("")
    lines.append("Negative and null results are first-class here - the point of a fair test "
                 "is that it could fail.")
    lines.append("")
    any_run_nulls = False
    for a in ordered:
        for n in a.get("nulls", []):
            lines.append(f"- **{a.get('title', a.get('name'))}:** {n}")
            any_run_nulls = True
    if not any_run_nulls:
        lines.append("- (No run-specific nulls recorded in the current artifacts.)")
    lines.append("")
    lines.append("Standing methodological caveats (true regardless of any single run):")
    lines.append("")
    for n in STANDING_NULLS:
        lines.append(f"- {n}")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT_PATH} from {len(ordered)} artifact(s)")
    n_bundle = write_web_bundle()
    print(f"wrote {TS_EVIDENCE_BUNDLE} ({n_bundle} artifacts) for the in-app evidence panel")
    missing = [n for n in ORDER if n not in artifacts]
    if missing:
        print("note: no artifact yet for: " + ", ".join(missing)
              + "  (run the matching harness / just bench / just crash-test)")


if __name__ == "__main__":
    main()
