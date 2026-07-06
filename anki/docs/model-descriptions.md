# Speedrun model descriptions

Speedrun reports three scores, all produced by the shared Rust engine and read by both the
desktop and phone builds: **Memory**, **Performance**, and **Readiness**. Each section below
states what the score means, how it is computed, when it declines to report a number (the
give-up rule), and how it is checked. The figures come from `just eval`; see
[eval-results.md](eval-results.md).

One idea is common to all three scores: a number is shown only when the data behind it is
sufficient. When it is not, the score abstains and says why, because a blank is more honest
than a confident guess.

## Memory

**What it measures.** How well you currently recall the cards you have already studied, as a
recall probability from 0 to 100%.

**How it is computed.** Memory is the FSRS scheduler the engine already uses to plan reviews.
Every reviewed card has an FSRS memory state, which gives its predicted recall at the current
time. Speedrun averages that recall across the cards in each content category, weighted by how
many cards have been reviewed, then rolls the categories up to each MCAT section and to a single
overall figure. Each estimate is shown with a 95% Wilson interval, so the display is a range
rather than one overly precise number. Implementation: `rslib/src/speedrun/dashboard.rs`, using
the per-topic recall from the topic-mastery pass.

**Give-up rule.** A content category with no reviewed cards has no recall to report, so it shows
a dash instead of a guess. A section takes its Memory score only from the categories that have
review history; if none do, the section abstains.

**How it is checked.** On a held-out split of reviews the model never trained on: calibration
error (RMSE across probability bins) 5.4%, Brier score 0.087, log loss 0.306. The small gap
between training and held-out error (2.8% to 5.4%) indicates the model is calibrated, not
overfit.

**Limit.** These numbers are measured on labelled synthetic review logs, not on one specific
student's history.

## Performance

**What it measures.** Whether you can answer exam-style questions correctly, reported per section
as an accuracy from 0 to 100%. It is kept separate from Memory on purpose: recalling a fact is
not the same as applying it under exam conditions.

**How it is computed.** For each section the engine fits a calibrated logistic model of the
probability of a correct answer, trained and evaluated on held-out, reworded items (an answer
counts as correct at ease 2 or better). Each section's accuracy is reported with a 95% Wilson
range. Implementation: `rslib/src/speedrun/performance.rs`.

**Give-up rule.** Performance stays off until the model earns its place. It must pass an
incremental-validity gate: at least 30 graded responses, and, in k-fold cross-validation, the
full model must beat a recall-only model by at least 0.02 AUC out of sample. If it cannot beat
"just use Memory", no Performance score is shown. Once the gate passes, an individual section
still needs at least 5 graded items before its accuracy appears; sections below that stay blank.

**How it is checked.** Held-out accuracy 60.0% on 60 reworded items (Brier 0.206). Out-of-sample
AUC 0.606 for the full model versus 0.534 for recall-only, a gain of 0.073 against the 0.02
gate. A leakage scan confirms the test items are not near-copies of studied text (maximum
overlap 0.40 against a 0.80 limit).

**Limit.** The responses used here are simulated with a planted skill to exercise the pipeline.
They are not real student answers.

## Readiness

**What it measures.** A single projected MCAT total on the official 472 to 528 scale, reported
as a point estimate with a range.

**How it is computed.** Each covered section's held-out Performance accuracy is mapped onto that
section's score band, 118 to 132, and the four sections sum to the total. A section with no data
yet (in practice CARS, which is out of scope as a flashcard deck) is filled in at the mean of
the covered sections; this is a disclosed assumption, not a measurement. The reported range is
the sum of the sections' Wilson bounds, so it widens when fewer items back a section. The full
method and a worked example are in [score-mapping.md](score-mapping.md). Implementation:
`computeProjected` in `ts/routes/speedrun/+page.svelte`, reproduced offline by
`testdeck/score_mapping.py`.

**Give-up rule.** Readiness is computed only when both conditions hold: overall coverage is at
least 50%, and the collection has at least 200 total reviews. Otherwise it abstains and gives
the reason, for example "coverage 30% < 50%" or "only 120 of 200 reviews".

**How it is checked.** On the current artifacts the projection is 505 (likely 493 to 515), from
three covered sections with one imputed (the range is the summed per-section Wilson bounds).

**Limit.** Readiness is a display-layer index built on top of Performance. It is not anchored to
real MCAT results; that validation would need students with both a study history and later test
scores, and is out of scope.
