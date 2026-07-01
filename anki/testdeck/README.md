# MCAT Test Deck (development fixture)

A small, curated MCAT deck used to **test the Speedrun app** against [../PRD.md](../PRD.md). It is a development fixture, not a shipped product deck (the PRD non-goal "not a content vendor"). All cards are **originally authored** from standard MCAT knowledge (facts are not copyrightable); no copyrighted deck or AAMC/UWorld stems are reproduced (ToS / PRD 11.1). CARS is intentionally excluded as a flashcard deck (PRD 4.2).

## Contents

- `mcat_outline.json` - the enumerated AAMC content categories for the three science sections; the **coverage-map denominator** (`covered/total`).
- `memory_bio_biochem.csv`, `memory_chem_phys.csv`, `memory_psych_soc.csv` - memory Q&A (`Front,Back,Tags`), directly importable into Anki (the `#`-prefixed lines are Anki import directives).
- `performance_items.json` - 30 concepts x 2 reworded, **held-out** exam-style items (the paraphrase test set).
- `disconfirmer_cards.json` - 8 example Feature-2 disconfirmer cards (one is an answer-restating negative case).
- `build_deck.py` - builds `mcat_test_deck.apkg` from all of the above.
- `mcat_test_deck.apkg` - the built deck (244 notes), importable into desktop or the AnkiDroid fork.

Counts: **176 memory cards + 60 performance items + 8 disconfirmer cards = 244 notes.**

## Tag taxonomy

Hierarchical `::` tags, so the per-topic mastery query (`rslib` `topic_mastery`, PRD Section 8) rolls leaves up to category, section, and `MCAT` totals via `include_descendants`:

```
MCAT::<Section>::<ContentCategory>::<Topic>
e.g. MCAT::BioBiochem::1A::AminoAcids
```

Cross-cutting tags:

- `concept::<id>` - links a base memory card (also tagged `paraphrase::source`) to its held-out performance items.
- `perf::paraphrase`, `variant::1|2` - mark the reworded exam-style items.
- `holdout::performance` - performance items are kept **out of the studied memory set**; used for the performance bridge and paraphrase test.
- `notetype::disconfirmer`, `disconfirmer::valid|invalid` - the Feature-2 cards (`invalid` = the answer-restating negative case).

## Note types

- **Basic** (built-in): `Front`, `Back` - memory cards.
- **Speedrun Performance Item**: `ConceptId, Stem, OptionA-D, Correct, Rationale, Variant` - paraphrase/exam-style MC items.
- **Speedrun Disconfirmer** (PRD 6.1): `Provenance, Principle, OriginalCoverStory, SwappedCoverStory, Trap, Disconfirmer, BoundaryCase`.

## Held-out split

The 30 base concepts each have a studied memory card (`paraphrase::source`) and two reworded items tagged `holdout::performance`. The reworded items share only the underlying principle, not wording, so:

- **memory** is measured from the base cards (FSRS reviews), and
- **performance** is measured on the held-out reworded items,

letting the paraphrase test (spec 7d / PRD AC4) compare card recall vs reworded accuracy. Because the wording is disjoint, the leakage check (7e) should find no overlap between the studied set and the held-out set.

## Deliberate coverage gaps

Coverage is partial so the coverage map and give-up rule have something to act on: **24 of 31** content categories are covered (**77%**), and Psych/Soc is the thinnest section.

- BioBiochem 8/9 (omits 2B prokaryotes/viruses)
- ChemPhys 8/10 (omits 4D light/sound, 5C separations)
- PsychSoc 8/12 (omits 7C attitude change, 8A self-identity, 9B demographics, 10A social inequality)

## How the deck tests each feature

- **Coverage map (PRD 5.4 / spec 7c):** `mcat_outline.json` is the denominator; deck tags are the numerator; the gaps make coverage < 100% with a thin Psych/Soc section.
- **Mastery query (PRD Section 8 / `topic_mastery`):** the `::` tags give per-topic mastered count and average recall, with section roll-up.
- **Memory score (PRD 5.1):** the 176 basic cards generate FSRS reviews for calibration.
- **Performance bridge + paraphrase test (PRD 5.1 / 7d):** 30 concepts x 2 held-out reworded items.
- **Give-up rule (PRD 5.3):** the held-out split plus coverage gaps make it easy to sit above/below the thresholds.
- **Feature 2 (PRD Section 6):** the disconfirmer note type and examples (incl. the answer-restating negative case) exercise authoring and disconfirmer validation.

## Build / import

Build the `.apkg` with the repo's built Python environment, from the anki repo root:

```bash
out/pyenv/Scripts/python testdeck/build_deck.py     # Windows
out/pyenv/bin/python testdeck/build_deck.py         # macOS/Linux
```

Then import `mcat_test_deck.apkg` via File > Import in the desktop app (or the AnkiDroid fork). The three `memory_*.csv` files can also be imported directly (Basic note type; the header directives set the deck and tags column) without running the script.
