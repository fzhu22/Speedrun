# MCAT Anki — Learning-Science Features — Experts & Facts (DOK 1)

## Core question
**Which concrete, learning-science-grounded features and engine changes should be built into a fork of Anki to materially improve MCAT preparation — pushing past recognition-level recall toward exam-style application, reasoning, and transfer — and which proposed features are likely to backfire or be cargo-cult?**

Sibling note: this is a SIBLING BrainLift to `brainlifts/mcat-anki-study-app/` (the three-score honesty tool). It REUSES that run's citation-checked DOK 1 facts and validated DOK 3 insights as high-authority, **pre-gated** input (cited as "parent BrainLift: mcat-anki-study-app"; not re-gated), but its FOCUS is the **pedagogical FEATURE / implementation layer** — what to build into Anki and how, grounded in learning science — NOT the scoring/readiness/honesty architecture. Fixed givens carry over (fork Anki, real Rust change, AGPL, MCAT-specific). The deliverable is a depth-gated menu of candidate-valid, feature-level SPOVs (which features to build, how to implement them in Anki, and which to avoid).

## First-principles map (feature-focused; seeds the research wave)
1. **Scheduling & spacing AS FEATURES** — FSRS desired-retention tuning (per-topic/high-yield weighting), load balancing, expanding vs uniform spacing, advance/postpone, same-day re-review, exam-date-aware scheduling. *Implementation:* FSRS params, Anki custom scheduling, fsrs-rs hooks.
2. **Retrieval-practice variants AS CARD/FEATURE TYPES** — cued vs free recall, generative/production cards, typed/short-answer, application prompts vs recognition cloze, "explain-why" cards, test-potentiated new learning.
3. **Transfer & desirable difficulties AS FEATURES** — interleaving/mixing across topics & subjects, contextual interference, surface-form variability, worked-example→problem fading, concept-discrimination drills (+ boundary conditions: interleaving heterogeneity, expertise reversal).
4. **CARS / reading-reasoning FEATURES** — passage-attached practice, daily-passage mode, no-content reasoning drills, timed passage sets, "reasoning beyond the text."
5. **Elaboration, dual coding, self-explanation FEATURES** — image occlusion, diagram/labeled cards, self-explanation/elaborative-interrogation prompts, concept maps, teach-back.
6. **Metacognition & calibration FEATURES** — confidence/JOL ratings, predicted-vs-actual feedback, calibration dashboards, "are you ready" check-ins (feature-level; the parent owns the honesty/score architecture).
7. **Error-driven & feedback FEATURES** — mine missed QBank/passage items into cards, error-type tagging, targeted resurfacing of weak concepts, "lapse → reformulate" prompts.
8. **Motivation, habit & cognitive-load FEATURES** — session structuring, daily load caps, streaks/gamification (with cautions), card atomicity/limits, overload prevention, notifications.
9. **The Anki implementation substrate** — note types & card templates, cloze, custom scheduling (JS/Rust), the add-on API, the EXISTING add-on landscape (Image Occlusion, Cloze-Overlapper, "mix"/interleaving add-ons, Review Heatmap, FSRS Helper, Speed Focus, Pop-up Dictionary, etc.), AnkiDroid/iOS parity, AGPL — so features are built on what exists, not reinvented.

## Pre-gated input from the parent BrainLift (mcat-anki-study-app) — already citation-checked; DO NOT re-gate
Researchers/synthesizer should BUILD ON these and go deeper/newer on the feature layer rather than re-deriving them:
- **Transfer is conditional, not automatic** (Pan & Rickard 2018): testing→transfer d=0.40; **0.58 WITH response congruency, 0.28 without, ~0 after bias-correction when moderators absent**; moderators = response congruency, elaborated retrieval, high initial accuracy. → features must ENGINEER the moderators or transfer collapses.
- **Interleaving works but is heterogeneous** (Brunmair & Richter 2019): overall g=0.42, paintings 0.67, math 0.34, **words −0.39, expository ns**; mechanism = discriminative contrast (works when categories are similar/complex). → interleaving features must be targeted; risky for verbal/CARS-like material.
- **Retrieval practice g≈0.50** (Rowland via Karpicke; 159 effect sizes/61 studies); **spaced retrieval g=0.74** (Latimier); expanding ≈ uniform (g=0.034).
- **Far transfer ~0 under controls** (Sala & Gobet; Sala 2019 "true variance equaled zero"). → engineer near-transfer; don't expect generic transfer.
- **Desirable difficulties can become UNdesirable** under high element interactivity / for advanced learners (Chen/Sweller; Kalyuga expertise-reversal). → difficulty features must be load- and expertise-aware.
- **"Feel good in Anki, bad in passages" = recognition-based cards;** prebuilt decks over-rely on cloze → "pattern recognition rather than true understanding" (Jack Westin; Memm). → application/transfer card design is the core feature problem.
- **CARS requires no content knowledge** (AAMC) → memory/recall features are structurally near-useless for CARS; CARS needs passage/reasoning features.
- **FSRS** = D/S/R model (R=exp(−t/S)); default since Anki 23.10; **fsrs-rs v6 adds per-card desired retention + cost-conditioned policy; Anki 26.05 exposes decay + desired retention to custom scheduling**; "20–30% fewer reviews" is SIMULATION not RCT; **Hard-misuse corrupts scheduling** (Hard counts as Pass).
- **Adaptive item scheduling up to 40% more recalled** (Eglington & Pavlik 2020) — but it changes the data-generating process (parent Insight 7/12).
- **Metacognition is poorly calibrated** (Dunning-Kruger); **calibration training helped overconfident students +4.1%** (Lee 2025); practice tests improve metacognitive accuracy (Rivers 2022).
- Parent's most relevant validated insights: I1 (construct separation; surface-perturbation transfer test), I6 (blended is harmful; section-aware; CARS proof), I7 (scheduler↔scorer feedback loop), I8 (severity-weighted coverage), I11 (label-starved/feedback-coupled launch). Full set: `../mcat-anki-study-app/02b-insights-validated.md`.

## Pooled DOK 1 facts (new, feature-layer)
Full DOK 1 fact sets (per source, links + tags) live in the six raw lane files (all captured):
- `raw-foundations.md` — each LS technique as an implementable feature: design parameters + boundary conditions (generation, retrieval+feedback, self-explanation principle-direction, dual coding/coherence, contextual interference, worked-example fading, spacing horizon-dependence, JOL limits, cognitive-load/expertise-reversal constraints).
- `raw-advocate.md` — evidence FOR features (self-explanation g=.55; user-generated>premade d=.45/.29; testing g=.54 + feedback; interleaved math d=.83; adaptive spacing +40%; personalized review +16.5%; spaced medical cases/images d=1.01 + transfer; calibration AI +8.9%; Anki↔Step-1 observational ~1pt/1,700 cards).
- `raw-adversary.md` — failure modes (gamification/streaks overjustification d=−0.40 + streak-anxiety; interleaving words g=−0.39; expertise reversal d=−0.428; seductive details negative; self-explanation null without scaffolding; over-cloze=recognition/illusion of competence; choice overload; DKT≈baselines; LLM faulty items; Anki ease-hell/leech/pile).
- `raw-cartographer.md` — the implementation substrate + "already-built-in vs genuine-gap" map (Image Occlusion/FSRS/Auto-Advance/burying/new-review-interleave built-in; custom scheduling = global JS; v3 can't be monkey-patched; rslib/fsrs-rs; AnkiDroid/AnkiMobile add-on constraints; front-side cloze constraint; gaps = concept-aware interleaving / metacognitive calibration / self-explanation prompting / per-deck scheduling / error-driven remediation).
- `raw-frontier.md` — how top scorers build application cards; #1 request = exam-date scheduling; CARS = wrong tool for Anki; AnkiHub already shipping AI; the recognition-vs-application critique.
- `raw-edge.md` — 2025-2026: LLM self-explanation +11.9pp transfer-explanation; "faster completion, less learning" (−17% unassisted); contextual-bandit sequencing on skill gain; FSRS-6/-7; existing AI add-ons (MyAnswerChecker free-response self-grading, AnkiAIUtils failure-triggered elaboration); UWorld UAsk / RemNote.

Plus the parent BrainLift's already-gated facts (transfer conditionality, interleaving heterogeneity, FSRS internals, CARS no-content, etc.) — see the pre-gated digest above and `../mcat-anki-study-app/`.

## Candidate experts (pooled, deduped)
**Learning science / memory / transfer:** Jeffrey Karpicke (https://learninglab.psych.purdue.edu/) · Henry Roediger III · Robert & Elizabeth Bjork (https://bjorklab.psych.ucla.edu/) · John Dunlosky · Doug Rohrer (http://uweb.cas.usf.edu/~drohrer/) · Steven C. Pan (https://sc-pan.github.io/) · Pooja Agarwal / The Learning Scientists (https://www.retrievalpractice.org/ , https://www.learningscientists.org/) · Andrew Butler · Shana Carpenter · Michelene Chi · Alexander Renkl · Bethany Rittle-Johnson.
**Cognitive load / multimedia / metacognition:** John Sweller · Slava Kalyuga · Richard Mayer · Asher Koriat · Nelson & Narens (architecture).
**Motivation:** Edward Deci & Richard Ryan (https://selfdeterminationtheory.org/).
**Scheduling / KT / adaptivity:** Philip Pavlik Jr. · Michael Mozer & Robert Lindsey · Théophile Gervet / Ken Koedinger · B. Price Kerfoot (spaced education in medicine) · HaeJin Lee (AI calibration).
**Anki / FSRS ecosystem (practitioners):** Damien Elmes "dae" (https://github.com/ankitects/anki) · Jarrett Ye "L-M-Sherlock" (https://github.com/l-m-sherlock) · Expertium (https://expertium.github.io) · glutanimate (https://glutanimate.com) · Jonathan Schoreels "JSchoreels" (FSRS-7) · AnkiDroid team / David Allison · The AnKing (Nick Flint et al., https://www.theanking.com).
**MCAT practitioners:** Jack Westin (https://jackwestin.com/) · MileDown / JackSparrow2048 / Mr. Pankow (deck creators).

## Child-topic flags
6 candidates raised; **0 children spawned** — all resolved inline (core question by the cycle guard; gamification as an inline SPOV lane; substrate as an inline constraint; sequencing/difficulty/interleaving-axis as feature sub-questions). See `child-brainlifts.md`.
