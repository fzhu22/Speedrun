---
name: speedrun-mcat
description: Guides building Speedrun, an MCAT study app forked from Anki (shared Rust engine, desktop + phone companion, two-way sync). Use whenever the user mentions building, planning, designing, creating, brainstorming, or scoping anything in this project — or works on its Anki fork, FSRS/scheduler/rslib changes, the three scores (memory/performance/readiness), readiness/give-up logic, AI card generation or evals, sync, or any MCAT learning-science feature. Read the project brief and research first (mcat-anki-learning-science-features/speedrun-spec.md, brainlift.md, actions/action-plan.md). Enforces the spec's honesty rules and the project's validated learning-science positions.
---

# Speedrun (MCAT Anki Fork)

Building a Desktop + Mobile study app on a fork of Anki for **one exam: the MCAT**. One shared Rust engine powers both apps; reviews and progress sync between them.

**Before designing, planning, or coding any feature, read the project research — start with the spec:**
- `mcat-anki-learning-science-features/speedrun-spec.md` — the canonical project brief (the assignment itself): the mission, the rules you cannot break, the Wed/Fri/Sun deadlines, the concrete challenges (7a-7h), how it is graded, and what to hand in. Everything else derives from this; if another file conflicts with the spec, the spec wins.
- `mcat-anki-learning-science-features/brainlift.md` — the depth-gated menu of validated/strong/weak feature positions (SPOVs) with the experiment that would settle each.
- `mcat-anki-learning-science-features/actions/action-plan.md` — the sequenced, feasibility-tested build plan (A1-A12), anti-patterns, critical path, and open decisions.

Summarize the relevant spec rule and SPOV / action step before writing code. Then consult [anki-brownfield.md](anki-brownfield.md) for engine constraints and [learning-science.md](learning-science.md) for the position/anti-pattern index.

## The three scores (never blend them)

Show **three separate** scores, each with a range — not one number:
- **Memory**: chance the student recalls a taught fact right now (FSRS already does this well — do not reinvent it).
- **Performance**: chance the student answers a *new, exam-style* question correctly, including unseen ones.
- **Readiness**: projected score on the real MCAT scale, with a range and a confidence note.

The hard bridges to build are memory->performance and performance->readiness. Measure the gap; do not hide it.

## The honesty rule (load-bearing)

Never show a readiness score unless you can also show:
1. what evidence produced the number,
2. what data is still missing,
3. how accurate past guesses turned out (calibration),
4. the likely range, not a single number,
5. the single best next thing to study.

A confident number without those is a guess in a nice font.

**Good readiness display:** `Projected MCAT: 508 | Likely range: 503-512 | Confidence: low, only 42% of topics studied | Updated: <time> | Top reasons: ... | Abstains when: <rule>`

## The give-up rule

The app must show **no score** when it lacks data. State the line explicitly and enforce it (example default: no score until >=200 graded reviews AND >=50% topic coverage). A deck that skips a high-weight section must not show "ready."

## MCAT specifics

- Total **472-528**; four sections each **118-132**.
- Huge fact base + reading passages; the hard part is covering it all.
- Build a **coverage map** against the official outline; show percent covered on the dashboard; abstain below the coverage line.
- CARS is a different construct — do **not** make it a primary flashcard deck or use card-accuracy as its KPI (see learning-science.md).

## Build order (no AI before Wednesday)

- **Wed**: both apps work and review the same deck. No AI: no model calls, no generated cards, no chatbot. Includes a real Rust change (3 Rust unit tests + 1 Python-calling test, undo works, no corruption) and a clean-machine installer.
- **Fri**: AI added and checked. Two-way sync works (review on phone -> see on desktop and reverse, no lost/double-counted reviews). Phone shows the three scores with ranges + give-up rule.
- **Sun**: prove it (calibration chart + Brier/log loss on held-out reviews; performance accuracy on held-out items; documented score mapping with a range; the study-feature 3-build test). Ship installable desktop + phone builds. Both run with AI off.

## AI discipline (or the AI section scores zero)

- Every AI output traces back to a **named source**.
- Run an **eval before students see anything**: accuracy + wrong-answer rate on a **held-out** set, with a cutoff set *before* looking at results; block cards that fail.
- **Beat a simpler baseline** (keyword or vector search) side by side.
- The app must still give a score with **AI switched off**.
- Run a **leakage check**: scan training data for test items or near-copies; leaked test data zeroes that score.

## Automatic fails / hard limits

- Made-up or misleading readiness numbers = **automatic fail**.
- Leaked test data = that score is **zero**. AI claims with no traceable source = AI section **zero**.
- No real Rust change: 50% cap. No phone companion sharing the engine + syncing: 70% cap. No re-runnable test setup or no held-out testing: 60% cap. Either app fails to run on a clean device: 50% cap.
- License: **AGPL-3.0-or-later**, with credit to Anki (some Anki parts are BSD-3-Clause). State the exam (MCAT) at the top of the README.

## We trust honest numbers over flattering ones

"We calibrated memory but don't yet have data to prove the projected score" scores **higher** than a polished score you can't back up. Run fair tests that could show you wrong; report results that did not work.
