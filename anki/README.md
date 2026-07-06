# Speedrun (a fork of Anki) - MCAT desktop app + shared engine

**Speedrun** is a desktop + mobile study app built on a fork of Anki for **one exam: the
MCAT** (scored 472-528, four sections each 118-132). This directory (`anki/`) holds the
**desktop app** and the **shared Rust engine** (`rslib`) that both the desktop and the phone
companion (an AnkiDroid fork under `../Anki-Android/`) run; reviews and progress sync between
them via a self-hosted server.

It measures **three separate things**, each reported with a range and a give-up rule, never
blended into one number:

- **Memory** - the chance you recall a taught fact now (FSRS), with a 95% range.
- **Performance** - the chance you answer a new exam-style question correctly (abstains until
  enough graded items exist).
- **Readiness** - a projected MCAT score with a likely range, withheld below an evidence floor
  (default: under 50% coverage or under 200 graded reviews). That is the honesty rule, and it
  is enforced in the engine.

## Speedrun docs (start here)

- **[SPEEDRUN.md](./SPEEDRUN.md)** - project overview, status, repository layout, license.
- **[../README.md](../README.md)** - the full desktop + mobile monorepo guide (testers, both-app
  build steps, sync).
- **[docs/architecture.md](./docs/architecture.md)** - how the pieces fit: the two-tier engine,
  the three scores, the AI lane, and the shared dashboard.
- **[docs/model-descriptions.md](./docs/model-descriptions.md)** - the memory / performance /
  readiness models and their give-up rules.
- **[docs/rust-change-topic-mastery.md](./docs/rust-change-topic-mastery.md)** - the engine
  change (spec 7a): what it is, why Rust, files touched, tests, benchmark.
- **[docs/files-touched.md](./docs/files-touched.md)** - every upstream file Speedrun modified,
  with merge-risk notes.
- **[docs/eval-results.md](./docs/eval-results.md)** - the generated evidence report
  (calibration, performance, score mapping, AI, injection, sync, ablation, crash).
- **[docs/ai-lane.md](./docs/ai-lane.md)** - what the AI does and its held-out eval.

## Build & run the desktop app (from `anki/`)

- Run from source (dev): `.\run` (Windows) or `./run`. Prereqs (Rust, MSYS2/Ninja on Windows):
  [docs/development.md](./docs/development.md), [docs/windows.md](./docs/windows.md) /
  [mac.md](./docs/mac.md) / [linux.md](./docs/linux.md). The source path must not contain spaces.
- All checks: `tools\ninja check` (Windows) / `./ninja check`.
- Engine-change tests only: `cargo test -p anki topic_mastery` and `cargo test -p anki speedrun`.
- Evidence: `just eval`, `just bench`, `just crash-test`, `just sync-test`.
- Installer: `tools\build-installer.bat` / `tools/build-installer` -> `out/installer/dist/`.

The mobile app and the shared-engine cross-compile live in the parent monorepo; see
[../README.md](../README.md) and [../SYNC.md](../SYNC.md).

This is a fork of [ankitects/anki](https://github.com/ankitects/anki); full credit to Anki and
its contributors. Speedrun's modifications are AGPL-3.0-or-later (see [LICENSE](./LICENSE)). The
original upstream Anki README follows.

---

# Anki

[![Build Status](https://github.com/ankitects/anki/actions/workflows/ci.yml/badge.svg)](https://github.com/ankitects/anki/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-dev--docs.ankiweb.net-blue)](https://dev-docs.ankiweb.net)

This repo contains the source code for the computer version of
[Anki](https://apps.ankiweb.net).

## About

Anki is a spaced repetition program. Please see the [website](https://apps.ankiweb.net) to learn more.

## Getting Started

### Contributing

Want to contribute to Anki? Check out the [Contribution Guidelines](./docs/contributing.md).

For more information on building and developing, please see [Development](./docs/development.md).

#### Contributors

The following people have contributed to Anki: [CONTRIBUTORS](./CONTRIBUTORS)

### Anki Betas

If you'd like to try development builds of Anki but don't feel comfortable
building the code, please see [Anki betas](https://betas.ankiweb.net/).

## License

Anki's license: [LICENSE](./LICENSE)
