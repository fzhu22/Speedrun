# The Speedrun AI lane (what it is, why, and how it is checked)

Short note for the Friday deliverable: what AI Speedrun uses, why, what it deliberately
does not do, and the eval that runs before any AI output is trusted.

## What the AI does

Two narrow, assistive jobs - and nothing else:

1. **Card-type classification.** Labels a card `declarative` (a fact to recall) or
   `application` (needs reasoning/transfer). This only decides whether missing a card is
   worth an in-review disconfirmer prompt. Code: `pylib/anki/speedrun/ai.py`
   (`classify_card_type_with_source`).
2. **Disconfirmer authoring hints.** A one-line Socratic hint ("what single fact would
   flip this answer?") to help a student *write their own* disconfirmer. Code:
   `disconfirmer_hint`.

## What it deliberately does NOT do (scoped out)

- **No card generation / authoring.** The AI never writes card fronts, backs, or the
  disconfirmer, and never grades. This is a stated position in `brainlift-v6.md` (AI card
  authoring is out of scope); the deterministic heuristic + template cover those paths.
- **No effect on the three scores.** Memory / Performance / Readiness come entirely from
  FSRS + the Rust engine. AI is off the scoring path by construction, so the app gives the
  same scores with AI on or off.

## Every AI output carries a named source (provenance)

- **Hints:** returned with `Provenance(source="AI:<model>")` (or `source="template"` when
  AI is off), shown in the authoring UI.
- **Classifications:** persisted on the card as a `speedrun_ctype_src::AI_<model>` tag
  (or `speedrun_ctype_src::heuristic`) next to the `speedrun_ctype::<type>` tag, so every
  label traces back to who produced it. Code: `pylib/anki/speedrun/cardcache.py`.

## The eval, run before any AI label is trusted (enforced cutoff)

The classifier is gated on a held-out gold set (`pylib/anki/speedrun/ai_eval.py`,
`CARD_TYPE_GOLD`, 37 items) kept disjoint from the few-shot prompt examples. Before the
AI classifier is used, `run_classifier_gate_eval` runs it against that gold set and the AI
label is trusted **only if it clears the pre-registered cutoff (accuracy >= 0.80) AND
beats the keyword heuristic** it would otherwise fall back to. The verdict is cached per
model in synced config. If it fails, classification uses the deterministic heuristic. So a
weak model is blocked, not shipped.

## Numbers (real model, `gpt-4.1-mini`)

Measured with the real model (`out\pyenv\Scripts\python testdeck\run_ai_eval.py`; the eval
talks to OpenAI directly via `SPEEDRUN_AI_KEY`, while the running app reaches the same model
through the hosted proxy). Every figure is regenerated into `docs/eval-results.md`.

| Method | Accuracy on the 37-item held-out gold | Notes |
| --- | --- | --- |
| AI classifier (`gpt-4.1-mini`) | 86.5% | wrong-rate 13.5%; real model |
| Keyword heuristic (baseline) | 91.9% | deterministic |
| Vector baseline (bag-of-words cosine) | 59.5% | deterministic |
| Cutoff (0.80) | PASS | AI clears the accuracy bar |
| Beats both baselines | NO | AI 86.5% < keyword 91.9% this run |
| Few-shot <-> gold leakage | CLEAN | k-gram containment check |

**Honest read:** the AI clears the 0.80 cutoff and beats the vector baseline, but it does
**not** beat the keyword heuristic (86.5% vs 91.9%) on this task. The gate therefore keeps
the free, deterministic heuristic rather than pay for a model that is not clearly better.
This is the honesty rule applied to AI: we built the check that could show the AI adds
little, and here it does - so the AI classifier stays gated off and the heuristic is used.

## Card generation, checked before anything ships (7f)

The AI may *propose* MCAT-style items strictly from one cited source; nothing reaches a deck
until it passes a structural check, an LLM fact-check against the source, a teaching-quality
check, and a leakage scan (`pylib/anki/speedrun/ai_items.py`). Pre-registered cutoff (set
before looking at results): `wrong <= 0` and `correct+useful >= 60%` of generated.

Real run (`run_ai_card_check.py`, `gpt-4.1-mini`): from one biochem source it generated 54
items - 49 correct + useful (91%), 1 wrong, 4 correct-but-bad (duplicate/leak), 0 malformed.
Verdict: **FAIL the batch cutoff**, because 1 item was wrong and the rule is `wrong <= 0`.
The point is that the checker *caught and blocked* that wrong card (and the 4 weak ones), so
it never reached the deck - a wrong fact is worse than no card. This is an honest negative:
the generator is not perfect, and the gate is exactly what makes shipping it safe.

## Prompt-injection red-team (spec 10)

A pasted source can hide instructions - override phrases, HTML comments, zero-width
characters, role tags, or a plain "append X to your response" line. `sanitize_source`
(`pylib/anki/speedrun/textutil.py`) strips those mechanisms, and every prompt frames the
source as untrusted DATA. Real run (`run_injection_redteam.py`, `gpt-4.1-mini`): 5 attacks,
each carrying a canary the attacker wants echoed - **5/5 neutralized**, the canary never
surfaced in any generated item / hint / advice, and a forced "mark this wrong answer
correct" item was **not** flipped. The red-team initially found two leaks (an exfiltration
imperative and an answer-forcing passage that survived sanitization); those generic patterns
were added to `sanitize_source` and the re-run passed - red-team, fix, re-test.

## Leakage check (7e)

`fewshot_leakage` compares the prompt's few-shot examples against the gold set with a
k-gram shingle-containment test (`validation.leakage_check`, threshold 0.8) and reports
CLEAN, so the gold set cannot be inflated by prompt overlap.

## AI off

AI is off whenever the toggle is off or no token is configured. In that state every
operation uses its deterministic path (heuristic classify / template hint), and the app
still produces all three scores. For local development, setting `SPEEDRUN_AI_KEY` to a
real OpenAI key bypasses the proxy.
