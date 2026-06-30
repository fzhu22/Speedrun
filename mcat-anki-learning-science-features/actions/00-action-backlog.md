# create-actions — Action Backlog + Execution Map (MCAT Anki Learning-Science Features)

Source BrainLift: `brainlifts/mcat-anki-learning-science-features/brainlift.md` (12 SPOVs: 1 Validated / 3 Strong / 8 Weak). Sibling: `mcat-anki-study-app` (scoring/honesty — out of scope here). Goal: translate the feature SPOVs into a concrete, sequenced, feasibility-tested **feature build plan**. Project context (given): a fork of Anki (one shared Rust engine, AGPL, MCAT), small team, hackathon-style cadence — so feasibility tests weight "buildable by a small team soon," and a 3-day-safe subset matters.

## Actions (the features to build) — numbered
- **A1 — Two-tier foundation (Validated SPOV 4):** desktop "prepare" tier (Python/Rust over `rslib`, sees whole collection) + cross-platform "review" tier (card-template JS on AnkiMobile/AnkiDroid) + a small syncable artifact channel. *Foundation — everything else rides on it.*
- **A2 — Student-authored miss→card scaffold with a DISCONFIRMER field (SPOV 1):** ingest a missed item, perturb surface, prompt the principle + "what one fact would flip this?", student authors the card; refuse blank/answer-restating disconfirmers; NO AI auto-authoring of the body.
- **A3 — Deep-structure SORT verification gate (SPOV 2):** principle-sharing card families + held-out "which two share the principle?" sort that unlocks a "transfer-trained" status flag.
- **A4 — Curated discrimination-drill library (SPOV 3):** human-reviewed confusable-set concept graph (acids/bases vs buffers; inhibition types; SN1/SN2) → drills forcing the discriminating mechanism + a differing consequence; opt-in after baseline; science-only.
- **A5 — Support-fading difficulty engine (SPOV 10):** per-concept-family expertise estimate + fade ladder (worked example → completion → open prediction → discrimination), fading toward the rejected alternative; high-element content only.
- **A6 — MC feedback + error-classification engine (SPOV 6):** commit-then-reveal MC/application card type, source-backed distractor rationales, forced error-type tagging (content/reasoning/trap/timing), ONE targeted remediation card (load-managed).
- **A7 — Confidence capture + high-confidence-wrong router (SPOV 7):** post-answer confidence, flag high-confidence-wrong, capture the false model, route to a misconception drill; NO vanity dashboard, NO confidence-only FSRS change.
- **A8 — Exam-date desired-retention RAMP (SPOV 11):** test-date input → desktop-prepared per-card DR target ramped toward test day (high-yield/weak first, capped <97%), applied via the exposed decay/DR custom-scheduling surface; NOT a cram override.
- **A9 — Falsifiable metrics layer (SPOV 5):** logging + item-discrimination (point-biserial) + a PFL proxy (trials-to-next-concept); refuse perturbed-accuracy/streaks/completion% as EVIDENCE of learning.
- **A10 — AI lane: severe-test generator + crutch kill-switch (SPOV 9):** AI generates counterexamples/boundary/disconfirmer prompts against a HUMAN-authored key (never final grader); provenance/trust record; an assisted-vs-unassisted A/B gate that kills crutch features.
- **A11 — CARS product decision (SPOV 12):** build a separate timed-passage + reasoning/error-pattern module OR integrate (Jack Westin); NOT a primary flashcard deck / not a CARS card-accuracy KPI.
- **A12 — Non-distorting motivation layer (SPOV 8):** private mastery/coverage, recovery streaks, effort-credit for hard items; EXCLUDE public leaderboards + loss-framed streaks.

## Execution map (work-streams per action) — seeds the research wave
- **A1:** fork build-from-source (given); `rslib`/Python prepare-tier scaffolding; syncable-artifact channel design (tags vs ≤100-byte `customData` vs companion store/AnkiHub-style sync); card-template JS review runtime; cross-platform parity harness (desktop + AnkiDroid + AnkiMobile); sync-conflict + schema-migration handling; AGPL packaging.
- **A2:** miss ingestion (UWorld/AAMC QID strings, paste, image OCR?); surface-perturbation generator; note-type/template with disconfirmer field; authoring UX; disconfirmer validation; provenance.
- **A3:** concept-family tagging source; held-out split logic; sort-task template (JS); status-flag storage (within customData/tags limits); item authoring.
- **A4:** the curated confusable-set content (who authors it, how big); concept-graph data model; drill generator; mechanism/consequence free-response capture + light checking.
- **A5:** per-family expertise estimator (success/transfer-item tracking); worked-example/fading content authoring; ladder state machine; scoping classifier (high-element vs declarative).
- **A6:** commit-then-reveal MC card type; distractor-rationale sourcing/authoring; error-classification UI; remediation queue + load cap.
- **A7:** confidence-capture UI (post-commit); high-confidence-wrong detection; false-model menu; misconception-drill routing.
- **A8:** test-date input + ramp-curve math (desktop); per-card DR write path (exposed surface / deck buckets / customData); workload cap; interval-corruption guard.
- **A9:** event logging schema; point-biserial pipeline; PFL proxy pipeline; honest dashboard (no streaks-as-evidence); held-out eval harness.
- **A10:** LLM choice + API (cost); severe-test prompt design; human-key authoring; provenance/trust record; prompt-injection defense; the assisted/unassisted A/B harness.
- **A11:** build-vs-integrate decision criteria; (build) passage delivery + timer + error-pattern analytics + passage content/licensing; (integrate) Jack Westin/partner handoff.
- **A12:** mastery/coverage progress UI; recovery-streak logic; effort-credit weighting; (explicit non-build: leaderboards/loss-streaks).

## Anti-patterns (rejected by the BrainLift — NEVER re-propose; injected into every spawn)
From `rejected.md` + Out-of-Scope + the dropped decoy:
1. **AI auto-authoring of card bodies / AI-generated score-bearing items** — REJECTED (BMC "all faulty" + kills the generation effect). AI may only generate severe TESTS against a human key, never the card body a student should author or any graded content.
2. **Live on-device semantic queue re-ranking** — IMPOSSIBLE per Anki source (proto `{deck_name,seed}`; ≤100-byte customData; queue built backend-side; JS runs at answer-time). No step may claim the phone reorders the queue by concept in real time → use the two-tier (desktop-prepare) pattern.
3. **Generic "interleave/shuffle" toggle or AUTO-TAGGED concept clusters** — REJECTED. Discrimination drills must be curated/human-reviewed and science-only (never CARS/verbal).
4. **Global "hard mode" / difficulty slider** — REJECTED (expertise reversal). Difficulty = per-family support-fading after demonstrated success.
5. **Public leaderboards / ranking / loss-framed streak penalties** — REJECTED (punish error-confrontation). Only non-distorting motivation.
6. **AI grading explanation QUALITY as authoritative** — REJECTED (Goodhart; resemblance ≠ correctness). AI generates criticism; humans/keys grade.
7. **Confidence dashboards / confidence-only FSRS interval changes** — REJECTED. Confidence is used ONLY to route high-confidence-wrong.
8. **Perturbed-item accuracy / streaks / deck-completion % as EVIDENCE of learning** — REJECTED. Use item discrimination + PFL.
9. **A "CARS content deck" / CARS card-accuracy as a KPI** — REJECTED. CARS = passages + error-pattern, separate or integrated.
10. **Naive cram override (max-interval hack / filtered-deck pileup)** — REJECTED. Exam-date = a DR ramp over FSRS.
11. **Re-adding Anki built-ins (Image Occlusion, FSRS, Auto-Advance) as "features"** — non-redundant only; build the gaps.
12. **The decoy:** "auto-generate a full-coverage AI deck + FSRS is all you need" — REJECTED (coverage ≠ application).

## Honest ceiling carried from the BrainLift
Only A1's substrate constraint is *established*; every other feature's *efficacy on MCAT scores* is an observational BET (Anki↔exam non-randomized; the one applied anchor, Wothe Step-2-CK, is null). So Feasibility Test 3 (efficacy) will mostly land FEASIBLE-PLAUSIBLE ("buildable; efficacy pends a pilot"), and each feature should ship with the volume-matched RCT / measurement that would prove it.
