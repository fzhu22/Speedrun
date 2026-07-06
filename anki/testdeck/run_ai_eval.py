# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Held-out eval of the card-type classifier + baseline comparison (spec AI gate / 7e).

Runs the classifier against the labeled held-out gold set and reports accuracy, wrong-rate,
the keyword and vector baselines side by side, the pre-registered cutoff, and the few-shot
<-> gold leakage check. Writes ``docs/eval-artifacts/ai-eval.json`` so the numbers in the
report are generated, not hand-typed.

- With an ``api-key`` / proxy token configured, the AI column is the real model
  (``gpt-4.1-mini``) - the decisive "AI beats a simpler method" evidence.
- With nothing configured it uses a deterministic OFFLINE stand-in (labelled), so the
  harness still runs and the artifact regenerates with no key.

Run from the anki/ dir:
    out\\pyenv\\Scripts\\python testdeck\\run_ai_eval.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ANKI = os.path.dirname(_HERE)
for _p in ("pylib", "out/pylib"):
    _full = os.path.join(_ANKI, _p)
    if _full not in sys.path:
        sys.path.insert(0, _full)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import _artifacts  # noqa: E402
from anki.speedrun import ai, ai_eval  # noqa: E402
from anki.speedrun.cardtype import heuristic_classify  # noqa: E402


def main() -> None:
    key = ai.api_key()
    if key:
        model = ai._DEFAULTS["model"]
        client = ai.OpenAICompatibleClient(base_url=ai.base_url(), model=model, api_key=key)
        ai_fn = lambda q, a: ai.classify_card_type(client, q, a)  # noqa: E731
        model_label = model
        ai_is_real = True
        print(f"AI ON  -> base_url={ai.base_url()} model={model}")
    else:
        ai_fn = ai_eval.reference_classifier()
        model_label = _artifacts.OFFLINE_MODEL
        ai_is_real = False
        print("AI OFF -> using the deterministic OFFLINE reference stand-in (labelled)")

    gold = ai_eval.CARD_TYPE_GOLD
    n = len(gold)
    ai_res = ai_eval.evaluate(ai_fn, gold)
    ai_acc = ai_res["accuracy"]
    wrong_rate = ai_res["wrong_rate"]

    vector_fn = ai_eval.make_vector_baseline(ai.FEWSHOT_EXAMPLES)
    heur_acc = ai_eval.evaluate(heuristic_classify, gold)["accuracy"]
    vec_acc = ai_eval.evaluate(vector_fn, gold)["accuracy"]
    leak = ai_eval.fewshot_leakage(ai.FEWSHOT_EXAMPLES, gold)

    cutoff_pass = ai_eval.passes_cutoff(ai_acc)
    beats = ai_acc > heur_acc and ai_acc >= vec_acc

    print(f"held-out gold items : {n}")
    print(f"AI accuracy         : {ai_acc:.1%}   (wrong-rate {wrong_rate:.1%})")
    print(f"keyword baseline    : {heur_acc:.1%}")
    print(f"vector baseline     : {vec_acc:.1%}")
    print(f"cutoff {ai_eval.CUTOFF:.0%}          : {'PASS' if cutoff_pass else 'FAIL'}")
    print(f"beats both baselines: {'yes' if beats else 'no'}")
    print(f"few-shot<->gold leak: {'CLEAN' if leak.clean else 'LEAK FOUND'}")

    svg = _artifacts.bar_svg(
        [("AI", ai_acc), ("keyword", heur_acc), ("vector", vec_acc)],
        title="Card-type classifier vs simpler baselines (held-out)",
        subtitle=f"model {model_label}; n={n}; cutoff {ai_eval.CUTOFF:.0%}",
        ymax=1.0,
        threshold=ai_eval.CUTOFF,
        threshold_label=f"cutoff {ai_eval.CUTOFF:.0%}",
    )
    _artifacts.write_svg("ai-eval", svg)

    nulls = []
    if not ai_is_real:
        nulls.append(
            "These are OFFLINE stand-in numbers (no api-key configured), kept for "
            "reproducibility. The decisive 'AI beats a simpler method' claim needs the real "
            "model - configure an api-key and re-run to record the gpt-4.1-mini row."
        )
    if ai_is_real and not beats:
        nulls.append(
            f"The AI ({ai_acc:.1%}) did NOT beat both baselines (keyword {heur_acc:.1%}, "
            f"vector {vec_acc:.1%}) this run - the keyword heuristic is already strong, so "
            "the gate correctly requires the AI to beat it before it is trusted."
        )

    _artifacts.write_artifact(
        "ai-eval",
        {
            "title": "AI card-type classifier: held-out eval + baseline comparison",
            "spec": "spec 7e / AI gate (evaluate before students see it; beat a baseline)",
            "command": "just eval  (run_ai_eval.py)",
            "model": model_label,
            "summary": [
                f"Held-out gold: {n} labeled items (disjoint from the few-shot prompt).",
                f"AI accuracy **{ai_acc:.1%}** (wrong-rate {wrong_rate:.1%}); "
                f"keyword baseline {heur_acc:.1%}; vector baseline {vec_acc:.1%}.",
                f"Pre-registered cutoff {ai_eval.CUTOFF:.0%} -> "
                f"{'PASS' if cutoff_pass else 'FAIL'}; beats both baselines: "
                f"{'yes' if beats else 'no'}.",
                f"Few-shot <-> gold leakage: {'CLEAN' if leak.clean else 'LEAK FOUND'} "
                f"(the prompt examples are not near-copies of the gold).",
                ("Real model row." if ai_is_real else
                 "OFFLINE stand-in row (deterministic; not a real LLM)."),
            ],
            "table": {
                "headers": ["Method", "Accuracy", "Note"],
                "rows": [
                    [f"AI ({model_label})", f"{ai_acc:.1%}", f"wrong-rate {wrong_rate:.1%}"],
                    ["keyword heuristic", f"{heur_acc:.1%}", "simple baseline"],
                    ["vector (2-shot NN)", f"{vec_acc:.1%}", "no-embedding stand-in"],
                ],
            },
            "metrics": {
                "n": n,
                "ai_accuracy": ai_acc,
                "wrong_rate": wrong_rate,
                "keyword_accuracy": heur_acc,
                "vector_accuracy": vec_acc,
                "cutoff": ai_eval.CUTOFF,
                "cutoff_pass": cutoff_pass,
                "beats_baselines": beats,
                "leakage_clean": leak.clean,
                "ai_is_real": ai_is_real,
            },
            "chart": "ai-eval.svg",
            "verdict": (
                f"{'PASS' if (cutoff_pass and beats) else 'GATED'} "
                f"({'real model' if ai_is_real else 'offline stand-in'})"
            ),
            "nulls": nulls,
        },
    )
    print("wrote artifact: docs/eval-artifacts/ai-eval.json + ai-eval.svg")


if __name__ == "__main__":
    main()
