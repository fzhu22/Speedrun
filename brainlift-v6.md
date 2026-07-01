# Speedrun: Three Features That Improve on Anki's Deliberate Design Choices

## Owners

Franklin Zhu

## Headline

Three additions earn their place on the strongest evidence: pretest-first cards, three honest scores that abstain, and student-authored application cards, all riding one architecture Anki's engine forces.

## Purpose

**Purpose (North Star).** This is a hardened version of the Speedrun BrainLift. Every position from the prior version was put through the SPOV Testing Protocol (a red-teamer on a different model family extracted each load-bearing claim and tested its retreat-resistance and reach; the citation-checker verified each claim against primary sources), and the menu was then pruned to the positions strongest not on spikiness but on two things the owner actually cares about: how likely each claim is to be validated, and how useful it is for a real build decision. The survivors are organized as one enabling constraint plus three features, and several positions point at the same feature. Each position still names the deliberate Anki choice it departs from and why the departure is better for one high-stakes exam.

**In scope.** One enabling constraint (the two-tier architecture, with the shared Rust `topic_mastery` query and the concept-graph spine it needs) and three features: pretest-first cards, the three-score honest dashboard (with its coverage veto and abstention), and the student-authored application loop (with per-family support-fading and the AI hint lane).

**Out of scope.** The project givens (fork Anki, one shared Rust engine, AGPL, MCAT-only, Android-first) and the deferred or excluded positions recorded in the source BrainLifts (an exam-date retention ramp, a CARS module, refutation cards, guided drawing, iOS, AI card authoring, leaderboards, a confidence dashboard, an auto-clustered graph).

**One honesty rule for the whole menu.** The link from a better flashcard feature to a higher MCAT score is observational, not proven: the Anki-to-exam literature is non-randomized and the one applied study that measured it directly is null (Wothe et al., Step 2 CK, 252.5 vs 247.0, p=0.440). Only the architecture is settled outright, against Anki's source. Everything else rests on an established mechanism whose MCAT-specific magnitude is a bet, so each position states how far it is validated and what would settle the rest. The measurement positions are spiky against the market's habit of selling one confident number; the learning positions are mainstream science the market does not ship.

## DOK 4: Spiky Points of View

A depth-gated, hardened menu. It is organized as one enabling constraint and three features; positions that share a feature are grouped under it. Tiers: Validated (crux settled against primary sources), Strong (crux holds, magnitude pends a dated experiment), Promising (a genuine bet with live counter-evidence, kept because it is useful and testable).

### Enabling constraint

#### SPOV 1 (Validated): Every concept-aware feature must be desktop-prepared and read by a plain review client, because Anki's engine cannot reorder the queue by concept on the phone. This is a constraint the three features obey, not a feature itself.

Spiky relative to: expert framing and current market practice.

Elaboration: Anki moved scheduling into one Rust engine with the v3 scheduler, reduced custom scheduling to a thin per-card hook, and deliberately removed the ability to monkey-patch it. The motive is sound engineering: one correct, fast engine shared across desktop, AnkiMobile, and AnkiDroid, with dependable sync, rather than fragile per-platform add-ons. The mobile clients do run the per-card scheduling JavaScript, and they do offer on-device levers such as deck order and tag-based Custom Study, but none of them can reorder the gather queue by semantic concept unless the concept tags were already computed elsewhere. So Speedrun does all concept work in a desktop "prepare" tier and writes small syncable artifacts (tags and config) that any review client reads, which is why the study cards are ordinary note types that run unchanged on the AnkiDroid fork. The one genuine engine change fits the same discipline: a read-only per-topic mastery query added beside the `extract_fsrs_retrievability` SQLite function it depends on, so the same numbers reach both platforms. The concept graph is likewise built only in the prepare tier.

Prediction (or Disconfirmer): No build reorders the due queue by semantic concept using only supported on-device surfaces, without a desktop-prepared artifact; re-verify against `main` by 2026-12-31. Re-weighting one card's interval, or a Custom Study filter over pre-existing tags, does not count.

How to resolve it: Already settled by primary source. The load-bearing word is "semantic": `scheduler.proto` delivers the queue from the backend and the per-card hook only adjusts a shown card; the v3 FAQ confirms it cannot be monkey-patched; PR #4880 (2026) added read access to a card's decay and desired retention, but not queue reordering.

Validation: Test 1 off-consensus as an architectural mandate and against marketing that implies live on-device sequencing. Test 2 crux and reach both pass (it constrains any concept-aware cross-platform Anki fork, not only Speedrun). Test 3 HOLDS-ESTABLISHED, confirmed directly against `scheduler.proto`, the v3 FAQ, and PR #4880; the red-teamer's one correction, that this is a constraint rather than a user-facing feature, is adopted above.

### Feature 1: Pretest-first cards

#### SPOV 2 (Strong): Introduce new material with a forced guess, reveal, and mandatory feedback, inverting spaced repetition's rule of reviewing only what you already know.

Spiky relative to: current market practice.

Elaboration: Spaced repetition is built to schedule known material efficiently, so Anki defers what you have not learned and shows new cards study-first. That is the right default for pure retention, but it forgoes the encoding benefit of a wrong guess taken before first exposure. Pretesting produces a real gain on the specific item tried, but only with corrective feedback, so Speedrun's pretest card always reveals the answer plus an explanation. It is on by default because learners systematically judge it worse than it is, and it lives entirely in the card template, so it needs no engine change and renders on any client. This was the strongest position in testing on both axes: the cleanest, most buildable claim and the best-supported one.

Prediction (or Disconfirmer): Forced-guess-then-feedback beats study-first on delayed accuracy for the pretested items by g≥0.3, with roughly zero spillover to untested items in the same topic, at equal time. A test-after-study arm is mandatory, because whether pretest beats test-after-study is contested.

How to resolve it: A three-arm, equal-time trial (study-first versus pretest versus test-after-study) using only semantically proximate lures.

Validation: Test 1 spiky against tools that review only what you already know. Test 2 crux, retreat-resistance, and reach all pass. Test 3 HOLDS-ESTABLISHED: two independent preregistered meta-analyses match exactly (St. Hilaire et al., 2023, specific g=0.54 versus general g=0.04; King-Shepard et al., 2025, g=0.66 versus 0.01, with feedback-plus-prequestions beating prequestions alone), and the "beats test-after-study" counter-case (Latimier et al., 2019) is correctly scoped out because the claim is only "beats study-first."

### Feature 2: The three-score honest dashboard

#### SPOV 3 (Strong): Report memory, performance, and readiness as three separately-gated scores, and require the performance score to add predictive value beyond recall or not ship it.

Spiky relative to: current market practice.

Elaboration: FSRS is honest precisely because it models one thing, the probability of recall, and does it well; Anki deliberately claims nothing about understanding or exam readiness. The market fills that vacuum with one confident readiness percentage, which is where the dishonesty enters, because recall predicts transfer only conditionally and a blended number hides the section actually holding a student back. CARS is the proof case: the AAMC states it requires no specific content knowledge, so a recall signal is structurally blind to roughly a quarter of the exam. The hardened claim, adopted after testing, is not that a correlated performance score is "fake," which overstated the evidence, but that Performance must carry predictive variance beyond recall or it is redundant. Speedrun keeps FSRS for Memory, gates Performance and Readiness separately, and reports Readiness only as a range. This is also why Performance and Readiness abstain on a fresh deck while Memory reports.

Prediction (or Disconfirmer): On held-out data, Performance retains predictive variance for passage outcomes after controlling for recall within difficulty-matched tags. If application-specific signals add no out-of-sample value beyond recall, Performance is redundant and should be deleted.

How to resolve it: An incremental-validity regression on difficulty-matched, surface-perturbed items.

Validation: Test 1 spiky against the market's single-number habit. Test 2 crux holds once softened to "must add independent predictive value," with reach to any exam where recall and transfer diverge. Test 3 HOLDS-ESTABLISHED for the mechanism (Pan & Rickard, 2018: transfer d=0.40, 0.28 without response congruency, near zero once moderators are absent), with the citation-checker's correction adopted: the earlier "carries no independent information" was an overclaim, since transfer is positive but conditional, not zero.

#### SPOV 4 (Strong): Refuse to show a readiness number below an evidence floor, veto it on coverage against the official outline, and replace the withheld number with the single best next topic.

Spiky relative to: current market practice.

Elaboration: Anki always shows your stats and never refuses, which is fine for a memory tool that makes no high-stakes external claim. A readiness score is different, because being confidently wrong about whether you will hit a 510 is worse than saying nothing, and the labels are brutally scarce, since an official MCAT score is roughly one delayed, biased data point per student. Fitting a confident day-one predictor onto data that thin manufactures precision. Speedrun therefore withholds readiness below its evidence thresholds, computes coverage against the official outline so a large deck that skips a high-weight section can never read "ready," and replaces the withheld number with a prerequisite-constrained next-best topic. The specific thresholds are tunable defaults, not claimed to be optimal, which is the honest framing after testing flagged them as arbitrary.

Prediction (or Disconfirmer): Coverage-based abstention improves the calibration of the scores that are shown, versus scoring everyone. The open question is behavioral, namely whether the refusal costs retention, which is a separate bet.

How to resolve it: A held-out calibration comparison of gated versus score-everyone, plus a usage A/B for churn.

Validation: Test 1 spiky against confident-dashboard prep tools. Test 2 crux holds for the abstention principle, though the specific thresholds are not defensible as optimal and can move after a failure. Test 3 HOLDS-PENDING: selective prediction is established and, importantly, on-domain (Mitton et al., 2025, knowledge tracing: abstaining on the most uncertain 20% lifts accepted accuracy by 2.3 to 3.0 points), but "improves calibration" specifically pends a measurement on Speedrun's own data, since the published gains are accuracy, not calibration.

### Feature 3: The student-authored application loop

#### SPOV 5 (Strong): Close the recognition-to-application gap by making the student author the card, and keep AI off the authoring and grading path.

Spiky relative to: current market practice.

Elaboration: Anki treats every card identically and optimizes only when you review, never what a card trains or how you make it, because that generality is what lets one tool serve medicine, languages, and law. For the MCAT the binding failure is recognition without application, which scheduling cannot touch, so the fix belongs in the space Anki leaves empty. Speedrun has the student author the card, because self-generated material beats premade, and validates a required disconfirmer field so it cannot merely restate the answer, because feedback is load-bearing. AI stays off the authoring and grading path: it may suggest a card type and offer source-cited hints against a human key, must beat a template baseline on a held-out evaluation before students see it, and falls back to deterministic heuristics with no key. Testing narrowed two things. The disconfirmer card format specifically is unvalidated and is treated as an experiment rather than an established design. And the anti-AI-authoring case is softer than first stated: the evidence is that AI-generated item sets each contain some faulty items and need human review, not that they are uniformly unusable, and newer models are closing the gap, so the rule is "AI off the score path and human-reviewed," not "AI items are always worse."

Prediction (or Disconfirmer): A student-authored application card beats a premade one on delayed application at equal time. Any AI level whose users perform at least five points worse unaided than a no-AI arm (the crutch signature) is disabled.

How to resolve it: A multi-arm, equal-time trial isolating authoring against premade cards, with an unassisted-performance phase to catch the crutch signature.

Validation: Test 1 spiky against premade-deck and AI-authoring vendors. Test 2 crux (student authoring beats premade for application) holds; the disconfirmer format is split out as a bet. Test 3 HOLDS-ESTABLISHED for authoring (Pan, 2023, user-generated over premade, d=0.45 memory and 0.29 application; Bertsch et al., 2007; feedback required, Rowland, 2014). The AI guardrail is only PARTLY-SUPPORTED: the crutch effect is real but from an analog domain and is design-dependent (Bastani et al., 2024, and notably its guard-railed tutor removed the penalty, which supports this exact design), and the "LLM items are unreliable" half was overstated and is eroding, so it is kept as a discipline, not a strong claim.

#### SPOV 6 (Promising, a testable bet): Fade support per concept-family rather than with a global difficulty setting, but treat this as a bet, because adaptive fading may not beat a fixed setting and can reverse for high-ability learners.

Spiky relative to: current market practice.

Elaboration: The principle underneath is settled: heavy assistance helps novices and hurts experts, so a global "hard mode" is the wrong instrument. What testing did not support is the operational step Speedrun takes on top of it, that a mastery-gated, per-family fading schedule reliably beats a fixed setting. A large field trial found adaptive practice did not beat static on average and that static actually won for high-ability students, which is close to Speedrun's likely high-prior MCAT population. This is the one position kept as an explicit bet rather than a strong claim, because it is useful and the built implementation is deliberately conservative as a hedge: it never seeds the mastery rung from recall alone, and it reinstates support on any miss. It is a candidate to disable, not defend, if the risk shows up.

Prediction (or Disconfirmer): Per-family fading beats a fixed scaffold on unseen transfer at equal time and is flat or negative on declarative families. The disconfirmer is explicit: if a fixed setting matches or beats fading for high-ability learners at equal time, disable fading.

How to resolve it: A volume-matched trial with a fixed-setting arm and, critically, a high-ability subgroup, because that is where the counter-evidence lives.

Validation: Test 1 spiky against a market that ships fixed cards or a single global toggle. Test 2 crux holds but retreat-resistance is only conditional (the claim can blame implementation or concept-family boundaries), which is part of why it is demoted. Test 3 PARTLY-SUPPORTED and CONTESTED: expertise reversal is established (Tetzlaff et al., 2025, d=0.505 for low-prior versus −0.428 for high-prior), but "adaptive fading beats fixed" fails a large RCT and reverses for high-ability learners (van Klaveren et al., 2017), which is the named contested point.

## Experts

- **Damien Elmes ("dae").** Who: creator of Anki and maintainer of the Rust engine and v3 scheduler. Focus: what the engine deliberately does and does not expose, and why. Why follow: the source of truth on the two-tier constraint. Where: https://github.com/ankitects/anki
- **Jarrett Ye ("L-M-Sherlock").** Who: author of FSRS and its benchmark. Focus: the recall model and why it estimates memory alone. Why follow: grounds why Memory is honest and Readiness must be separate. Where: https://github.com/l-m-sherlock
- **Steven C. Pan.** Who: learning scientist. Focus: transfer of test-enhanced learning and the generation effect. Why follow: recall-is-not-transfer (SPOV 3) and authoring-beats-consuming (SPOV 5). Where: https://sc-pan.github.io/
- **Nate Kornell and Shana Carpenter.** Who: memory researchers. Focus: pretesting, errorful generation, and the feedback and proximity constraints. Why follow: the evidence spine of SPOV 2, the strongest position. Where: https://doi.org/10.1007/s10648-025-10075-7
- **Sayash Kapoor and Arvind Narayanan.** Who: ML-reproducibility researchers. Focus: leakage and overoptimism in fitted predictors. Why follow: the argument for the abstain rule (SPOV 4). Where: https://reproducible.cs.princeton.edu/
- **Leonie Tetzlaff and Garvin Brod.** Who: authors of the 2025 expertise-reversal meta-analysis. Focus: how assistance should scale with prior knowledge. Why follow: the settled half of the fading bet (SPOV 6). Where: https://doi.org/10.1016/j.learninstruc.2025.102142
- **Chris van Klaveren and colleagues.** Who: education-economics researchers. Focus: a large field RCT on adaptive versus static practice. Why follow: the counter-evidence that demotes fading to a bet, and the high-ability reversal to watch. Where: https://doi.org/10.1016/j.econedurev.2017.04.003
- **AAMC MCAT resources.** Who: the test maker. Focus: the official scale, section bands, the content outline, and CARS requiring no content knowledge. Why follow: anchors the three scores and the coverage map. Where: https://students-residents.aamc.org/about-mcat-exam/how-mcat-scored

## DOK 3: Insights

### Reading Anki's choices as motives

**Insight 1 (Buildability):** Anki's greatest strength, a single correct and fast Rust engine that is shared across platforms and cannot be monkey-patched, is exactly what forbids on-device concept intelligence. The right response is to inherit the engine and add a desktop "prepare" tier plus one read-only shared query, not to fork the scheduler. *Rests on:* `scheduler.proto` delivering the queue from the backend; the per-card-only hook; the no-monkey-patch FAQ; PR #4880 adding read-only decay and desired retention; `extract_fsrs_retrievability` living in `rslib`.

**Insight 2 (Measurement):** FSRS is honest because it measures only recall; the dishonesty appears when one number is asked to mean readiness. The fix is construct separation plus abstention, not a cleverer predictor, and the honest form of the claim is that a performance score must add value beyond recall, not that any correlation makes it fake. *Rests on:* Pan & Rickard (2018); AAMC bands and CARS-no-content; Kapoor & Narayanan on leakage; Mitton et al. (2025) on selective prediction in knowledge tracing.

### Reading the learning evidence honestly

**Insight 3 (Direction is safe, magnitude is not, and not all levers are equal):** After testing, the learning levers split cleanly by how well they hold up. The strongest are the ones with converging preregistered meta-analyses and a clean, item-specific mechanism (pretesting with feedback) or a large, well-replicated base (student generation). The weakest is the adaptive personalization step (per-family fading), because a settled principle (expertise reversal) does not guarantee that an adaptive schedule beats a fixed one, and a large field RCT reverses it for high-ability learners, which is the MCAT population. Build the first group as features; instrument the last as a bet. *Rests on:* St. Hilaire (2023) and King-Shepard (2025); Pan (2023) and Bertsch (2007); Tetzlaff (2025) versus van Klaveren (2017).

**Insight 4 (Anki defaults trade honesty for adherence):** Anki's defaults optimize sustainable daily review. Hard counts as a pass, stats are always visible, and nothing is ever refused, which quietly trades measurement honesty for adherence. A high-stakes exam tool has to re-tighten the honesty the general tool relaxed, through a threshold-based mastery definition, a coverage veto, and abstention. *Rests on:* Anki stats counting Hard, Good, and Easy as a pass; the Hard-misuse inflation note; the leech threshold; the selective-prediction literature.

**Insight 5 (The observational ceiling):** Every "this is better" claim ultimately rests on an unproven observational link from a feature to an MCAT score, so the honest posture is to ship the mechanism and instrument the bet, never to assert the gain. *Rests on:* the non-randomized Anki-to-exam literature; the null Wothe et al. Step 2 CK result.

## DOK 2: Knowledge Tree

### A. Anki's engineering choices and their rationale

- **Source — Anki v3 scheduler FAQ, `scheduler.proto`, PR #4880.** *DOK 1 facts:* the scheduling context is delivered per card from the Rust backend and the custom hook only adjusts a shown card, so it cannot reorder the gather queue; the v3 scheduler cannot be monkey-patched and has been default since 23.10; PR #4880 (merged 2026-06-08) exposes a card's decay and desired retention for reading only; the pre-#4880 context carried two fields (deck name and seed), now four; the mobile clients run the per-card JS but allow no add-ons or Python. *DOK 2 summary:* the constraints are deliberate choices for a robust, shared engine, and they force the two-tier split; the load-bearing word is "semantic," since on-device reordering exists only over pre-prepared tags. *Link:* https://faqs.ankiweb.net/the-2021-scheduler.html ; https://github.com/ankitects/anki/pull/4880
- **Source — FSRS docs and benchmark; the `topic_mastery` change.** *DOK 1 facts:* FSRS models difficulty, stability, and retrievability, estimating the probability of recall, and does not estimate reasoning or an exam score; the mastery query is a read-only RPC beside `extract_fsrs_retrievability`, returning per-tag counts and average recall. *DOK 2 summary:* FSRS is an honest recall estimator by design, which is why Memory is trustworthy and Readiness is built separately, and the one engine change respects the same boundary. *Link:* https://expertium.github.io/Benchmark.html

### B. Memory, performance, and readiness

- **Source — Pan & Rickard (2018).** *DOK 1 facts:* testing-to-transfer d=0.40, 0.58 with response congruency, 0.28 without, near zero after bias correction when moderators are absent. *DOK 2 summary:* recall is a conditional, attenuated proxy for transfer, so Performance must add independent value; the earlier "no independent information" phrasing was an overclaim its own source refutes. *Link:* https://doi.org/10.1037/bul0000151
- **Source — AAMC scoring and outline; Mitton et al. (2025); Kapoor & Narayanan; Chen & Corridon.** *DOK 1 facts:* section scores 118–132, total 472–528, with a ±2 total and ±1 section band; CARS requires no specific content knowledge; abstaining on the most uncertain 20% of knowledge-tracing predictions lifts accepted accuracy by 2.3 to 3.0 points; leakage produces overoptimism across hundreds of studies; the strongest single-anchor validation study for practice-to-MCAT prediction is very small. *DOK 2 summary:* labels are scarce and the feature-to-score link is observational, so the dashboard abstains and instruments the bet; selective prediction is on-domain, though the calibration gain specifically pends a measurement on the app's data. *Link:* https://students-residents.aamc.org/about-mcat-exam/how-mcat-scored ; https://arxiv.org/abs/2509.21514 ; https://doi.org/10.1016/j.patter.2023.100804

### C. The application loop

- **Source — Pan (2023); Bertsch et al. (2007); Rowland (2014).** *DOK 1 facts:* user-generated material beats premade, d=0.45 for memory and 0.29 for application; the generation effect is about 0.40 across 86 studies; without feedback the testing effect only emerges above roughly 50% initial accuracy. *DOK 2 summary:* students should author application cards and feedback is load-bearing, which is the disconfirmer loop; the disconfirmer format itself is an experiment. *Link:* https://doi.org/10.1037/mac0000083 ; https://doi.org/10.3758/bf03193441 ; https://doi.org/10.1037/a0037559
- **Source — Tetzlaff et al. (2025); Salden et al. (2010); van Klaveren et al. (2017).** *DOK 1 facts:* high assistance helps low-prior learners (d=0.505) and hurts high-prior learners (d=−0.428); mastery-gated fading beat fixed fading in one tutoring line (d=0.49 to 0.74); but a large field RCT found adaptive practice did not beat static on average and static won for high-ability students by about 0.08 standard deviations. *DOK 2 summary:* the expertise-reversal principle is settled, but the adaptive-fading step is contested for exactly the high-ability population Speedrun serves, so fading is a conservative, instrumented bet. *Link:* https://doi.org/10.1016/j.learninstruc.2025.102142 ; https://doi.org/10.1007/s11251-009-9107-8 ; https://doi.org/10.1016/j.econedurev.2017.04.003
- **Source — Bastani et al. (2024); BMC review of LLM item generation (2024).** *DOK 1 facts:* GPT-4 tutoring raised assisted performance by 48% and cut unassisted performance by 17% on high-school math, but a guard-railed version removed the unassisted penalty; the review found every studied LLM item set contained some faulty questions, while several studies also produced exam-valid questions. *DOK 2 summary:* keep AI off the authoring and grading path and govern any AI level by unassisted performance, but hold the "AI items are unreliable" claim as a review discipline rather than a settled result, since it is design-dependent and eroding with newer models. *Link:* https://doi.org/10.1073/pnas.2422633122 ; https://doi.org/10.1186/s12909-024-05239-y

### D. First-exposure pretesting

- **Source — St. Hilaire et al. (2023); King-Shepard et al. (2025); Latimier et al. (2019).** *DOK 1 facts:* pretested content g=0.54 versus 0.04 for the surrounding topic, and g=0.66 versus 0.01 in the 2025 meta, with feedback-plus-prequestions beating prequestions alone; a field study found post-testing beat pre-testing on trained items, but both beat equal-time reading. *DOK 2 summary:* an item-specific, feedback-dependent first-exposure benefit that is the best-supported learning position; the pretest-versus-post-test question is scoped out because the claim is only that it beats study-first. *Link:* https://doi.org/10.3758/s13423-023-02353-8 ; https://doi.org/10.1007/s10648-025-10075-7 ; https://doi.org/10.1038/s41539-019-0053-1

## Hardening pass (v6): what changed and why

- **Kept and led with the best-validated positions.** Testing ranked pretest-first (SPOV 2), construct separation (SPOV 3), and student authoring (SPOV 5) highest on likelihood-to-validate and usefulness; their cruxes are HOLDS-ESTABLISHED against primary sources.
- **Demoted the architecture to a constraint.** The two-tier claim (SPOV 1) is the most-verified position but is not a user-facing feature, so it is now the enabling constraint the three features obey.
- **Softened the construct-separation overclaim.** "If Memory predicts Performance, Performance is fake" was refuted by its own source (transfer is positive but conditional, not zero) and is now "Performance must add independent predictive value."
- **Merged abstention into the dashboard.** The refusal (SPOV 4) is no longer a standalone headline; it is the readiness rule of the three-score feature, its thresholds labeled as tunable defaults rather than optimal, and its verdict corrected to HOLDS-PENDING with on-domain support (Mitton 2025).
- **Demoted fading to a bet.** Mastery-gated per-family fading (SPOV 6) is CONTESTED: a large field RCT reverses it for high-ability learners, the MCAT population, so it is Promising with an explicit "disable if a fixed setting wins for high-ability learners" disconfirmer.
- **Folded the AI position into a guardrail and fixed its citations.** The standalone AI SPOV was the weakest; it is now the AI-off discipline inside SPOV 5. The BMC citation was corrected (to `10.1186/s12909-024-05239-y`) and "all faulty" softened to "each set contained some faulty items," since the claim is design-dependent and eroding for newer models.
- **Result:** one constraint and three features (pretest cards, the honest dashboard, the authoring loop), carried by six tested positions, one Validated, four Strong, one Promising.
