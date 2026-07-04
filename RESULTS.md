# Speedrun test results (summary)

High-level pass/fail. Full numbers + how to reproduce: [anki/docs/eval-results.md](anki/docs/eval-results.md)
(`just bench`, `just eval`, `just crash-test`). Measured on a Windows desktop dev machine.

| Spec | Test | Result | Status |
| --- | --- | --- | --- |
| 7h / 10 | Speed + memory on a 50k-card deck | answer p95 1.5 ms, next-card p95 0.2 ms, dashboard p95 150 ms, cold start 208 ms, 78.6 MB | PASS |
| 9 Step 1 | Memory calibration on held-back reviews | held-out RMSE 6.5%, log_loss 0.35 | PASS |
| 7d | Paraphrase test (memory vs performance) | recall 64.3% vs reworded 60.0% -> gap +4.3% | PASS (gap reported) |
| 7e | Leakage check | perf lane overlap 0.40 (<0.80); few-shot<->gold clean | PASS (clean) |
| 7e | AI card-type classifier | 95.2% vs 90.5% keyword / 61.9% vector; cutoff 80% | PASS |
| 7f | AI card check (gold set) | 59 generated -> 52 useful, 0 wrong, 7 duplicates blocked | PASS (cutoff) |
| 7g | Crash: 20x hard kill mid-review | 20/20 collections intact | PASS |
| 7g | Offline / AI-off | no fabrication, template fallbacks, dashboard still scores | PASS |
| 10 | Prompt injection (hidden text) | sanitizer strips markup/overrides; unit tests pass | PASS |
| 7b | Two-device sync + conflict rule | documented + live server healthy; run needs 2 devices | Manual |
| 8 | 3-version ablation (full/off/plain) | toggles + engine gates tested; A/B needs real learners | Manual |

Caveats: calibration/performance use synthetic-but-labelled review data (real-student
validation = 9 Step 4, not claimed); benchmark reports engine-call latency (phone numbers
to be measured on-device).
