# Raw research — Bleeding-edge lane (newest 2025-2026 study-feature research + releases; tagged + dated)

### Practice Less, Explain More: LLM-Supported Self-Explanation (Chen et al., 2026)
Stance: edge — [preprint-unreviewed]; Link: https://arxiv.org/html/2604.00142v1
DOK 1 - Facts:
- Between-subjects N=92: no self-explanation vs menu-based vs open-ended with LLM-generated feedback. Open-ended LLM-feedback scored +11.9 pp on "Not Enough Information" transfer explanation quality vs control (p=.030); NEI MC accuracy advantage NOT significant (p=.183); open-ended learners completed ~¼ as many practice problems in the same time; LLM grader Cohen's κ .66-.68 vs individual humans, .78 vs human consensus. [preprint-unreviewed]

### SmartFlash (Li et al., 2026)
Stance: edge — [preprint-unreviewed]; Link: https://doi.org/10.48550/arxiv.2602.14431
DOK 1 - Facts:
- AI flashcard prototype (ISLS 2026); 6 higher-ed students think-aloud. Students valued automation for reducing prep burden but REQUIRED transparent, editable AI outputs to maintain "cognitive ownership"; conceptualized AI as a collaborative partner needing verifiable reasoning. Design principles: editability, transparency, metacognitive scaffolding without prescription, motivational flexibility. [preprint-unreviewed]

### AI Tutoring Can Safely and Effectively Support Students (LearnLM/Eedi, 2025)
Stance: edge — [preprint-unreviewed]; Link: https://arxiv.org/pdf/2512.23633
DOK 1 - Facts:
- Exploratory RCT, 165 students, 5 UK secondary schools; LearnLM drafted chat tutoring on Eedi with EXPERT TUTORS supervising/revising before sending; tutors approved 76.4% of drafts with zero/minimal edits; students guided by LearnLM were +5.5 pp more likely to solve novel problems on subsequent topics than human-tutored-alone; tutors praised Socratic question drafting. [preprint-unreviewed]

### Faster Completion, Less Learning (arXiv, 2026)
Stance: edge — [preprint-unreviewed]; Link: https://arxiv.org/html/2605.21629v1
DOK 1 - Facts:
- Generative AI reduced study time AND knowledge built; cites a 2025 HS math RCT where GPT-4 access improved AI-assisted practice +48% but reduced UNASSISTED exam performance −17% vs control (assist-vs-test reversal from reduced active engagement). [preprint-unreviewed]

### Bandit-Based Educational Recommender (De Kerpel, Thuy, Benoit, 2026)
Stance: edge — [emerging]; Link: https://arxiv.org/pdf/2602.04347
DOK 1 - Facts:
- Linear Thompson Sampling for exercise recommendation; reward = learner SKILL GAIN (BKT knowledge-state change), not next-question correctness; LinTS +15.2% avg skill gain over non-contextual TS, +16.5%/+20.7% over collaborative-filtering baselines (ASSISTments). [emerging]

### Adaptive Difficulty via Contextual Bandits / InfoTutor (OpenReview, 2026)
Stance: edge — [preprint-unreviewed]; Link: https://openreview.net/pdf?id=vFShUczPNE
DOK 1 - Facts:
- Difficulty selection as a contextual multi-armed bandit; InfoTutor = BKT + UCB exploration; 12-18% post-test gains over baselines (ASSISTments, Junyi). [preprint-unreviewed]

### SRS Benchmark / FSRS-7 (open-spaced-repetition, 2026)
Stance: edge — [public-repo/emerging]; Link: https://github.com/open-spaced-repetition/srs-benchmark
DOK 1 - Facts:
- Benchmark ~727M reviews / 10,000 Anki users; FSRS-5 uses same-day data; FSRS-6 improves same-day handling + adds optimizable forgetting-curve flatness; FSRS-7 designed for fractional interval lengths + realistic same-day recall-probability; FSRS-7 "sched. penalties" address very short same-day intervals at high DR + massive interval jumps at low DR. [public-repo]

### FSRS-7 Support PRs #395 / #426 (JSchoreels / open-spaced-repetition, Apr-Jun 2026)
Stance: edge — [public-repo/emerging]; Link: https://github.com/open-spaced-repetition/fsrs-rs/pull/395 ; https://github.com/open-spaced-repetition/fsrs-rs/pull/426
DOK 1 - Facts:
- PR #395 (created 2026-04-07): FSRS-7 in fsrs-rs, expands 21→35 parameters, adds a penalty mode to avoid "1s hell review"; review flagged regressions (default FSRS-7 behavior, `enable_short_term=false`) → defaults reverted to FSRS-6, FSRS-6/7 paths split. PR #426 (2026-06-14): NEON for macOS + 15-20% faster ADR; Expertium (2026-06-14) said final Rust FSRS-7 "ready today or tomorrow." [public-repo/public-post]

### Anki/AnkiDroid FSRS releases + manual (2024-2026)
Stance: edge — [release-note/documentation]; Link: https://docs.ankidroid.org/changelog.html ; https://docs.ankiweb.net/deck-options.html?highlight=FSRS
DOK 1 - Facts:
- AnkiDroid 2.20 (2024-12-04): Anki 24.11 + FSRS 5.0, same-day scheduling (remove learning steps), load balancing, Easy Days, forgetting-curve card info, sort by descending retrievability. 2.21.1 (2025-07-16): Anki 25.07.4 + FSRS 6.0. Manual: DR is "the most important FSRS setting," workload rises quickly >90%, overwhelming >97%; Easy Days works with FSRS + SM-2. [release-note]

### AnkiHub AI features (MCAT deck update + June 2026)
Stance: edge — [release-note/public-post]; Link: https://community.ankihub.net/t/anking-mcat-deck-update-20-may-11th-june-10th/600786 ; https://community.ankihub.net/t/june-updates/506789
DOK 1 - Facts:
- AnKing MCAT update (May 11-Jun 10 2026): SmartSearch finds MCAT material from PPT/PDF/text; new chatbot prompts "Generate a Practice Question" + "Explain Like I'm Five"; AI bot can generate questions BEFORE UWorld/AAMC. June: FSRS auto-enabled for new AnKing users on import + monthly optimize-FSRS prompt (>30 days) with undo; SmartSearch launches from browser/deck overview. [release-note]

### MCAT AI products (UWorld UAsk; RemNote)
Stance: edge — [release-note/vendor-claim]; Link: https://newsroom.uworld.com/story/ai-powered-learning-tool-mcat-usmle-test-prep/ ; https://www.remnote.com/mcat_landing_page
DOK 1 - Facts:
- UWorld UAsk (2026-05-05) for MCAT/USMLE: real-time exam-aligned support in QBank/exams/UBooks, trained+monitored by in-house SMEs, turn responses into flashcards/notes, covers all MCAT sections incl. CARS. [vendor-claim]
- RemNote MCAT: 10,000+ SR flashcards, interactive AI tutor for 1,000+ lessons, "Super-Lessons" (KA videos + AI tutoring), 5,000+ QBank questions. [vendor-claim]

### AI Anki add-ons (explainer / answer-checker / utils / MCP tutor)
Stance: edge — [public-repo/release-note]; Link: https://github.com/yuwayanagitani/anki-ai-explainer ; https://github.com/Junibabng/MyAnswerChecker ; https://github.com/thiswillbeyourgithub/AnkiAIUtils ; https://github.com/mkrech/anki-course-tutor-mcp-server
DOK 1 - Facts:
- Anki AI Explainer (created 2025-12-14; v1.0.0 2026-02-18): generates HTML explanations for the current/batched cards (OpenAI/Gemini), configurable destination field (skip/overwrite/append).
- MyAnswerChecker: type an answer in a chat bubble; AI evaluates semantic accuracy + response time and SUGGESTS Again/Hard/Good/Easy (learner can accept or override); follow-up chat. (← directly relevant to free-response self-grading.)
- AnkiAIUtils (855 stars, push 2026-04-01): AI explanations/mnemonics/illustrations/summaries/adaptive learning; tested for med school; one workflow adds ChatGPT explanation + DALL-E illustration + mnemonic AFTER a learner fails a card. (← failure-triggered elaboration.)
- Anki Course Tutor MCP Server: Anki SR + AI tutoring via chat; explain mode + test mode; get-next-card/submit-answer/confirm-or-override/get-explanation; reviews to native scheduler via AnkiConnect.

## Freshest facts (one-line + date + tag)
- 2026-06-14: FSRS7 PR — macOS NEON + 15-20% faster ADR [public-repo]; Expertium says FSRS-7 Rust near-final [public-post].
- 2026-06-10: AnKing MCAT — SmartSearch over PDF/PPT/text + chatbot practice-question generation [release-note].
- 2026-06: AnkiHub — FSRS auto-enable + monthly optimize prompt for new AnKing users [release-note].
- 2026-05-05: UWorld UAsk launched for MCAT/USMLE; in-context explanations + flashcard conversion [release-note].
- 2026-04-07→06-01: FSRS-7 PR expands 21→35 params; exposes same-day/fractional-interval issues [public-repo].
- 2026-04: LLM self-explanation RCT — better transfer explanation quality, NOT significant MC transfer accuracy [preprint].
- 2026-02: SmartFlash — AI flashcards need editable/transparent/verifiable outputs for cognitive ownership [preprint].
- 2026-02: Contextual Thompson Sampling optimizes sequencing on SKILL GAIN not correctness [emerging]; InfoTutor = BKT+UCB difficulty bandit [preprint].
- 2026-02-18: Anki AI Explainer v1.0.0 (OpenAI/Gemini card explanations) [release-note].
- 2025-12: LearnLM/Eedi supervised-AI-tutor RCT ≥ human-tutor chat on measured outcomes (76.4% drafts approved) [preprint].
- 2025-07-16: AnkiDroid 2.21.1 = FSRS 6.0 [release-note].

## Emerging experts / voices (edge)
Jarrett Ye / L-M-Sherlock (FSRS) https://github.com/L-M-Sherlock ; Expertium (FSRS benchmark/formula) https://github.com/Expertium ; Jonathan Schoreels / JSchoreels (FSRS-7 PRs) https://github.com/JSchoreels ; Hongming "Chip" Li (SmartFlash) ; Lukas De Kerpel (contextual TS recommender) ; LearnLM Team / Eedi (supervised AI tutor RCT) ; AnkiHub/AnKing MCAT team ; UWorld product team.

## Flags (edge)
- Most AI flashcard + MCAT product claims are VENDOR claims, not efficacy evidence.
- Strongest efficacy-adjacent AI evidence is OUTSIDE MCAT (calculus self-explanation, secondary math tutoring, math AI-assist risk).
- FSRS-7 highly relevant but NOT stable/shipped in Anki — active regressions/rapid iteration; solid current = FSRS-6 (Anki 25.07/AnkiDroid 2.22).
- Adaptive interleaving/sequencing evidence is emerging in general ed-recommendation + ear training, NOT yet card-level MCAT transfer scheduling.
- AI-card-generation crowded; quality-control evidence is mostly prototype/design logic/repo claims/product copy, not RCTs.
- MCAT-specific AI tools converge on in-context explanations + flashcard conversion; no public MCAT OUTCOME studies for those features.

## CHILD BRAINLIFT CANDIDATE (edge)
- Topic: Adaptive sequencing beyond FSRS for MCAT transfer — should a fork optimize only review TIMING (FSRS) or also choose WHICH concept/card/task next for discrimination + passage transfer (contextual bandit on skill gain)? Big/contested (FSRS optimizes timing; bandits optimize selection; combining unsettled)/load-bearing (materially changes feature priorities).
- Orchestrator note: modeling/feature sub-question → resolve inline.
