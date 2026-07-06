# Speedrun test results (summary)

High-level pass/fail. Full numbers + how to reproduce: [anki/docs/eval-results.md](anki/docs/eval-results.md)
(`just bench`, `just eval`, `just crash-test`). Measured on a Windows desktop dev machine.

| Spec | Test | Result | Status |
| --- | --- | --- | --- |
| 7h / 10 | Speed + memory on a 50k-card deck | answer p95 1.6 ms, next-card p95 0.2 ms, dashboard refresh p95 422 ms, cold start 222 ms, 82.9 MB | PASS |
| 9 Step 1 | Memory calibration on held-back reviews | held-out RMSE 5.4%, log_loss 0.31, Brier 0.087 | PASS |
| 7d | Paraphrase test (memory vs performance) | recall 64.3% vs reworded 60.0% -> gap +4.3% | PASS (gap reported) |
| 7e | Leakage check | perf lane overlap 0.40 (<0.80); few-shot<->gold clean | PASS (clean) |
| 7e | AI card-type classifier | AI (gpt-4.1-mini) 86.5% vs 91.9% keyword / 59.5% vector; cutoff 80% PASS; does not beat keyword | PASS (cutoff) |
| 7f | AI card check (gold set) | 54 generated -> 49 useful, 1 wrong + 4 dup/bad blocked (never shipped); cutoff wrong<=0 | FAIL (cutoff); wrong card caught |
| 7g | Crash: 20x hard kill mid-review | 20/20 collections intact | PASS |
| 7g | Offline / AI-off | no fabrication, template fallbacks, dashboard still scores | PASS |
| 10 | Prompt injection (hidden text) | 5/5 attacks neutralized vs real gpt-4.1-mini; canary never leaked; forced correctness-flip held | PASS |
| 7b | Two-device sync + conflict rule | documented + live server healthy; run needs 2 devices | Manual |
| 8 | 3-version ablation (full/off/plain) | toggles + engine gates tested; A/B needs real learners | Manual |

Caveats: calibration/performance use synthetic-but-labelled review data (real-student
validation = 9 Step 4, not claimed); benchmark reports engine-call latency (phone numbers
to be measured on-device).
