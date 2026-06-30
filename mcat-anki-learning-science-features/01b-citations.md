# Citation Gate (Step 1b) — feature-layer DOK 1 verification record

**Scope:** the NEW feature-layer facts in the six raw lane files (parent BrainLift facts were already gated in `../mcat-anki-study-app/` and not re-verified).
**Headline:** Unusually clean. Every load-bearing/numeric/surprising/contested NEW claim resolved to a retrievable primary source and matched the figures — including all the 2026 arXiv IDs flagged as risky (2604.00142, 2605.21629, 2602.04347, 2602.14431), the 2025 LearnLM/Eedi ID (2512.23633), the FSRS-7 PR (21→35 params), and the OpenReview InfoTutor ID. **Nothing to DROP** (no hallucinations, fabricated numbers, or dead links). 5 FIXes applied before synthesis.

## Verified anchors (all exact unless noted)
- **Effect sizes:** self-explanation g=.55 (Bisra 2018); user-generated > premade d=0.45 memory / 0.29 application (Pan 2023); generation .40 (Bertsch 2007); testing g=0.50 weighted / 0.54 unweighted, near-zero (g=0.03) without feedback ≤50% (Rowland 2014); Donoghue & Hattie d=0.85 distributed / 0.74 testing + "mostly surface outcomes" caveat; interleaved math d=0.83 (Rohrer 2020) / d=1.21 (Taylor & Rohrer 2010); adaptive spacing up to 40% (Eglington & Pavlik 2020); personalized review +16.5%/+10% (Lindsey 2014); expertise-reversal d=0.505 / −0.428 (Tetzlaff 2025); seductive-detail −0.30 retention / −0.48 transfer (Rey 2012); overjustification d=−0.40 (Deci 1999); Levels+Badges+Leaderboards negative (Huang 2024); self-explanation prompts null/detrimental (McCarthy et al. 2018 — see FIX; Rittle-Johnson 2017).
- **Spaced education in medicine:** Kerfoot 2007 d=1.01 / 2009 2-yr d=0.35 / 2010 transfer of image-diagnosis — verified.
- **Anki↔exam (OBSERVATIONAL, confirmed non-randomized):** Deng 2015 (~1 Step-1 pt per ~1,700 cards, B=5.9e-4); Gilbert 2023 (+6.4–12.9% incl. CBSE +12.9%); Winter 2025 (≥9,390 mature cards → 71.56% vs 60.05%); the 11-study review (none randomized) = **Frappa et al. 2026** (see FIX).
- **Anki substrate (vs official docs):** Image Occlusion built-in since 23.10; custom scheduling = GLOBAL JavaScript; v3 scheduler can't be monkey-patched; rslib/fsrs-rs backend; FSRS-6 in 25.07 (decay w20, 21 params); per-deck DR in 25.09; front-side native-cloze HTML-conversion constraint; AnkiMobile no add-ons / AnkiDroid no Python add-ons (JS only). All verified.
- **Bleeding-edge (exists + says it; tags preserved):** LLM self-explanation +11.9pp transfer-explanation (Chen 2026); "faster completion, less learning" −17% unassisted (2026); contextual-bandit on skill gain +15.2% (De Kerpel 2026); LearnLM/Eedi +5.5pp, 76.4% drafts approved (2025); FSRS-7 PR 21→35 params; AI add-ons MyAnswerChecker / AnkiAIUtils / Anki AI Explainer exist as described; UWorld UAsk / RemNote / AnkiHub Smart Search = vendor claims (verified as claims, not efficacy).

## ⛔ DROP — NONE
No hallucinated/fabricated/dead claim.

## 🔧 FIX (applied to raw files)
1. **Anki review miscite:** "Rana et al. 2026" → **Frappa et al. 2026** (Med Sci Educ 36:1015–1025); DOI + figures otherwise correct. (raw-advocate.md) ✅
2. **"Metacognitive Overload!" author:** McNamara et al. 2018 → **McCarthy et al. 2018** (McNamara is senior, not first, author); soften "removed in future versions." (raw-adversary.md) ✅
3. **Rowland 2014:** clarify g=0.54 = unweighted mean; **headline weighted ES = g=0.50**; the load-bearing "g=0.03 without feedback ≤50%" is exact. (raw-advocate.md) ✅
4. **Step-2-CK null:** cite the primary study **Wothe et al.** (252.5 vs 247.0, p=0.440), not the practitioner relay. (raw-frontier.md) ✅
5. **LearnLM/Eedi:** keep 76.4% (matches preprint); note Eedi press cites 82.3% — don't mix. (raw-edge.md) ✅

**Bottom line:** all feature-layer facts feeding the insights/SPOVs are VERIFIED (or fixed-then-verified). Corpus safe to synthesize.
