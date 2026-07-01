# Anki Brownfielding (Rust engine)

This is a brownfield project: change Anki's **Rust engine**, not just the Python/Qt screens. The engine is shared, so a Rust change ships to desktop AND the phone build.

## Repo layout (ankitects/anki)

- `rslib/` — the Rust engine (collection, scheduler, search, storage). FSRS lives in the separate `fsrs-rs` crate (BSD-3).
- `pylib/` — Python bindings; `rsbridge` exposes Rust to Python via **PyO3**.
- `proto/` — protobuf service/message definitions; backend methods are declared here and generated for both Rust and Python.
- `ftl/` — translations. `qt/` — desktop UI (Python). `ts/` — web/reviewer frontend.
- Mobile: AnkiDroid (Kotlin + JNI over the Rust backend) and AnkiMobile (iOS, Rust via C-FFI).

## How a Rust change reaches Python

1. Add/extend a message + service method in `proto/`.
2. Implement it in `rslib/` (e.g. a new search, scheduler order, or query).
3. It is exposed to Python through the protobuf service + PyO3 `rsbridge`; call it from `pylib/anki`.

## Requirements for the Rust change (spec 7a)

- **>=3 Rust unit tests** + **1 test that calls it from Python**.
- Prove **undo still works** and the collection does **not** corrupt.
- A one-page note on **why this belongs in Rust, not Python**.
- A list of **upstream files touched** and how hard a future merge would be.
- It must still work on the **phone build**.

Candidate changes (pick one of comparable weight):
- **Points-at-stake queue**: new review order sorting due cards by topic weight x student weakness; add a protobuf message, call from Python.
- **Topic-aware scheduling**: bring weak-topic cards back sooner while keeping FSRS intervals valid and undo working.
- **Mastery query**: per-topic mastered count + average recall, fast enough to power the dashboard on 50,000 cards.

## Real-Rust-change CORRECTION (from action-plan.md)

The `extract_custom_data` SQLite search/column **already exists in mainline** (`rslib/src/storage/sqlite.rs` registers the scalar fn; `has-cd:` / `prop:cdn:` already parse in `rslib/src/search/parser.rs`). Building it is a near-no-op and does **NOT** satisfy "make a genuine engine change." Lead candidate for a genuine change: a **native per-card desired-retention WRITE that targets `customData`** (real rslib + protobuf + migration + sync work) — NOT a new schema column, which would break stock-client + AnkiWeb sync.

## Substrate constraints (code-verified — do not over-promise)

- Custom scheduling is **global JavaScript** that sees only `SchedulingContext{deck_name, seed, decay, desired_retention}`, runs at answer-time on the current card, and **re-weights one card's next interval — it cannot reorder the backend-built due queue**. Live on-device semantic queue re-ranking is impossible (this is why every concept-aware feature must be two-tier; see learning-science.md SPOV 4).
- `customData` is **<=100 bytes total / 8-byte keys**; never exceed `validate_custom_data` (silent truncation). Tags are the durable cross-client channel for anything larger.
- The v3 scheduler **cannot be monkey-patched**; per-card desired-retention write is reachable only via add-on/fork.
- **AnkiMobile (iOS): no add-ons** and no synced review-flow write. **AnkiDroid: no Python** (JS only); the `AnkiDroidJS` get/set-tags API is the only blessed synced write from the review flow.
- Anki is **single-writer** (`with_col`); third-party writes while a device has unsynced changes force a full sync / lost changes. Note-type field/template edits are schema-modifying -> forced full sync (freeze fields early).
- FSRS is the strongest part — **layer over it, do not reimplement it**. PR #4880 (merged) exposes decay + desired retention to custom scheduling; per-deck DR shipped in 25.09.

## Speed / reliability targets (spec 10) — `make bench` reports p50, p95, worst

- Button press acknowledged: p95 < 50 ms. Next card after grading: p95 < 100 ms.
- Dashboard first load: p95 < 1 s. Dashboard refresh: p95 < 500 ms, no screen freeze.
- Sync of a normal session: < 5 s. Cold start: < 5 s desktop / < 4 s phone. Nothing freezes the UI > 100 ms.
- Crash test: kill mid-review 20x; **zero corrupted collections** on both platforms.

## Build note

Build on **WSL/Linux/Mac, not Windows/PowerShell**; clone to a **space-free path**; pinned Rustup + uv + Ninja + `just` (`./run` builds rslib+rsbridge; `tools/build` -> wheels). Use your own name/logo (the Anki name is trademarked; the logo is AGPL).
