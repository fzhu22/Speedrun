# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: the AI card check (spec 7f).

Generates ~50 multiple-choice cards from ONE cited source (``card_gen_source.md``), then
runs every card through the checker and reports the three counts the spec asks for:

  * correct + useful      - supported by the source and good teaching (ACCEPTED)
  * wrong                 - the marked answer is not supported / contradicts the source
                            (a wrong fact is worse than no card -> BLOCKED)
  * correct but bad       - correct yet vague, trivial, or a duplicate/leak of the gold
                            set (BLOCKED)

The passing cutoff is declared BELOW, before any results are seen, and every card that
fails it is blocked. Correctness is fact-checked by the LLM against the source; teaching
quality and duplication are deterministic. With no AI key configured the generator makes
no cards (no fabrication) and the check reports "not run".

Run from the anki repo root (needs a proxy token or SPEEDRUN_AI_KEY for the AI path):

    out/pyenv/Scripts/python testdeck/run_ai_card_check.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ANKI = _HERE.parent
os.chdir(_ANKI)
sys.path[:0] = ["pylib", "qt", "out/pylib", "out/qt"]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import _artifacts  # noqa: E402
from anki.speedrun import ai, ai_items  # noqa: E402
from anki.speedrun.performance import LEAKAGE_THRESHOLD, leakage_check  # noqa: E402

# ---- Passing cutoff, declared BEFORE looking at results (spec 7f) -------------------
N_TARGET = 50
CUTOFF_MAX_WRONG = 0  # a single wrong fact fails the batch (worse than no card)
CUTOFF_MIN_USEFUL_FRACTION = 0.60  # >= 60% of generated cards must be correct + useful


def _gold_stems() -> list[str]:
    data = json.loads((_HERE / "card_gen_gold.json").read_text(encoding="utf-8"))
    return [it["q"] for it in data["items"]]


def main() -> None:
    source = (_HERE / "card_gen_source.md").read_text(encoding="utf-8")
    gold = _gold_stems()

    print("=== Speedrun AI card check (spec 7f) ===")
    print(f"source: card_gen_source.md   gold set: {len(gold)} Q/A pairs")
    print(
        f"cutoff (pre-registered): wrong <= {CUTOFF_MAX_WRONG} AND "
        f"correct+useful >= {CUTOFF_MIN_USEFUL_FRACTION:.0%} of generated\n"
    )

    key = ai.api_key()
    if not key:
        print("AI OFF -> generator makes no cards (no fabrication); check NOT RUN.")
        print("Configure SPEEDRUN_AI_KEY or the proxy token to run the real check.")
        _artifacts.write_artifact(
            "ai-card-check",
            {
                "title": "AI card check (generate from a cited source, then verify)",
                "spec": "spec 7f",
                "command": "just eval  (run_ai_card_check.py; needs an api-key)",
                "model": _artifacts.OFFLINE_MODEL,
                "summary": [
                    "AI OFF (no api-key configured): the generator makes no cards (no "
                    "fabrication), so the 7f check is NOT RUN. This is the correct AI-off "
                    "behaviour; configure an api-key and re-run to record the counts.",
                    f"Pre-registered cutoff (unchanged): wrong <= {CUTOFF_MAX_WRONG} AND "
                    f"correct+useful >= {CUTOFF_MIN_USEFUL_FRACTION:.0%} of generated.",
                ],
                "metrics": {"status": "not_run_ai_off", "gold_items": len(gold)},
                "verdict": "NOT RUN (AI off)",
                "nulls": [
                    "The 7f card check requires the real model; with no key it does not run "
                    "(and correctly generates nothing rather than fabricating cards)."
                ],
            },
        )
        print("wrote artifact: docs/eval-artifacts/ai-card-check.json (status: not run)")
        return
    client = ai.OpenAICompatibleClient(
        base_url=ai.base_url(), model=ai._DEFAULTS["model"], api_key=key, timeout=180
    )
    print(f"AI ON -> base_url={ai.base_url()} model={ai._DEFAULTS['model']}")

    print(f"generating {N_TARGET} items from the source ...")
    items = ai_items.generate_items(client, source, n=N_TARGET, source_name="Sample Biochem Chapter")
    if not items:
        print("generation returned no items (network/parse failure); check NOT RUN.")
        return
    print(f"generated {len(items)} items; checking ...\n")

    stems = [it.stem for it in items]
    gold_leak = {int(m["index"]) for m in leakage_check(gold, stems, threshold=LEAKAGE_THRESHOLD).matches}

    correct_useful: list = []
    wrong: list = []
    correct_bad: list = []
    malformed: list = []

    for i, it in enumerate(items):
        struct = ai_items.structural_problems(it)
        if struct:
            malformed.append({"stem": it.stem, "problems": struct})
            continue
        ok, reason = ai_items.judge_correctness(client, it, source)
        if ok is not True:
            wrong.append({"stem": it.stem, "reason": reason})
            continue
        problems = ai_items.teaching_problems(it)
        if i in gold_leak:
            problems.append("duplicate/leak of a gold item")
        # within-batch duplicate against earlier stems
        if i > 0 and not leakage_check(stems[:i], [it.stem], threshold=LEAKAGE_THRESHOLD).clean:
            problems.append("duplicate of an earlier generated card")
        if problems:
            correct_bad.append({"stem": it.stem, "problems": problems})
        else:
            correct_useful.append(it)
        if (i + 1) % 10 == 0:
            print(f"  checked {i + 1}/{len(items)}")

    n = len(items)
    n_useful = len(correct_useful)
    n_wrong = len(wrong)
    n_bad = len(correct_bad)
    n_malformed = len(malformed)
    useful_fraction = n_useful / n if n else 0.0

    print("\n--- results (the three counts) ---")
    print(f"  generated              : {n}")
    print(f"  correct + useful (KEEP): {n_useful}   ({useful_fraction:.0%})")
    print(f"  wrong (BLOCK)          : {n_wrong}")
    print(f"  correct but bad (BLOCK): {n_bad}")
    print(f"  malformed (BLOCK)      : {n_malformed}")
    print(f"  accepted onto deck     : {n_useful}   blocked: {n_wrong + n_bad + n_malformed}")

    passes = n_wrong <= CUTOFF_MAX_WRONG and useful_fraction >= CUTOFF_MIN_USEFUL_FRACTION
    print(f"\n  CUTOFF: {'PASS' if passes else 'FAIL'}  (wrong={n_wrong}<= {CUTOFF_MAX_WRONG}, "
          f"useful={useful_fraction:.0%}>= {CUTOFF_MIN_USEFUL_FRACTION:.0%})")

    if wrong:
        print("\n  sample WRONG (blocked):")
        for w in wrong[:3]:
            print(f"    - {w['stem'][:80]}  <- {w['reason'][:80]}")
    if correct_bad:
        print("\n  sample CORRECT-BUT-BAD (blocked):")
        for b in correct_bad[:3]:
            print(f"    - {b['stem'][:80]}  <- {', '.join(b['problems'])[:80]}")
    print()

    nulls = []
    if n_wrong:
        nulls.append(
            f"{n_wrong} generated card(s) were WRONG (unsupported by the source) and "
            "BLOCKED - a wrong fact is worse than no card, and one failure fails the batch."
        )
    if n_bad:
        nulls.append(
            f"{n_bad} card(s) were correct but bad teaching (vague/trivial/duplicate/leak) "
            "and BLOCKED."
        )
    _artifacts.write_artifact(
        "ai-card-check",
        {
            "title": "AI card check (generate from a cited source, then verify)",
            "spec": "spec 7f",
            "command": "just eval  (run_ai_card_check.py)",
            "model": ai._DEFAULTS["model"],
            "summary": [
                f"Generated {n} MC items from one cited source; gold set {len(gold)} Q/A.",
                f"Pre-registered cutoff: wrong <= {CUTOFF_MAX_WRONG} AND correct+useful "
                f">= {CUTOFF_MIN_USEFUL_FRACTION:.0%} of generated.",
                f"correct+useful (kept) **{n_useful}** ({useful_fraction:.0%}); "
                f"wrong (blocked) **{n_wrong}**; correct-but-bad/duplicate (blocked) "
                f"**{n_bad}**; malformed {n_malformed}.",
                f"Cutoff -> **{'PASS' if passes else 'FAIL'}**.",
            ],
            "table": {
                "headers": ["Count", "Value"],
                "rows": [
                    ["generated", n],
                    ["correct + useful (kept)", f"{n_useful} ({useful_fraction:.0%})"],
                    ["wrong (blocked)", n_wrong],
                    ["correct but bad / duplicate (blocked)", n_bad],
                    ["malformed (blocked)", n_malformed],
                ],
            },
            "metrics": {
                "generated": n,
                "useful": n_useful,
                "wrong": n_wrong,
                "bad": n_bad,
                "malformed": n_malformed,
                "useful_fraction": useful_fraction,
                "cutoff_max_wrong": CUTOFF_MAX_WRONG,
                "cutoff_min_useful": CUTOFF_MIN_USEFUL_FRACTION,
                "passes": passes,
            },
            "verdict": f"{'PASS' if passes else 'FAIL'}",
            "nulls": nulls,
        },
    )
    print("wrote artifact: docs/eval-artifacts/ai-card-check.json")


if __name__ == "__main__":
    main()
