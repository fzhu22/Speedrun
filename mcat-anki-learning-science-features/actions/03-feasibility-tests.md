# Feasibility Testing Protocol — Results (Step 5)

Three tests, cheapest first, on the revised MVP/load-bearing set (`02b-plan-revised.md`) + a planted decoy. Anti-sycophancy spine: each test can fail; cross-family decorrelation (Test 1 testers = GPT + Claude; Test 2 adversary = GPT ≠ the Claude-Opus planner; Test 3 = citation-checker vs PRIMARY sources). One decoy per run.

## Decoy self-check (S-Q — on-device semantic queue re-ranking) — CAUGHT ✅
A deliberately infeasible step dressed as concrete ("TF.js MiniLM in the card webview re-ranks the due queue + writes synced queue order"; $0/1×J/1 day). It ALSO reintroduces anti-pattern #2 (live on-device re-rank).
- **Test 1:** GPT **2/10**, Claude **1/10** — both flagged "obviously infeasible" cold.
- **Test 2:** **FAIL** — "NO BINDING CONSTRAINT (wish)"; depends on a nonexistent card-JS ability to access/reorder/persist the backend queue; violates the two-tier design + anti-pattern #2.
- **Test 3:** **INFEASIBLE** — both crux legs REFUTED vs source: custom-scheduling JS mutates the *current card only* at answer-time (`ts/reviewer/answering.ts`, `SchedulingContext{deck_name,seed}`); the queue is built backend-side (`rslib/src/scheduler/queue/mod.rs`); AnkiMobile has no review-screen synced write.
→ **The gate tracks feasibility, not polish.** Decoy logged to `rejected-actions.md`.

## Test 1 — Cold concreteness (0–10; two families, given ONLY the bare step)
| Step | GPT | Claude | avg | note |
|---|---|---|---|---|
| A1-S0 | 8 | 7 | 7.5 | specific APIs + matrix deliverable |
| A1-S1 | 7 | 7 | 7.0 | repo+change named (but see Test 3 wobble) |
| A1-S2 | 6 | 8 | 7.0 | interface + quality gates stated |
| A1-S3 | 7 | 7 | 7.0 | cross-client reveal-on-tap |
| A1-S4 | 5 | 4 | 4.5 | blocked on A1-S0 matrix (sequencing) |
| A2-S1 | 8 | 8 | 8.0 | all fields named, testable |
| A2-S2 | 5 | 5 | 5.0 | data model clear; UI substrate open |
| A2-S3 | 5 | 4 | 4.5 | mechanic concrete; "provably" needs review |
| A3-S1 | 6 | 6 | 6.0 | structure clear; domain/pilot logistics open |
| A3-S4 | 5 | 4 | 4.5 | flag format clear; trigger/gating undefined |
| A4-S1 | 7 | 6 | 6.5 | count+examples+constraint clear |
| A9-S1 | 6 | 8 | 7.0 | six fields + sources + no mobile-POST |
| A9-S2 | 6 | 5 | 5.5 | metric clear; **`psychometrics` lib dubious** |
| A8-S2a | 4 | 4 | 4.0 | unresolved fork + GAP-5 ramp policy |
| A8-S2b | 6 | 5 | 5.5 | named sub-tasks; an epic, not a step |
| **S-Q (decoy)** | **2** | **1** | **1.5** | **INFEASIBLE** |

## Test 2 — Binding constraint + pre-mortem (GPT adversary, decorrelated)
- **PASS (real, checkable binding constraint):** A1-S0, A1-S3, A1-S4, A2-S1, A2-S2, A3-S4, A9-S1, A9-S2.
- **WEAK (constraint real but estimate/QA shaky):** A1-S1 (first-fork-build + tested-search both in 0.5–1 day), A1-S2 (production-safe backup/resume/pagination optimistic), A2-S3 ("provably swapped" needs reviewer), A3-S1 (independent QA + pilot-sort under-budgeted for a hackathon), A4-S1 (independent-review calendar shaky).
- **FAIL:** A8-S2a (depends on A8-S1 whose ramp policy is GAP-5 — unresolved), A8-S2b (branch ambiguity + GAP-5 + unsettled product fork), S-Q (decoy).

## Test 3 — External verification + efficacy (citation-checker vs PRIMARY sources)
9 FEASIBLE-CONFIRMED · 5 FEASIBLE-PLAUSIBLE · 1 RISKY · 0 INFEASIBLE (real steps); decoy INFEASIBLE.
- **FEASIBLE-CONFIRMED:** A1-S0, A1-S1, A1-S2, A1-S3, A1-S4, A2-S1, A2-S2, A9-S1, A9-S2.
- **FEASIBLE-PLAUSIBLE (efficacy pends a pilot/RCT — PROXY-ONLY):** A2-S3, A3-S1, A3-S4, A4-S1, A8-S2a.
- **RISKY (binding constraint CONTESTED):** A8-S2b — native per-card-DR write is **unmerged** (jhhr draft) and a **new schema column breaks stock-client + AnkiWeb sync**; only the customData-targeting variant preserves sync (collapsing it into A8-S2a). Keep ONLY behind its 6-step DoD + FSRS-integrity regression + an explicit stock-sync decision gate.
- **Two correction flags (Test 3):**
  1. **A1-S1 premise wobble:** the "mandatory real Rust change = `extract_custom_data` SQLite search/column" **ALREADY EXISTS in mainline** (`rslib/src/storage/sqlite.rs` registers the scalar fn; `has-cd:` / `prop:cdn:` already parse in `rslib/src/search/parser.rs`). Building it is CONFIRMED but **nearly a no-op** → it does NOT satisfy the project's "make a genuine engine change" requirement. The genuine Rust change must be re-selected (lead candidate = A8-S2b's customData-targeting native per-card-DR write — real rslib work that preserves stock sync). → **Open decision.**
  2. **A9-S2 library:** prefer `girth` (real, MIT) + `scipy.stats` / a direct corrected-point-biserial formula; drop the unverified `psychometrics` package name.
- **Efficacy ceiling (expected, matches the BrainLift's domain ceiling):** the feature→MCAT-outcome link is OBSERVATIONAL (the one applied anchor, Wothe Step-2-CK, is null), so the content/learning steps (A2-S3, A3-S1/S4, A4-S1, A8-S2a) are PROXY-ONLY by design — efficacy resolves at the volume-matched pilot/RCT, while the *feasibility* binding constraints all hold vs primary source (except A8-S2b).

## Readiness tiers (per step) — consolidated
- **Ready** (T1 pass · T2 real constraint · T3 FEASIBLE-CONFIRMED): **A1-S0, A1-S2, A1-S3, A1-S4** (sequence after A1-S0), **A2-S1, A9-S1, A9-S2** (with the `girth`+scipy fix). A1-S1 **build = Ready**; A2-S2 **build = Ready** (ship gated on legal).
- **Plausible** (feasible; efficacy pends a pilot/measurement — T3 FEASIBLE-PLAUSIBLE): **A2-S3, A3-S1, A3-S4, A4-S1, A8-S2a** (write mechanism plausible; ramp policy is GAP-5). The deferred content/feature steps that share this pattern (A5-S1/S2/S3, A6-S2/S3, A7, A9-S3/S4, A10-S5, A12-S2) inherit Plausible-pending-pilot.
- **Risky** (binding constraint contested; keep only with mitigation + decision gate): **A8-S2b** — mitigation = target customData (not a new column) + the 6-step DoD + FSRS-integrity regression; decision gate = stock-sync vs own-infra.
- **Needs-Decision** (feasible, but rests on a human input the plan can't resolve):
  - **The genuine real-Rust-change selection** (A1-S1's chosen change is a no-op; pick A8-S2b-customData or another novel rslib change).
  - **A8 exam-date DR ramp policy** (GAP-5: curve shape + cap schedule) — A8 is **BLOCKED** until resolved (a gap-filling research pass, not a guess).
  - **iOS/sync forks** (A1-S5a self-host = §13+GDPR; A1-S6 iOS path) and the **legal-review quote gate** (A2-S2 ingestion, A10 DPA/GDPR, A11 CARS license = GAP-1).
  - **A11 CARS** build-vs-integrate (GAP-1: JW partnership + Khan/AAMC reuse license).
- **BLOCKED** (load-bearing action with NO execution-ready step until a gap closes): **A8 (exam-date DR ramp)** — pending GAP-5 ramp policy; the *write path* (A8-S2a) is feasible, but the *policy* is unspecified, so no step ships until the ramp curve/cap is set.

## Net
All real MVP steps clear the bar (Test 1 pass + Test 2 real binding constraint + Test 3 holds or partly-supported). Only the decoy is INFEASIBLE; A8-S2b is RISKY (kept behind a gate); A8 is BLOCKED pending GAP-5; two corrections (real-Rust-change re-selection + the A9-S2 library) feed the editor. Converges to ONE sequenced plan with the genuine build-vs-buy forks (iOS, sync, AI model, content build-vs-hire, CARS, the real-Rust-change) presented as Needs-Decision.
