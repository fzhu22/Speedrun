# Speedrun

**A desktop + mobile study app built on a fork of Anki, for one exam: the MCAT.**

Exam: **MCAT** - total score 472-528, four sections each scored 118-132.

Speedrun shares **one engine** (Anki's Rust backend, `rslib`) across a desktop app
(a fork of [Anki](https://github.com/ankitects/anki)) and a phone companion (a fork
of [AnkiDroid](https://github.com/ankidroid/Anki-Android)). Reviews and progress sync
between them. It measures **three separate things**, each reported with a range and a
give-up rule, and never blends them into one number:

- **Memory** - the chance the student recalls a taught fact right now (FSRS), shown
  with a 95% range that narrows as more cards are reviewed.
- **Performance** - the chance the student answers a new, exam-style question correctly
  (abstains until exam-style items exist).
- **Readiness** - a projected MCAT score with a likely range, withheld below an
  evidence floor (coverage + review count).

## The honesty rule

The app refuses to show a readiness score unless it can also show the evidence behind
it, the missing data, the calibration history, the likely range, and the single best
next thing to study. A confident number without those is a guess in a nice font. The
give-up rule is explicit and enforced in the engine (default: readiness abstains below
50% coverage or under 200 graded reviews).

## Repository layout (monorepo)

This repository combines both apps so they can be cloned and reviewed together:

- `anki/` - the **desktop app** and the **shared Rust engine** (`rslib`), Python
  bindings (`pylib`), the protobuf boundary (`proto`), the Qt desktop UI (`qt`), and
  the web/Svelte frontend (`ts`). Speedrun's engine and features live here.
- `Anki-Android/` - the **mobile app** (AnkiDroid fork). It runs the same Rust engine
  via a locally built `rsdroid` backend and renders the same shared dashboard.
- `mcat-anki-learning-science-features/` - the project's BrainLift research and the
  sequenced build plan (learning-science positions and anti-patterns the build follows).
- `SYNC.md` - self-hosted two-way sync server setup (a self-hosted `anki-sync-server`).
- `backend_setup.sh`, `backend_build.sh`, `backend_fixanki.sh`, `backend_wire.sh`,
  `mobile_sync.sh` - helper scripts that cross-compile the shared Rust engine into the
  mobile `rsdroid` backend (WSL/Linux) and wire it into the AnkiDroid build.
- `decks/` - sample/exported decks.

## The Rust engine change (spec 7a)

The genuine engine change is a read-only per-topic **mastery query**,
`StatsService.TopicMastery`, added beside the `extract_fsrs_retrievability` SQLite
function it depends on. It returns, per topic (tag), the number of cards, how many are
mastered, how many are reviewed, and the average FSRS recall - fast enough to power the
dashboard on 50,000 cards. It ships to the phone for free because it lives in the shared
engine.

- Full write-up, rationale ("why Rust, not Python"), the list of upstream files touched,
  merge-risk assessment, tests, and the benchmark:
  [anki/docs/rust-change-topic-mastery.md](anki/docs/rust-change-topic-mastery.md).
- Tests: 4 Rust unit tests in [anki/rslib/src/stats/mastery.rs](anki/rslib/src/stats/mastery.rs)
  (including a read-only/undo/determinism proof) plus a Python-calls-Rust test in
  [anki/pylib/tests/test_topic_mastery.py](anki/pylib/tests/test_topic_mastery.py).
- The dashboard data assembly (the three scores, coverage roll-up, prerequisite-aware
  plan, per-family fading, and the memory range) lives in
  [anki/rslib/src/speedrun/dashboard.rs](anki/rslib/src/speedrun/dashboard.rs), with the
  shared UI at [anki/ts/routes/speedrun/+page.svelte](anki/ts/routes/speedrun/+page.svelte).

## Building

### Desktop (`anki/`)

Prerequisites are per-platform (Rust, MSYS2/Ninja on Windows): see
[anki/docs/development.md](anki/docs/development.md) and the platform pages
([Windows](anki/docs/windows.md) / [Mac](anki/docs/mac.md) / [Linux](anki/docs/linux.md)).
The source path must not contain spaces.

- Run from source (dev): from `anki/`, `.\run` (Windows) or `./run`.
- Run all tests/checks: `tools\ninja check` (Windows) or `./ninja check`.
- Run just the engine-change tests: `cargo test -p anki topic_mastery` and
  `cargo test -p anki speedrun`.
- Build an installer: `tools\build-installer.bat` (Windows) / `tools/build-installer`.
  Output goes to `anki/out/installer/dist/` (an MSI on Windows, a .dmg on macOS, a
  tarball on Linux).

### Mobile (`Anki-Android/`)

The phone app runs the **same** Rust engine (including the `topic_mastery` change) via a
locally built `rsdroid` backend:

1. Cross-compile the shared engine into the mobile backend (WSL/Linux): run
   `backend_setup.sh` then `backend_build.sh` / `backend_wire.sh` (these clone
   `Anki-Android-Backend`, build `librsdroid` from `anki/`, and place the AAR).
2. `Anki-Android/local.properties` sets `local_backend=true` so the build uses that AAR
   instead of the prebuilt Maven artifact.
3. Build + install the app: from `Anki-Android/`, `gradlew installPlayDebug`.

Sync between the two apps uses a self-hosted `anki-sync-server` - see [SYNC.md](SYNC.md).

## Running with AI off

Speedrun runs and gives scores with AI switched off; the AI lane is a keyless-fallback
add-on and is disabled for the Wednesday build (no model calls, no generated cards).

## License

This is a fork of Anki (by Ankitects Pty Ltd) and AnkiDroid (by the AnkiDroid Open
Source Team). Anki and AnkiDroid are licensed **AGPL-3.0-or-later** (some components are
BSD-3-Clause); Speedrun's modifications are likewise **AGPL-3.0-or-later**. Full credit
to Damien Elmes, the Anki contributors, and the AnkiDroid contributors. See
[anki/LICENSE](anki/LICENSE) and [Anki-Android/COPYING](Anki-Android/COPYING), and the
per-app overviews in [anki/SPEEDRUN.md](anki/SPEEDRUN.md) and
[anki/README.md](anki/README.md).
