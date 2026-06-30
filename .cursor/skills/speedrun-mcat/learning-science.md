# Learning-Science Positions & Anti-Patterns

A compact index of `mcat-anki-learning-science-features/brainlift.md` (the SPOV menu) and `actions/action-plan.md` (the build plan). **Read the source files before building a feature** — this is the cheat sheet, not the authority.

## The one Validated position (the architecture spine)

**SPOV 4 — every concept-aware feature must be two-tier: desktop "prepare" -> cross-platform "review."** A desktop tier (Python/Rust, sees the whole collection) emits small syncable artifacts (tags / tiny `customData`); the review tier is card-template JavaScript that runs on stock AnkiMobile + AnkiDroid. Live on-device semantic queue re-ranking is code-verified impossible (see anki-brownfield.md). Any "your phone reorders your queue by concept in real time" promise is vaporware. The **authoritative write path is desktop-prepare reconcile**; mobile-at-answer writes are an Android-only, version-contingent optimization; iOS writes nothing synced.

## Strong / flagship feature bets

- **SPOV 1 (flagship)**: student-authored "miss -> card" scaffold whose required field is a **DISCONFIRMER** ("what one fact would flip this answer?"). The student authors the body — **no AI auto-authoring** (forfeits the generation effect and ships faulty LLM items).
- **SPOV 2**: a card earns "transfer-trained" status only by passing a **held-out deep-structure SORT** ("which two share the principle?"), not by perturbed-item accuracy alone.
- **SPOV 3**: a **curated, human-reviewed discrimination-drill library** for known MCAT confusable sets (acids/bases vs buffers; competitive/non-competitive/uncompetitive inhibition; SN1/SN2) — NOT a generic interleave toggle, NOT auto-tagged, science-only (not CARS/verbal).
- **SPOV 10**: difficulty **fades support within a per-concept-family expertise estimate** — NOT a global "hard mode," and not on declarative recall (expertise-reversal effect).
- **SPOV 5**: instrument the fork's own theory with **item discrimination (point-biserial) + a Preparation-for-Future-Learning proxy**; refuse perturbed-accuracy / streaks / completion% as *evidence of learning* (fine as ops/UX metrics).

Deferred bets: MC distractor-feedback + error-classification engine (SPOV 6), committed-answer confidence -> high-confidence-wrong router (SPOV 7), exam-date desired-retention ramp over FSRS (SPOV 11), AI severe-test generator + crutch kill-switch (SPOV 9), non-distorting motivation (SPOV 8), CARS product decision (SPOV 12).

## Hard anti-patterns — never ship

1. AI authoring the card body. 2. On-device queue re-rank. 3. Auto-tagged concept clusters. 4. Global hard-mode / difficulty slider. 5. Public leaderboards or loss-framed streaks. 6. AI as authoritative grader. 7. Confidence dashboard or confidence-only FSRS interval change. 8. Accuracy/streaks/completion% as proof of learning. 9. CARS as a primary deck or its KPI. 10. Naive cram override that corrupts FSRS. Also: do not re-add Anki built-ins as "features."

## The observational ceiling (honesty)

The "better Anki features -> MCAT gains" link is **OBSERVATIONAL**: the Anki<->exam literature is non-randomized, and the one applied anchor (Wothe et al., Step-2-CK, 252.5 vs 247.0, p=0.440) is **null**. So present every transfer/application/readiness feature's efficacy as a **bet**, with a **volume-matched RCT on unseen MCAT-style items** as the resolver — never as a measured result. SPOV 4 is the exception (settled by Anki's source, no experiment needed).

## The study-feature test (spec 8)

Pick one learning-science feature, write its one-sentence hypothesis and failure condition up front, then compare three builds on the same learners / questions / time budget: (1) full app, (2) app with that one feature off (ablation), (3) plain unmodified Anki (baseline). Report a range and report nulls — "interleaving made no difference here" is a real, scoring result.

## Critical path / first move (action-plan.md)

A1-S0 write-parity spike (what can stock review-tier JS persist + sync, per client) -> A1-S2 desktop "prepare" authoritative write path -> A1-S3 stock-client review runtime -> {flagship miss->card, sort gate, discrimination drills} + metrics. The **fork build runs in parallel, off the critical path** (it exists for branding + the genuine Rust change, not the review tier). The exam-date DR ramp (A8) is BLOCKED pending its curve/cap policy. Content authoring is the long pole — start day 1.
