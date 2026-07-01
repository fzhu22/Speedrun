# Speedrun Rust engine change: per-topic mastery query

This documents the genuine Rust engine change required by spec section 7a
("the Rust change"), implemented as the **mastery query** option:

> add a backend call that returns, per topic, how many cards are mastered and
> the average recall, fast enough to power the dashboard on 50,000 cards.

## What it does

A new read-only backend RPC, `StatsService.TopicMastery`, returns per topic
(an Anki tag) the number of cards, how many are mastered, how many have been
reviewed, and the average FSRS recall. It powers the dashboard, the coverage
map, and the memory side of the three scores.

Definitions (stated, per the honesty rule):

- **Topic** = a tag. Anki has no native "topic"; cards are grouped by their
  note's tags, and `::` denotes hierarchy (e.g. `MCAT::Biochem::Enzymes`).
- **Mastered** = a card in the Review state whose current FSRS retrievability is
  at or above the threshold (default 0.9).
- **Average recall** = mean FSRS retrievability over cards that have one
  (new/unreviewed cards are excluded). The query **abstains** (returns no
  average) for a topic with fewer than `min_cards_for_average` reviewed cards.

## Why this belongs in Rust, not Python

1. **It needs the engine's own SQL.** Retrievability is produced by the
   `extract_fsrs_retrievability` SQLite scalar function that rslib registers on
   the connection (`rslib/src/storage/sqlite.rs`). It is not exposed to Python.
   Computing the metric in one SQL pass beside that function is the natural home.
2. **Performance at 50k cards.** The query is a single scan of `cards` joined to
   `notes`, aggregated in Rust. Doing this in Python would mean either pulling
   every card/note across the PyO3 boundary (tens of thousands of crossings) or
   issuing per-tag queries (N+1). The Rust path meets the dashboard target
   (p95 < 1s; see the benchmark).
3. **It ships to the phone for free.** Because the logic lives in the shared
   rslib engine, the same call is available to the desktop, AnkiDroid (JNI), and
   AnkiMobile (C-FFI). A Python-only implementation would not exist on mobile.
4. **Read-only correctness.** The query never writes, so it records no undo step
   and cannot corrupt the collection (proven by a unit test). Keeping it in the
   engine keeps that guarantee close to the data.

## Upstream files touched and merge difficulty

All changes are additive; a future merge against upstream Anki is low risk.

- `proto/anki/stats.proto` — appended one `rpc` to `StatsService` and two new
  messages (`TopicMasteryRequest`, `TopicMasteryResponse`). Appending (not
  reordering) keeps existing service/method indices stable. *Merge risk: low.*
- `rslib/src/stats/mastery.rs` — new file (the query, helper, and tests).
  *Merge risk: none (new file).*
- `rslib/src/stats/mastery.sql` — new file (the single joined query).
  *Merge risk: none (new file).*
- `rslib/src/stats/mod.rs` — added one line, `mod mastery;`. *Merge risk: low.*
- `rslib/src/stats/service.rs` — added one trait method delegating to the
  inherent `Collection::topic_mastery`. *Merge risk: low.*
- `pylib/anki/collection.py` — added a `TopicMastery` alias and a thin
  `topic_mastery(...)` wrapper. *Merge risk: low.*
- `pylib/tests/test_topic_mastery.py` — new file (Python-calls-Rust test).
  *Merge risk: none (new file).*

The only codegen-coupled touch is the regenerated `StatsService` trait (from the
`.proto`); the new method is implemented for `Collection` like every existing
stats method.

## Tests (spec 7a: >=3 Rust unit tests + 1 Python test)

Rust unit tests in `rslib/src/stats/mastery.rs`:

- `aggregates_by_tag_and_counts_untagged`
- `applies_mastery_threshold_and_average_recall`
- `rolls_up_hierarchy_when_requested`
- `is_read_only_and_deterministic` (the undo / no-corruption proof: the undo
  counter is unchanged after the call, and repeated calls return identical
  results)

Run:

```bash
cargo test -p anki topic_mastery   # or: just test-rust
```

Python-calls-Rust test in `pylib/tests/test_topic_mastery.py` (uses
`getEmptyCol()`, adds a tagged note, and asserts the per-topic result):

```bash
just test-py    # or: pytest pylib/tests/test_topic_mastery.py
```

## Benchmark (spec 7h / speed targets 10)

`topic_mastery_benchmark` (ignored by default) builds a configurable deck
(default 50,000 cards), runs the query 20 times, and reports p50/p95/worst,
asserting p95 < 1s:

```bash
cargo test -p anki topic_mastery_benchmark -- --ignored --nocapture
# optional: TOPIC_MASTERY_BENCH_CARDS=100000 cargo test -p anki \
#   topic_mastery_benchmark -- --ignored --nocapture
```

This is the timing artifact for this change; it can be wired into a project-wide
`make bench` / `just bench` target alongside the other speed numbers.

## Undo and collection integrity

`topic_mastery` is read-only: it issues a single `SELECT` and never opens a
write transaction, so it pushes no undo entry and cannot corrupt the collection.
The `is_read_only_and_deterministic` test asserts the undo counter is unchanged
across a call.

## Build / regeneration note

Build and test under WSL/Linux/Mac, not Windows PowerShell (see `docs/linux.md`
/ `docs/mac.md`). Editing the `.proto` and running `./run` (or `just check`)
regenerates both the Rust `StatsService` trait and the typed Python wrapper
(`_backend.topic_mastery`), keeping service/method indices in sync.
