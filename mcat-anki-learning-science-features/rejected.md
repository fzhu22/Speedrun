# Reject Log — MCAT Anki Learning-Science Features

Every DOK 1–4 item cut at a gate, with the concrete reason. Format: `- <item> — REJECTED (<stage/test>): <specific reason>`.

## DOK 1 — Facts cut by the citation gate (Step 1b)
**0 facts dropped.** The feature-layer corpus verified unusually clean (all priority effect sizes, Anki substrate facts, and 2026 preprints/PRs resolved to primary sources and matched). 5 FIXes applied (no drops):
- "Rana et al. 2026" Anki review → **Frappa et al. 2026** (Med Sci Educ 36:1015–1025) — author miscite (raw-advocate.md).
- "Metacognitive Overload!" → **McCarthy et al. 2018** (McNamara senior author); softened the "removed in future versions" phrasing (raw-adversary.md).
- Rowland 2014 — clarified g=0.54 is the UNWEIGHTED mean; headline WEIGHTED ES = g=0.50 (the load-bearing "g=0.03 without feedback ≤50%" is exact) (raw-advocate.md).
- Step-2-CK null → cite the primary study **Wothe et al.** (252.5 vs 247.0, p=0.440) not the practitioner relay (raw-frontier.md).
- LearnLM/Eedi — keep 76.4% (preprint); Eedi press cites 82.3% — don't mix (raw-edge.md note).
- All Anki↔exam figures (Deng/Gilbert/Winter/Frappa) confirmed VERIFIED **and observational/non-randomized** (association, not proven causation).

## DOK 2 — Summary/Knowledge-Tree claims dropped for lacking a verified fact
*(pending)*

## DOK 3 — Insights cut/demoted in the critique round (Step 3)
**0 insights rejected outright; sharpened/demoted (4 isolated critics: 3 Claude + 1 GPT):**
- "Card-construction COMPILER" (Insight 1) — DEMOTED to a student-authored scaffold. REASON (skeptic + red-teamer + cogsci): automating the card body forfeits the generation effect (the very thing that works, Pan d=0.45/0.29) AND collapses into the faulty AI card-gen the corpus rejects (BMC "all faulty"); "killer feature" → "highest-leverage bet" (cards→MCAT link is observational + Step-2-CK null).
- "'More reviews' is a false lever" (Insight 2) — CUT as overstated. REASON (skeptic): volume/spacing DO move memory (Donoghue & Hattie d=0.85); scoped to application/transfer only.
- Application-card TRANSFER as an effect (Insight 3) — DEMOTED to a testable hypothesis. REASON (all): the corpus's own boundaries (parent SPOV 11 WEAK; words −0.39 / expository ns / far-transfer ~0) put it in a contested regime; added a deep-structure-sort verification probe.
- Interleaving via AUTO-TAGGING + Rohrer math d=0.83 as the MCAT effect (Insight 4) — CUT. REASON (skeptic + red-teamer): auto-tagging re-imports faulty-AI risk; math RCT effect can't be imported as MCAT magnitude → curated confusable sets + "mechanism untested for MCAT content."
- "A CARS deck teaches false confidence" (Insight 5) — SOFTENED. REASON (skeptic): unsourced inference → "offers no diagnostic signal for the limiting reasoning/timing failure."
- "Adaptive difficulty" (Insight 6) + "feedback helps / every card needs explanation" (Insight 7) + "AI should scaffold not author" (Insight 10) — RESCUED FROM TRUISM. REASON (skeptic + red-teamer): platitudes; foregrounded the spikes (fade toward the rejected alternative after ≥2 unaided successes; MC is net-NEGATIVE without distractor feedback; AI must GENERATE criticism, never GRADE — cogsci; + the unassisted crutch-effect risk).
- **"Reject gamification" (Insight 9) — FAILED as stated → FIXED.** REASON (red-teamer + skeptic): one-sided evidence (omitted net-positive metas g≈.46–.82) + a Deci category-slip (overjustification is about tangible rewards, not all gamification). Narrowed to the mechanism (gamification that punishes error-confrontation), keeping non-distorting gamification.
- AI permission to GRADE explanation quality (Insight 10) — CUT. REASON (cogsci): a statistical model certifies only resemblance → Goodhart; restricted AI to generating checkable criticism against a human-authored key.

## DOK 4 — SPOV candidates cut by the SPOV Testing Protocol (Step 6) + decoy result
- **DECOY ("auto-gen full-coverage AI deck on FSRS = all you need")** — REJECTED (Test 2, FATAL): crux "an auto-generated full-coverage AI deck on FSRS raises unseen MCAT performance ≥ application/discrimination features at equal time" is REFUTED (coverage ≠ application; AI medical items "all faulty" per BMC; the feature→MCAT link is observational + the Wothe Step-2-CK null). Both cold testers (Test 1) rated it 2/10. **Protocol self-check PASSED.**
- **SPOV 12 absolutist version ("NEVER ship a CARS deck / ZERO diagnostic signal")** — REJECTED as stated (Test 2): "zero diagnostic signal" is too strong (tone/fallacy/trap-type micro-cards could correlate as a verbal-prep proxy) and the wording is retreatable (relabel any working deck as "strategy support"). **KEPT in SCOPED form** (Weak): "don't ship CARS as a PRIMARY flashcard deck or use CARS card-accuracy as the KPI; use timed passages + error-pattern analytics; optional vocab/taxonomy micro-cards only."
- **No other real candidate dropped at Test 1** (11, 12 = WEAK but advanced) **or Test 2** (all yielded a real crux; the 8 WEAKs carry closable escape hatches, hardened in final wording).
- **Test 3 outcome: 0 cruxes REFUTED → 0 additional drops.** 12/12 kept and tiered: **1 Validated** (SPOV 4 — Test 3 HOLDS-ESTABLISHED via Anki proto/rslib source: stock custom-scheduling JS cannot re-rank the queue), **3 Strong** (2, 3, 10), **8 Weak** (1, 5, 6, 7, 8, 9, 11, 12). SPOV 8 is the most contested (gamification net-positive metas vs the leaderboard-distortion mechanism). 3 minor citation FIXes recorded in `04-spov-validation.md` (Pan 2023 re-resolution; Lee 2025 down-weight; Williams/Lombrozo precise mapping).
