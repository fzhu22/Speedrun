# Step 4 — Candidate DOK 4 feature-SPOVs (12) + protocol decoy

Forged by the spov-generator (Claude Opus) from the 12 validated feature insights; each respects the 3 hard constraints (redundancy vs AnKing+UWorld+Jack Westin; observational transfer ceiling → bets with resolvers; Anki buildability). Full elaborations in the generator transcript; condensed here with all gate fields.

### Candidate SPOV 1 — Disconfirmer-field authoring scaffold, NOT AI card-gen
**Assertion:** The flagship feature is a student-authored "miss → card" scaffold whose load-bearing required field is a DISCONFIRMER ("what one fact would flip this answer?"); it must NOT auto-generate the card body (automation forfeits the generation effect + ships faulty LLM items).
**Core Q:** On a miss, generate the card (AI) or scaffold the student to author it — and what field makes it transfer-bearing?
**Prediction/Disconfirmer:** Volume-matched study by 2027-09-01: disconfirmer-scaffold beats BOTH AI-auto-gen and premade-cloze cohorts on UNSEEN MCAT-style transfer items by d≥0.3, AND AI-auto shows ≥10% more faulty cards on blind audit. Non-retreatable: if it doesn't beat premade at equal volume on unseen items, the claim fails ("liked it"/"made more cards" doesn't count).
**Reach:** USMLE Step 1 / bar-exam prep.
**Expert:** disagrees Jarrett Ye (LLM card-gen), UWorld UAsk / RemNote / AnkiHub Smart Search; extends Jack Westin + Pan/Agarwal.
**Insights:** I1, I10 (+I11).

### Candidate SPOV 2 — Deep-structure SORT as the transfer-verification gate
**Assertion:** An "application card" earns the name only if the student passes a deep-structure SORT ("which two share the principle?"); ship the sort as the GATE that unlocks "transfer-trained" status — perturbed-item accuracy alone certifies a pattern-match, not transfer.
**Core Q:** How do you know a transfer card trained the principle vs a new surface shortcut?
**Prediction/Disconfirmer:** By 2027-09-01, on unseen MCAT-style passages, sort-verified students beat students MATCHED on perturbed-item accuracy but not sort-verified by ≥0.3 d. Non-retreatable: if equal, the sort gate adds nothing ("feels deeper" doesn't count).
**Reach:** chess/coding-pattern trainer.
**Expert:** extends Chi (deep vs surface) + Pan; disagrees heatmap culture + AI-minivignette vendors.
**Insights:** I3, I11.

### Candidate SPOV 3 — Curated discrimination drills for known confusable sets, NOT generic interleaving
**Assertion:** Build a curated library of discrimination drills for human-reviewed confusable sets (acids/bases vs buffers; competitive/non-competitive/uncompetitive inhibition; SN1/SN2), each forcing the discriminating MECHANISM + a differing consequence — not a generic interleave toggle, not auto-tagged, not for CARS/verbal.
**Core Q:** Is the win "interleave everything" or curated mechanism-discrimination drills on the confusions that sink MCAT students?
**Prediction/Disconfirmer:** Volume-matched RCT by 2027-09-01: curated drills beat BOTH random-interleave and blocked arms on unseen confusable-pair items by ≥0.3 d AND show ≈0 advantage on expository/verbal (consistent with words −0.39). Non-retreatable: if generic interleave matches at equal volume, "curation beats shuffle" fails; if drills help CARS/verbal, the science-only scoping was wrong.
**Reach:** radiology/derm confusable-lesion-pair drills.
**Expert:** disagrees Anki-forum generic-interleaving + auto-tagging vendors; extends Brunmair & Richter + Rohrer/Taylor (mechanism).
**Insights:** I4, I12.

### Candidate SPOV 4 — Two-tier architecture (desktop-prepare → cross-platform-review); live semantic re-ranking is vaporware
**Assertion:** Every concept-aware feature must be two-tier (desktop "prepare" emits small syncable artifacts → cross-platform card-template-JS "review"), because the live scheduler is code-verified incapable of semantic queue re-ranking — any "your phone reorders your queue by concept in real time" promise is vaporware.
**Core Q:** Where do smart-sequencing features physically run, and which "adaptive on mobile" promises are impossible?
**Prediction/Disconfirmer (buildability, checkable now):** by 2026-12-31, no working build exists where live AnkiMobile custom-scheduling JS REORDERS the due queue by semantic concept cluster (not re-weights one card's interval) using only `{deck_name, seed}` + `customData` ≤100 bytes with no desktop-prepared artifact. If such a build exists, "two-tier is mandatory" is false (re-weighting one interval / front-side cloze via template JS does NOT count).
**Reach:** any cross-platform SRS fork wanting on-device semantic re-ranking.
**Expert:** aligns Damien Elmes + Jarrett Ye/Expertium; disagrees marketing implying live on-device semantic re-ranking.
**Insights:** I12, I2, I4.

### Candidate SPOV 5 — Falsifiable metric layer (item-discrimination + PFL), refuse perturbed-accuracy/streaks
**Assertion:** The fork must instrument its own learning theory with item DISCRIMINATION + a Preparation-for-Future-Learning proxy (fewer trials to acquire the NEXT concept after remediation), and REFUSE to report perturbed-item accuracy, streaks, or deck-completion % as evidence of learning.
**Core Q:** How does the product prove (or disprove) its features work rather than feel rigorous?
**Prediction/Disconfirmer:** By 2027-09-01, "transfer-trained" items show Δ point-biserial ≥0.1 over plain recall clozes AND remediated clusters show fewer trials-to-next-concept than matched non-remediated. Non-retreatable: if "transfer-trained" items discriminate no better than recall clozes, the transfer theory is falsified by its own metric (rising accuracy/streaks don't rescue it).
**Reach:** corporate-compliance / coding-bootcamp LMS claiming "deep learning."
**Expert:** extends Bransford & Schwartz (PFL) + Williams/Lombrozo; disagrees heatmap/streak culture.
**Insights:** I11, I3.

### Candidate SPOV 6 — MC cards net-NEGATIVE without a feedback+error-classification engine
**Assertion:** MC/application cards must be gated behind a feedback-and-remediation engine — commit an answer, then CLASSIFY the error (content/reasoning/trap/timing) against source-backed distractor rationales before ONE targeted remediation card is queued — because unscaffolded MC encodes false knowledge and is net-negative; the buildable value is the engine, not more questions.
**Core Q:** Are MC cards an asset by default or a liability unless wrapped in distractor-feedback + forced error-classification?
**Prediction/Disconfirmer:** Volume-matched RCT by 2027-09-01: MC WITHOUT the engine produces ≤0/negative gain on unseen items vs no MC practice; the SAME cards WITH the engine produce ≥0.3 d. Non-retreatable: if bare MC matches engine-wrapped at equal volume, "the engine is the feature" fails ("did more questions" doesn't count).
**Reach:** bar-exam / NCLEX MC trainer.
**Expert:** disagrees "just do more UWorld"/screenshot cards; extends Butler & Roediger + Jack Westin error taxonomy.
**Insights:** I7, I8.

### Candidate SPOV 7 — Confidence data good ONLY for high-confidence-wrong routing; never a dashboard or FSRS input
**Assertion:** Capture confidence ONLY after a committed answer, flag HIGH-CONFIDENCE-WRONG, route it to a source-backed misconception drill recording the false model — and explicitly REFUSE to show confidence as a dashboard metric or feed it into FSRS intervals (both Goodhart traps).
**Core Q:** What is confidence data actually good for — a dashboard, a scheduling signal, or one trigger?
**Prediction/Disconfirmer:** By 2027-09-01, routing high-confidence-wrong → targeted drills reduces repeat high-confidence-wrong errors on unseen same-family items by ≥20% vs capture-but-don't-route; AND a confidence-driven-FSRS variant shows no recall benefit. Non-retreatable: if routing doesn't beat capture-only, confidence earns no place; if confidence-driven scheduling helps recall, the "never feed FSRS" rule is falsified.
**Reach:** pilot-training / medical-CME high-confidence-error tool.
**Expert:** disagrees calibration-dashboard/predict-your-score products; extends Nelson & Narens/Koriat + parent "scheduler ≠ scorer."
**Insights:** I8, I7.

### Candidate SPOV 8 — Only non-distorting motivation; exclude leaderboards/loss-streaks despite net-positive metas
**Assertion:** Ship only NON-DISTORTING mechanics (private mastery/coverage, recovery streaks rewarding return-after-lapse, effort-credit for hard/low-confidence items) and categorically EXCLUDE public leaderboards/ranking/loss-framed streaks — because (net-positive metas notwithstanding) those Goodhart engagement by punishing the error-confrontation MCAT gains require.
**Core Q:** Given gamification metas are net-positive on engagement, which mechanics are still disqualified for an error-confrontation exam?
**Prediction/Disconfirmer:** By 2027-09-01, A/B: a public leaderboard + loss-streak INCREASES daily engagement but DECREASES a behavioral-honesty metric (attempting flagged-hard cards, low-confidence admissions, time-in-remediation) by ≥15% and does NOT improve unseen-item performance. Non-retreatable: if they raise engagement WITHOUT depressing honesty metrics, the distortion claim fails.
**Reach:** language-learning app loss-streak (more logins, fewer hard lessons).
**Expert:** disagrees streak/leaderboard apps + citing net-positive metas as defense; extends Deci + Huang 2024.
**Insights:** I9, I8.

### Candidate SPOV 9 — AI GENERATES severe tests, never GRADES; kill any assisted-up/unassisted-down scaffold
**Assertion:** The AI lane is restricted to GENERATING severe tests (counterexamples, boundary cases, disconfirmer prompts, contradiction checks) against a human-authored key — never grading explanation quality as authoritative — and every AI scaffold must be killed if it raises ASSISTED but lowers UNASSISTED MCAT-style performance (the exam is taken unassisted).
**Core Q:** What may AI do, and what gate separates a real aid from a liked-but-harmful crutch?
**Prediction/Disconfirmer:** By 2027-09-01, ≥1 popular AI scaffold (explanation-grader or card-gen) shows the crutch signature on a held-out test (assisted up, UNASSISTED flat/down ≥5pp vs no-AI/generate-only). Non-retreatable: if AI explanation-GRADING raises UNASSISTED unseen performance over a generate-only arm at equal time, the "never grade" restriction is falsified (satisfaction/assisted accuracy doesn't count).
**Reach:** AI coding tutor (auto-writes → in-IDE up, whiteboard down).
**Expert:** disagrees Jarrett Ye / UWorld UAsk / AnkiHub Chatbot / RemNote AI; extends BMC "all faulty" + the −17% unassisted finding.
**Insights:** I10, I1.

### Candidate SPOV 10 — Support-fading per concept-family toward the rejected alternative; no global hard-mode, not for declarative recall
**Assertion:** Difficulty must FADE SUPPORT within a per-concept-family expertise estimate (fade only after ≥2 unaided successes + 1 transfer item, toward explaining the REJECTED alternative) and must NOT offer a global "hard mode" or apply to declarative recall — escalating difficulty on novices or rote facts backfires (expertise reversal).
**Core Q:** Should "adaptive difficulty" crank global hardness or fade specific scaffolds per family toward the counterfactual — and where does it backfire?
**Prediction/Disconfirmer:** Volume-matched by 2027-09-01: per-family support-fading beats BOTH global-hard-mode and no-fading on unseen high-element-interactivity items by ≥0.3 d AND shows ≈0/negative on declarative-recall families. Non-retreatable: if global hard-mode matches per-family fading on unseen high-element items, "fade don't escalate" fails; if fading helps declarative recall too, the high-element scoping was wrong.
**Reach:** math-tutoring (per-skill fading > global slider; nothing for arithmetic fluency).
**Expert:** disagrees "hard mode"/global-difficulty designs; extends Sweller/Chen/Kalyuga + Atkinson/Renkl.
**Insights:** I6, I4.

### Candidate SPOV 11 — Exam-date desired-retention RAMP over FSRS, NOT a cram override
**Assertion:** Build an exam-date-aware desired-retention RAMP (raise per-deck/per-card DR smoothly toward test day, high-yield/weak first, capped below the >97% workload cliff) layered OVER FSRS — NOT a naive cram override (max-interval hack / filtered-deck pileup) that corrupts FSRS.
**Core Q:** How to make Anki exam-date-aware — a cram override or a DR ramp on top of FSRS?
**Prediction/Disconfirmer:** Buildability (by 2026-12-31): a per-card DR ramp toward a date IS implementable via the exposed custom-scheduling surface (decay+DR exposed via PR #4880; per-deck DR 25.09) + a desktop-prepared per-card target WITHOUT forking rslib. Empirical (2027-09-01): DR-ramp cohort reaches test day with higher true retention on high-yield/weak concepts at equal/fewer reviews than fixed-90%-DR; cram-override arm shows corrupted intervals. Non-retreatable: if the ramp REQUIRES an rslib fork, "layer over FSRS" fails; if a cram override matches without corruption, "not a cram override" fails.
**Reach:** bar-exam / language-proficiency SRS exam-date ramp.
**Expert:** extends Anki-forum deadline requests + FSRS Helper; disagrees filtered-deck cram + "cramming is less effective" dismissals.
**Insights:** I2, I12.

### Candidate SPOV 12 — CARS is not a flashcard problem (separate passage module or integrate); never a "CARS deck"
**Assertion:** The fork must decide explicitly that CARS is NOT a flashcard problem — build a SEPARATE daily-passage + reasoning/error-pattern module (inference/tone/scope/timing) or deliberately leave CARS to an integration (Jack Westin) — and NEVER ship a "CARS content deck," because recall yields ZERO diagnostic signal for the reasoning/timing/tone failures that limit CARS.
**Core Q:** Cover CARS with cards, or recognize it's a different construct needing passages + reasoning analytics?
**Prediction/Disconfirmer:** By 2027-09-01, a "CARS content deck" arm shows ≈0 improvement on unseen CARS passages vs no-CARS-cards, while a daily-timed-passage + error-pattern module shows a positive gain, AND CARS card-accuracy fails to correlate (r<0.2) with unseen-passage CARS performance. Non-retreatable: if a CARS content deck DOES improve unseen CARS scores, or card-accuracy correlates strongly with passage performance, the "no diagnostic signal" claim is falsified.
**Reach:** LSAT logical-reasoning / GRE-verbal trainer (fact deck = zero signal; passage module helps).
**Expert:** agree-extends Jack Westin + 520-scorer consensus; disagrees "CARS deck" culture.
**Insights:** I5, I11.

---
## DECOY (protocol self-check — NOT a real candidate)
**Decoy SPOV:** Because spaced repetition + FSRS is a solved, proven engine, the single best MCAT feature is to AUTO-GENERATE a comprehensive AI flashcard deck covering 100% of the AAMC content outline and let FSRS schedule it — total coverage plus a great algorithm is all a student needs; "application," "transfer," and "discrimination" features are over-engineering that adds friction without moving scores.
*(Deliberately wrong but persuasive: contradicts the whole corpus — AI card-gen ships faulty items [BMC "all faulty"], coverage ≠ application, recognition ≠ transfer [Pan moderators; "feel good in Anki, bad in passages"], and the Anki↔exam evidence is observational. Should FAIL Test 2/3 — crux "an auto-generated full-coverage deck on FSRS raises unseen MCAT-style performance at least as much as application/discrimination features" is refuted. If it PASSES, the protocol is tracking rhetoric.)*
