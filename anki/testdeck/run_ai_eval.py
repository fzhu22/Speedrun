# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Run the REAL card-type classifier against the held-out gold set and print the numbers.

Unlike the committed unit test (which scores a perfect oracle to prove the harness), this
calls the live AI classifier through the proxy, so the accuracy / wrong-rate / baseline
figures are the real ones to paste into docs/ai-lane.md. With no token configured it
reports the AI-off (heuristic) path.

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

from anki.speedrun import ai, ai_eval  # noqa: E402
from anki.speedrun.cardtype import heuristic_classify  # noqa: E402


def main() -> None:
    key = ai.api_key()
    model = ai._DEFAULTS["model"]
    if key:
        client = ai.OpenAICompatibleClient(base_url=ai.base_url(), model=model, api_key=key)
        print(f"AI ON  -> base_url={ai.base_url()} model={model}")
    else:
        client = None
        print("AI OFF -> no token configured; the 'AI' column is the heuristic fallback")

    # Classify the AI once over the gold set (the model isn't perfectly deterministic,
    # so a single pass keeps accuracy and wrong-rate consistent), then compare against
    # the deterministic local baselines.
    gold = ai_eval.CARD_TYPE_GOLD
    n = len(gold)
    ai_correct = sum(1 for q, a, t in gold if ai.classify_card_type(client, q, a) == t)
    ai_acc = ai_correct / n if n else 0.0
    wrong_rate = (n - ai_correct) / n if n else 0.0

    vector_fn = ai_eval.make_vector_baseline(ai.FEWSHOT_EXAMPLES)
    heur_acc = ai_eval.evaluate(heuristic_classify)["accuracy"]
    vec_acc = ai_eval.evaluate(vector_fn)["accuracy"]
    leak = ai_eval.fewshot_leakage(ai.FEWSHOT_EXAMPLES)

    beats = ai_acc > heur_acc and ai_acc >= vec_acc
    print(f"held-out gold items : {n}")
    print(f"AI accuracy         : {ai_acc:.1%}   (wrong-rate {wrong_rate:.1%})")
    print(f"keyword baseline    : {heur_acc:.1%}")
    print(f"vector baseline     : {vec_acc:.1%}")
    print(f"cutoff {ai_eval.CUTOFF:.0%}          : {'PASS' if ai_eval.passes_cutoff(ai_acc) else 'FAIL'}")
    print(f"beats both baselines: {'yes' if beats else 'no'}")
    print(f"few-shot<->gold leak: {'CLEAN' if leak.clean else 'LEAK FOUND'}")


if __name__ == "__main__":
    main()
