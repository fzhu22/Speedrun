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

## Getting started (for testers)

You need two things on each device: the **app**, and the **shared sync login** (so the
desktop and phone show the same cards). You do **not** configure any servers or API keys
- the self-hosted sync server URL and the AI service are already baked into the builds.

From the maintainer, get:

- the **desktop installer** (`anki-*-win-x64.msi` on Windows - the Speedrun build is a
  fork, so it installs as "Anki") and the **Android app** (`AnkiDroid-play-*-debug.apk`) -
  these are attached to the repo's **Releases** (they are not committed to the repo). Prefer
  to build them yourself? See [Building from source](#building-from-source-developers).
- your **sync username + password** (the shared self-hosted sync account - this is *not*
  an AnkiWeb account).

### Desktop (Windows)

1. **Install & launch:** run the `anki-*-win-x64.msi` installer, then launch **Anki** (the
   Speedrun build) from the Start menu. (Or run from source: from `anki/`, `.\run`.)
2. **Sign in to sync:** click **Sync** (top-right) and log in with the sync
   **username/password** you were given. The server URL is already filled in and locked
   under `Tools > Preferences > Syncing`, so there is nothing to type there.
3. On the **first sync**, choose **Download from server** to pull the shared MCAT deck.
4. **Open the dashboard:** `Tools > Speedrun Dashboard` (the three scores, coverage map,
   and single best next thing to study).

### Mobile (Android phone or emulator)

1. **Install the APK:** pick the file matching the device - `arm64-v8a` for most phones,
   `x86_64` for an emulator.
   - On a phone: allow "Install unknown apps" for your browser/file manager, then open the
     `.apk`.
   - On an emulator or via USB: `adb install AnkiDroid-play-x86_64-debug.apk`.
2. **Sign in to sync:** `Settings > Sync > AnkiWeb account` and log in with the **same**
   sync username/password. The custom sync server is already enabled, filled in, and
   locked under `Settings > Sync > Custom sync server`.
3. On the **first sync** (the circular-arrows icon), choose **Download from server**.
4. **Open the dashboard:** nav drawer (the ☰ menu, top-left) -> **Speedrun**.

### Using it

- Study a deck; your grades feed the **Memory** score (FSRS). Miss an application-style
  card and you'll get the disconfirmer prompt.
- The three scores never blend, and **Readiness** stays hidden until there's enough
  evidence (>=50% coverage and >=200 graded reviews) - that's the honesty rule, not a bug.
- **AI** (card-type classification + severe-test hints) works out of the box through a
  hosted proxy - no API key needed on your side. Toggle it under
  `Tools > Speedrun AI Settings...`, or turn individual features on/off for ablation under
  `Tools > Speedrun Study Features...`.
- **Sync tip:** Anki forces a one-directional choice if both devices changed since the
  last sync, so **sync right after each study session** on each device to avoid conflicts.
  Full sync details are in [SYNC.md](SYNC.md).

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

## Building from source (developers)

Testers can skip this section - use the prebuilt installer/APK from Releases (see
[Getting started](#getting-started-for-testers)). Build from source only if you're
modifying the app.

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
3. Build + install the app: from `Anki-Android/`, `gradlew installPlayDebug` (installs to
   a connected device/emulator), or `gradlew assemblePlayDebug` to produce shareable APKs
   in `Anki-Android/AnkiDroid/build/outputs/apk/play/debug/` (split per ABI).

Sync between the two apps uses a self-hosted `anki-sync-server` - see [SYNC.md](SYNC.md).

## AI (optional, on by default)

AI runs through a hosted proxy that holds the OpenAI key **server-side**, so no API key
ships in the app and testers configure nothing. The AI lane only classifies card types and
offers severe-test hints - it never writes cards and never grades. If the proxy is
unreachable, or you switch AI off (`Tools > Speedrun AI Settings...`), every AI step
degrades to a deterministic fallback (heuristic classification / template hint), so the app
and all three scores work unchanged. Proxy service + deploy notes:
[anki/docs/aiproxy/](anki/docs/aiproxy/).

## License

This is a fork of Anki (by Ankitects Pty Ltd) and AnkiDroid (by the AnkiDroid Open
Source Team). Anki and AnkiDroid are licensed **AGPL-3.0-or-later** (some components are
BSD-3-Clause); Speedrun's modifications are likewise **AGPL-3.0-or-later**. Full credit
to Damien Elmes, the Anki contributors, and the AnkiDroid contributors. See
[anki/LICENSE](anki/LICENSE) and [Anki-Android/COPYING](Anki-Android/COPYING), and the
per-app overviews in [anki/SPEEDRUN.md](anki/SPEEDRUN.md) and
[anki/README.md](anki/README.md).
