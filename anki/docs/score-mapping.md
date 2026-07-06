# Readiness score mapping (spec section 9 Step 3)

This is the single authoritative description of how Speedrun turns held-out **performance**
into a projected **MCAT total**, with a range. It matches the implementation in
[ts/routes/speedrun/+page.svelte](../ts/routes/speedrun/+page.svelte) (`computeProjected`)
and the offline reproduction in [testdeck/score_mapping.py](../testdeck/score_mapping.py)
(artifact `docs/eval-artifacts/score-mapping.json`).

## Inputs

Per **section**, from the engine's Performance lane (only sections with graded held-out
exam-style items):

- `accuracy` - held-out performance accuracy in `[0, 1]`,
- `low` / `high` - the section's 95% Wilson bounds on that accuracy.

Readiness is only computed when the give-up gate is satisfied (>= 200 graded reviews AND
>= 50% coverage); otherwise no number is shown (see PRD 5.3).

## Method

1. **Section scaled score.** Map each covered section's accuracy linearly onto the official
   MCAT section band `[118, 132]`:

   ```
   section_score = 118 + accuracy * (132 - 118)
   ```

   Do the same with the section's Wilson `low` / `high` to get the section score band.

2. **Sum to the total scale.** The four MCAT sections each score `[118, 132]` and sum to the
   total `[472, 528]`. Sum the covered sections' scaled scores.

3. **Impute uncovered sections (stated assumption).** Sections without performance data yet
   - most importantly CARS, which is out of scope as a flashcard deck - are imputed at the
   **mean scaled score of the covered sections**, so the total stays on the real 472-528
   scale. This is a deliberate, disclosed assumption, not a measurement: it says "assume the
   uncovered sections look like your covered ones." The `coveredSections` count is available
   so the UI can flag how much of the projection is imputed.

4. **Range, not a point.** The projected total is reported as `score (low-high)`, where the
   bounds are the summed (and imputed) section Wilson bounds. The range widens when fewer
   items back a section, so the projection never implies more certainty than the data
   supports.

Equal-weighting the sections (each band is equal on the MCAT scale) is the correct weighting
for this scale; note that with all covered sections at the same accuracy, this reduces to the
simple linear map `472 + accuracy * 56`, so the earlier linear implementation was a special
case of this method.

## Worked example

Three covered science sections at accuracies 0.62 / 0.50 / 0.48 (Bio/Biochem, Chem/Phys,
Psych/Soc), CARS uncovered:

- section scores: `126.7`, `125.0`, `124.7`; mean `125.5`
- total = `126.7 + 125.0 + 124.7 + 125.5 (imputed CARS)` = **502** (within 472-528)
- the range comes from summing the sections' Wilson bounds the same way.

(`score_mapping.py` recomputes this from the current `performance.json` artifact when
present, so the number in the report is generated.)

## Honesty / limits

- This is a **display-layer index** derived from the engine's validated Performance score.
  It is **not** validated against real MCAT results - that anchoring (section 9 Step 4) needs
  students with both study history and practice-test scores over time, and is out of scope.
- The CARS imputation is an assumption; a deck that skips CARS cannot honestly claim a CARS
  score, so the projection says so (imputed at the covered mean) rather than inventing one.
- Because performance itself is measured on held-out items and the give-up rule gates the
  whole thing, the projection abstains rather than guessing when data is thin.
