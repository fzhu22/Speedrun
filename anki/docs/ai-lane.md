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
`CARD_TYPE_GOLD`, 21 items) kept disjoint from the 2 few-shot prompt examples. Before the
AI classifier is used, `run_classifier_gate_eval` runs it against that gold set and the AI
label is trusted **only if it clears the pre-registered cutoff (accuracy >= 0.80) AND
beats the keyword heuristic** it would otherwise fall back to. The verdict is cached per
model in synced config. If it fails, classification uses the deterministic heuristic. So a
weak model is blocked, not shipped.

## Numbers (real model, via the hosted proxy, `gpt-4.1-mini`)

Reproduce with: `out\pyenv\Scripts\python testdeck\run_ai_eval.py`

| Method | Accuracy on the 21-item held-out gold | Notes |
| --- | --- | --- |
| AI classifier (`gpt-4.1-mini`) | ~86-100% | not perfectly deterministic even at temperature 0 |
| Keyword heuristic (baseline) | 90.5% | deterministic |
| Vector baseline (bag-of-words cosine) | 61.9% | deterministic |
| Cutoff (0.80) | PASS | |
| Few-shot <-> gold leakage | CLEAN | k-gram containment check |

**Honest read:** the AI reliably beats the vector baseline, but the keyword heuristic is
already strong (90.5%), so the AI does not always beat it. That is exactly why the gate
requires the AI to beat the heuristic before it is used - on this task it often falls back
to the (free, deterministic) heuristic rather than pay for a model that is not clearly
better. This is the honesty rule applied to AI: we built the check that could show the AI
adds little, and it sometimes does.

## Leakage check (7e)

`fewshot_leakage` compares the prompt's few-shot examples against the gold set with a
k-gram shingle-containment test (`validation.leakage_check`, threshold 0.8) and reports
CLEAN, so the gold set cannot be inflated by prompt overlap.

## AI off

AI is off whenever the toggle is off or no token is configured. In that state every
operation uses its deterministic path (heuristic classify / template hint), and the app
still produces all three scores. For local development, setting `SPEEDRUN_AI_KEY` to a
real OpenAI key bypasses the proxy.
