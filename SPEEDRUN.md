# Speedrun

**A Desktop + Mobile study app built on a fork of Anki, for one exam: the MCAT.**

Exam: **MCAT** — total score 472-528, four sections each scored 118-132.

Speedrun shares one engine (Anki's Rust backend) across a desktop app and a phone
companion, and measures three separate things, each reported with a range (never a
single blended number):

- **Memory** — the chance the student recalls a taught fact right now (FSRS).
- **Performance** — the chance the student answers a new, exam-style question correctly.
- **Readiness** — a projected MCAT score on the 472-528 scale, with a likely range and
  a confidence note.

The app refuses to show a readiness score when it lacks the data to back it up (the
"give-up rule"), and never presents a number without the evidence, the missing-data
note, the calibration history, the range, and the single best next thing to study.

## Relationship to Anki

This is a fork of [Anki](https://apps.ankiweb.net) by Ankitects Pty Ltd.

- `origin` -> this repository (Speedrun)
- `upstream` -> https://github.com/ankitects/anki (for pulling in future Anki changes)

Full credit to Damien Elmes and the Anki contributors. See
[CONTRIBUTORS](./CONTRIBUTORS) and the upstream project.

## License

Anki is licensed under AGPL-3.0 (see [LICENSE](./LICENSE)); some components are
BSD-3-Clause. Speedrun's modifications are licensed **AGPL-3.0-or-later**, consistent
with the upstream license.

## Repository layout

- `rslib/` - the shared Rust engine (scheduler, collection, search, storage).
- `pylib/` - Python bindings; `rsbridge` exposes the Rust backend via PyO3.
- `proto/` - protobuf service/message definitions (the Rust <-> Python boundary).
- `qt/` - the desktop UI. `ts/` - the reviewer/web frontend.
- `mcat-anki-learning-science-features/` - the project's BrainLift research and the
  sequenced execution plan (the learning-science positions and anti-patterns the
  build follows).
- `.cursor/skills/speedrun-mcat/` - the agent skill that keeps the product spec, the
  Anki brownfielding constraints, and the validated learning-science positions in
  context while building.

## Building

Build instructions for the desktop app are in [docs/development.md](./docs/development.md)
and the platform pages ([Windows](./docs/windows.md) / [Mac](./docs/mac.md) /
[Linux](./docs/linux.md)). From the repo root: `./run` (or `.\run` on Windows).

## Status / TODO

The following are tracked deliverables (see the spec PDF and action plan in
`mcat-anki-learning-science-features/`):

- [ ] The real Rust engine change (3 Rust unit tests + 1 Python-calling test; undo
      preserved; no collection corruption) and the list of upstream files touched.
- [ ] The three-score models (memory calibration, performance, readiness mapping)
      with ranges and the give-up rule.
- [ ] The phone companion sharing the engine, with two-way sync.
- [ ] Held-out evaluation, leakage check, and the study-feature ablation test.
