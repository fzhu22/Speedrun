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

This is a fork of [Anki](https://github.com/ankitects/anki) by Ankitects Pty Ltd,
vendored into the Speedrun monorepo (the desktop app + shared engine live under `anki/`,
the mobile app under `Anki-Android/`). To pull in future Anki changes, add Anki as a git
remote and merge from it.

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
- `pylib/anki/speedrun/` - the concept knowledge graph (AAMC-outline spine, coverage
  map, prerequisite-aware planning, edge validation, the study-planning benchmark), the
  **pretest-first** note type (`pretest.py`, SPOV 13: forced guess -> reveal -> feedback
  via the native type-in field), the `Speedrun Disconfirmer` note type
  (`disconfirmer.py`), the support-fading ladder (`fading.py`, per-family, conservative,
  reinstates support on any miss), the original sample content + deck seeding
  (`sample_content.py`, `seeding.py`), the **performance lane** (`performance.py`: the
  memory->performance model, the incremental-validity gate, the paraphrase test and the
  leakage check; `ai_items.py`: gated AI item generation), and the (parked) AI lane
  (`ai.py`, `cardtype.py`, `ai_eval.py`, `anticrutch.py`) - all shipped as part of the
  `anki` library. No copyrighted decks are bundled; sample cards are original and labeled
  `[Sample]`.
- `qt/aqt/speedrun/` - the desktop integration: the readiness dashboard, the guided
  Miss->Card authoring dialog, the fading driver that updates the per-family rung from
  real study-card reviews and writes it back as a syncable `speedrun_rung::` tag
  (`state.py`), the AI Tools (settings, classify, eval; `ai_ui.py`), and the note-type /
  fading / key hooks. The pretest-first study experience lives in the card template
  itself (no desktop modal). All learning features run **in the study loop, on by
  default**: the in-review disconfirmer prompt (`review.py`) fires on a miss, and the AI
  card-type classification runs in the background on deck open (`autoclassify.py`) to gate
  it - falling back to the deterministic heuristic when AI is off / keyless. The
  **Performance** score is separately gated: Tools -> "Fit Performance Model"
  (`perf_fit.py`) fits the model from the review log and only enables the dashboard's
  Performance column once it beats recall out-of-sample; "Generate Items from Source"
  runs AI item generation behind the eval gate.
- `mcat-anki-learning-science-features/` - the project's BrainLift research and the
  sequenced execution plan (the learning-science positions and anti-patterns the
  build follows).
- `.cursor/skills/speedrun-mcat/` - the agent skill that keeps the product spec, the
  Anki brownfielding constraints, and the validated learning-science positions in
  context while building.

## Building

Build instructions for the desktop app are in [docs/development.md](./docs/development.md)
and the platform pages ([Windows](./docs/windows.md) / [Mac](./docs/mac.md) /
[Linux](./docs/linux.md)). From this folder: `./run` (or `.\run` on Windows). Build an
installer with `tools/build-installer` (`tools\build-installer.bat` on Windows), which
writes an MSI/.dmg/tarball to `out/installer/dist/`. For the phone app and two-way sync,
see the top-level [../README.md](../README.md) and [../SYNC.md](../SYNC.md).

## Status / TODO

The following are tracked deliverables (see the spec in
`../mcat-anki-learning-science-features/`):

- [x] The real Rust engine change: the read-only `topic_mastery` query (4 Rust unit
      tests + 1 Python-calling test; undo preserved; no collection corruption), with the
      upstream files-touched list in
      [docs/rust-change-topic-mastery.md](./docs/rust-change-topic-mastery.md).
- [x] The three separately-gated scores on the shared dashboard: memory (with a 95%
      range that narrows with more reviews), performance (abstains - no exam-style items
      yet), and readiness (abstains below the coverage/review give-up line).
- [x] The phone companion sharing the engine, with two-way sync (self-hosted
      `anki-sync-server`; see [../SYNC.md](../SYNC.md)).
- [ ] Held-out evaluation (memory calibration / Brier or log loss), the leakage check,
      and the study-feature ablation test - the Sunday "prove it" deliverables.
