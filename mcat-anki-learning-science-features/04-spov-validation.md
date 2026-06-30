# Step 6 — SPOV Testing Protocol results (feature layer)

## Test 1 — Spikiness (cold disagreement, 2 families: Claude-4.6-sonnet + GPT-5.5, bare assertion only)
Rule: unanimous high-agreement + "nod along" = truism = FAIL; "dispute"/"split" = off-consensus = PASS.

| # | Topic | GPT (agree/verdict) | Claude | Test 1 |
|---|---|---|---|---|
| 1 | Disconfirmer authoring scaffold, not AI card-gen | 7 / split | dispute/split | PASS (spike = anti-AI + disconfirmer requirement) |
| 2 | Deep-structure SORT = transfer gate | 6 / dispute | dispute | PASS |
| 3 | Curated discrimination drills, not generic interleave | 6 / split | dispute/split | PASS |
| 4 | Two-tier architecture; live semantic re-rank impossible | 5 / dispute | dispute | PASS (implementation claim → Test 2/3 buildability) |
| 5 | Item-discrimination + PFL metrics; refuse streaks/% | 7 / split | split | PASS |
| 6 | MC net-NEGATIVE without feedback+error-classification | 6 / dispute | dispute | PASS (spike = "net-negative unless," absolutism) |
| 7 | Confidence ONLY for high-confidence-wrong routing | 5 / dispute | dispute | PASS |
| 8 | Exclude leaderboards/loss-streaks despite net-positive metas | 8 / split | split | PASS |
| 9 | AI generates tests, never grades; kill crutch scaffolds | 6 / split | split | PASS |
| 10 | Support-fading per family, no global hard-mode, not for facts | 7 / split | split | PASS |
| 11 | Exam-date desired-retention RAMP, not cram override | 8 / **nod along** | borderline | **WEAK** — close to SR consensus; spike rests on "not a cram override" + buildability |
| 12 | CARS not a flashcard problem (separate module / integrate) | 8 / **nod along** | borderline | **WEAK** — most MCAT educators agree; spike rests on "NEVER a CARS deck / zero diagnostic signal" |
| **D** | **DECOY:** auto-gen full-coverage AI deck + FSRS = all you need | 2 / dispute | spiky-but-WRONG | advances to Test 2 as SELF-CHECK (off-consensus because wrong; must be refuted) |

**Outcome:** all 12 real candidates advance (11, 12 = WEAK). Decoy advances unlabeled into Test 2.

## Test 2 — Defensibility + depth (crux + retreat-resistance + reach)
Two GPT red-teamers (different family than the Claude-Opus generator). WEAKs carry a closable escape hatch — the hardening is adopted into final wording.

| # | Crux (one checkable sentence) | Retreat | Reach | Test 2 | Hardening adopted |
|---|---|---|---|---|---|
| 1 | A required student-written DISCONFIRMER field improves unseen MCAT transfer by ≥0.3 d over an identical authoring scaffold WITHOUT it, at equal time. | FAIL→fix | PASS | WEAK | isolate `student-authored+disconfirmer` vs `+ordinary explanation` vs `AI-draft+student-edit` vs `premade`, equal time |
| 2 | Matched on time/ability/perturbed-accuracy, passing a held-out deep-structure SORT predicts ≥0.3 d better unseen transfer. | PASS | PASS | **PASS** | pre-register sort items; match baseline ability + perturbed accuracy |
| 3 | Human-reviewed mechanism-discrimination drills beat blocked AND high-quality random interleave on unseen confusable-pair science items by ≥0.3 d. | PASS | PASS | **PASS** | compare vs high-quality random interleave on the SAME concept graph (not a straw shuffle) |
| 4 | Stock AnkiMobile custom-scheduling JS CANNOT reorder the due queue by semantic concept cluster (only mutate per-card next intervals) given `{deck_name,seed}` + ≤100-byte customData. | PASS | PASS | **PASS** | scope to "stock Anki/AnkiMobile custom-scheduling JS alone," not "any SRS fork" → Test 3 candidate for HOLDS-ESTABLISHED |
| 5 | Item-discrimination + a PFL proxy predict unseen transfer / detect failed features better than perturbed-accuracy, streaks, or completion %. | FAIL→fix | PASS | WEAK | "refuse them as EVIDENCE OF LEARNING," still allow as UX/ops metrics |
| 6 | MC practice WITHOUT distractor feedback + forced error-classification produces ≤0 gain vs no MC; the same cards WITH the engine ≥0.3 d. | PASS | PASS | WEAK | soften "net-negative" → "unreliable/false-knowledge-prone unless wrapped"; lead with the engine's incremental lift |
| 7 | Confidence features beyond high-confidence-wrong routing fail to improve UNASSISTED unseen performance (or only by reducing error-honesty). | FAIL→fix | PASS | WEAK | scope "never dashboard/FSRS" → no VANITY dashboard + no confidence-only interval change UNLESS it beats routing on unassisted items |
| 8 | Public comparative ranking / loss-framed streaks reduce behavioral honesty ≥15% AND don't improve unseen performance vs private mastery/recovery. | FAIL→fix | PASS | WEAK | ban SPECIFIC mechanics that measurably reduce hard-card attempts/low-confidence admissions/remediation time, not all public comparison by definition |
| 9 | Authoritative AI grading of explanation quality fails to improve (or worsens) UNASSISTED unseen performance vs AI-generated severe tests against a human key, equal time. | PASS (if "AI grading" defined pre-trial) | PASS | WEAK | forbid AI as FINAL authoritative grader; allow source-cited rubric critique only if it beats generate-only on unassisted gains |
| 10 | For high-element families, per-family support-fading after demonstrated unaided success beats global hard-mode on unseen transfer; same fading gives ≈0 for declarative recall. | PASS (names winning condition + scoping disconfirmer) | PASS | **PASS** | distinguish support-fading (high-element problem-solving) from retrieval-format difficulty (declarative); ban ungated global escalation, not every global affordance |
| 11 | Anki 25.09+ custom scheduling can apply a desktop-prepared per-card exam-date DR target during review (exposed decay/DR + small syncable artifacts) WITHOUT forking rslib or corrupting FSRS. | FAIL→fix | PASS | WEAK | specify the per-card target storage/read path (deck buckets / card field / tiny customData); change empirical claim to "higher retention for prioritized concepts at a BOUNDED extra-review budget / after reallocating low-yield reviews" |
| 12 | CARS flashcard-deck accuracy has near-zero correlation with unseen timed-CARS passage performance AND a CARS deck produces no gain over no-CARS-cards, while a passage/error-pattern module does. | FAIL→fix | WEAK | WEAK (absolutist version FAILED) | drop "NEVER a deck / ZERO signal"; scope to "do not ship CARS as a PRIMARY flashcard deck or use CARS card-accuracy as the KPI; use timed passages + error-pattern analytics; optional vocab/taxonomy micro-cards only" |
| **D** | **DECOY:** an auto-gen full-coverage AI deck on FSRS raises unseen MCAT performance ≥ application/discrimination features at equal time. | FAIL | WEAK | **FAIL (FATAL)** | crux REFUTED (coverage≠application; AI items faulty; observational link + Wothe null) |

**Protocol self-check (decoy):** PASS — caught at Test 2 (FATAL, crux refuted). The gate tracks validity, not rhetoric.
**Advancing to Test 3:** all 12 real candidates (PASS: 2, 3, 4, 10; WEAK-hardened: 1, 5, 6, 7, 8, 9, 11, 12). Decoy dropped.

## Test 3 — Verification (externalize the crux vs primary sources / buildability)
citation-checker, crux mode. **No crux REFUTED. 1 HOLDS-ESTABLISHED (SPOV 4), 10 HOLDS-PENDING, 1 PARTLY-CONTESTED (SPOV 8).** Freshly verified: Tetzlaff 2025 (d=0.505/−0.428 verbatim), Rowland no-feedback ≤50% g≈0.03 (k=17, CI spans 0), Bastani et al. 2024 PNAS (GPT Base −17% unassisted), Anki PR #4880 (merged 2026-06-08), and SPOV 4's substrate fact against `scheduler.proto` + `rslib/data.rs` + v3 FAQ.

| # | Test 3 verdict | What's established vs pending |
|---|---|---|
| 4 | **HOLDS-ESTABLISHED** | `SchedulingContext{deck_name,seed}` (proto), ≤100-byte customData (rslib data.rs), queue built backend-side + JS runs at answer-time (v3 FAQ), per-card DR "unaccessible to custom scheduling… only via an add-on" (forum) — stock JS cannot re-rank the queue. Settled, no experiment needed. |
| 2 | HOLDS-PENDING | Chi deep-structure + TAP established; the ≥0.3 d incremental-prediction delta pends held-out data. |
| 3 | HOLDS-PENDING | Discriminative-contrast established + interleaving helps most for confusable similar categories; contested boundary (verbal ~0); 3-arm delta pends. |
| 10 | HOLDS-PENDING (best-grounded) | Expertise reversal verbatim (Tetzlaff 2025 d=0.505/−0.428, 176 ES); MCAT fading-vs-hard-mode delta pends; ERE "less clear" for humanities/verbal. |
| 6 | HOLDS-PENDING | Butler & Roediger lures + Rowland g≈0.03 (no-feedback ≤50%) both verified; "≤0 without feedback" holds for low-accuracy/no-feedback (not universally); engine ≥0.3 d pends. |
| 1 | HOLDS-PENDING | Generation effect d=0.40–0.41 (Bertsch 2007 + 2023 text-gen meta) established; the disconfirmer-SPECIFIC delta untested; generation>premade is load-moderated (can reverse). |
| 5 | HOLDS-PENDING | PFL canonical (Bransford & Schwartz); accuracy-gameable supported (Williams/Lombrozo, looser mapping); comparative predictive claim pends. |
| 7 | HOLDS-PENDING | JOL-bias/foresight-bias established (Koriat & Bjork 2005); "beyond-routing fails" largely untested. |
| 9 | HOLDS-PENDING | Crutch effect verified (Bastani PNAS −17% unassisted) but on HS math (analog, not grading-specific); grading head-to-head pends. |
| 11 | HOLDS-PENDING | Buildability PRIMITIVES established (PR #4880 exposes decay/DR; per-deck DR 25.09; syncable customData) BUT native per-card-DR WRITE is an unmerged PR → feasible via workaround, not one native path; empirical half pends. |
| 12 | HOLDS-PENDING | AAMC CARS-no-content established (strong prior for low correlation); the "near-zero correlation / no-gain" magnitude pends (scoped version). |
| 8 | **PARTLY-SUPPORTED/CONTESTED** | Leaderboard-negative direction real (UMN quasi-exp; Deci) BUT gamification net-positive on average (Sailer & Homner g=0.49) contests the magnitude; the ≥15% honesty figure untested. |
| D | (REFUTED — decoy, already dropped at Test 2) | — |

## Final tiers
- **VALIDATED (Test 1 off-consensus + Test 2 pass + Test 3 HOLDS-ESTABLISHED) — lead the menu:** **SPOV 4** (two-tier architecture; live on-device semantic queue re-ranking is impossible through stock Anki custom-scheduling JS — a true-but-not-widely-known buildability fact). Step 6b: the crux is already settled by Anki's primary source/proto/docs (no future experiment); deepening = the source-level verification above.
- **STRONG (all 3 pass + reach; Test 3 HOLDS-PENDING):** SPOV 2 (deep-structure SORT as the transfer-verification gate), SPOV 3 (curated discrimination drills, not generic interleave), SPOV 10 (per-family support-fading, not global hard-mode; expertise-reversal verbatim).
- **WEAK (Test 3 partly/contested, reach weak, or Test 2 retreat-resistance required the adopted hardening):** SPOV 1 (disconfirmer authoring scaffold), SPOV 5 (falsifiable item-discrimination + PFL metrics), SPOV 6 (MC feedback/error-classification engine), SPOV 7 (confidence → high-confidence-wrong routing only), SPOV 8 (non-distorting gamification only — PARTLY-CONTESTED), SPOV 9 (AI generates severe tests, never grades; + the unassisted crutch kill-switch), SPOV 11 (exam-date desired-retention ramp — buildable via workaround), SPOV 12 (CARS not a primary flashcard deck — scoped).

**Kept: 12/12 candidate-valid (1 Validated, 3 Strong, 8 Weak). Dropped: 1 (decoy) + SPOV 12's absolutist version (kept scoped). Validated: 1.**

## Citation FIXes from Test 3 (apply in the editor's wording)
1. SPOV 1: the Test-3 checker couldn't re-resolve "Pan 2023 d=0.45/0.29" (it WAS verified at Step 1b as Pan, Zung, Imundo, Zhang, Qiu 2023, doi 10.1037/mac0000083) — cite Pan 2023 AND the broader generation-effect primaries (Bertsch 2007 d=0.40; 2023 text-generation meta g=0.41) so the mechanism doesn't rest on one ref.
2. SPOV 7: "Lee 2025 calibration-training" is thin/unverified-this-pass — down-weight; don't make it load-bearing.
3. SPOV 5: Williams/Lombrozo supports "explanation→overgeneralization" (a looser mapping than "perturbed-accuracy is gameable") — state the mechanism precisely.
