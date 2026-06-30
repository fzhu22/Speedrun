# Raw action-research — Methods lane (concrete how-to, precedents)

## A1 — fork + shared engine across desktop/Android/iOS
### Anki build + architecture (ankitects/anki)
Lane: methods; Link: https://github.com/ankitects/anki/blob/main/docs/development.md ; https://dev-docs.ankiweb.net/en/latest/architecture.html
- Build: clone to space-free path, Rustup (pinned `rust-toolchain.toml`) + uv + N2/Ninja, `./run` builds `rslib`+`rsbridge`; `tools/build` → wheels in `out/wheels`. Boundary: `rslib/` (Rust: DB/sync/scheduling/render) ← `pylib/anki` (Python wrapper) ← `pylib/rsbridge` (PyO3) ← `qt/aqt`+`ts/` GUI. Cross-language via Protobuf `proto/anki/`. ⇒ engine change in `rslib` (or a desktop-prepare Python layer over `pylib`); reviewer UI in templates/`ts`.
### AnkiDroid backend `rslib-bridge` (ankidroid/Anki-Android-Backend)
Lane: methods; Link: https://github.com/ankidroid/Anki-Android-Backend/blob/main/docs/ARCHITECTURE.md
- Android reuses desktop Rust via `rslib-bridge` (shared lib including `ankitects/anki` rslib as a submodule); JNI API = 3 functions (`openBackend`/`closeBackend`/`runMethodRaw`), everything else over protobuf. Published as a library (no Rust toolchain needed); clone side-by-side, `local_backend=true`. Single-writer model: all access via `with_col` (DB lock). AnkiDroid migrating off Java libAnki → rslib for parity. ⇒ bridge pattern = sanctioned one-engine-three-platforms route.
### iOS C-FFI precedents (JSchoreels/ios-anki; antigluten/amgi)
Lane: methods — [anecdotal→template]; Link: https://github.com/JSchoreels/ios-anki ; https://github.com/antigluten/amgi
- iOS method: compile Anki Rust crate as a static lib, expose ~4-function C FFI, wrap in Swift `AnkiBackend`, cross-compile device+sim into `AnkiRust.xcframework`; 24 .proto services; Rust owns DB/sync/FSRS/templates, "Swift owns the UI." Both credit AnkiDroid's bridge. ⚠️ These are THIRD-PARTY clients; **official AnkiMobile is closed-source, no add-ons** → a fork must ship its OWN iOS client (App Store + AGPL question → see constraints HARD BLOCKER).

## A1/A8 — custom-scheduling JS surface + PR #4880
### scheduler.proto + answering.ts + PR #4880 (merged 2026-06-08, commit 83d711f)
Lane: methods — [measured/primary]; Link: https://github.com/ankitects/anki/pull/4880 ; https://github.com/ankitects/anki/blob/main/proto/anki/scheduler.proto
- Custom-scheduling JS receives exactly `SchedulingContext{deck_name, seed}` (verbatim); runs at answer-time on the current card's `states`; can re-weight the current card's next interval; NO queue handle → cannot re-rank by concept (code basis for Validated SPOV 4 / anti-pattern #2). Persists via per-state `customData` (`packCustomData` writes per again/hard/good/easy). **PR #4880 exposes card decay + DR to JS (`ctx.decay`).** Per-card DR WRITE not native (jhhr draft only) → workaround = customData flags + a desktop add-on moving cards into per-DR decks (desktop-only; "20 extra decks"). Review order = ascending/descending retrievability keys off each card's DR → desktop-prepared per-card DR influences ordering via a supported native path.

## A1/A2/A3 — templates, reviewer JS, front-side cloze
### Reviewer JS + hooks (addon-docs)
Lane: methods; Link: https://addon-docs.ankiweb.net/reviewer-javascript.html ; https://addon-docs.ankiweb.net/hooks-and-filters.html
- Desktop JS inject: `gui_hooks.card_will_show(text,card,kind)->str` (must return HTML); time DOM via `onUpdateHook`/`onShownHook` (fade). JS→Python: template calls `pycmd("msg")` → `gui_hooks.webview_did_receive_js_message`; `evalWithCallback` reads JS return. ⇒ `card_will_show`/`pycmd`/Python = desktop-only; on AnkiDroid/AnkiMobile interactivity must live in the card template `<script>` (JS only) → two-tier.
### Front-side cloze as a template (Anki-Cloze-Interactive; Closet)
Lane: methods; Link: https://github.com/huandney/Anki-Cloze-Interactive ; https://forums.ankiweb.net/t/closet-for-anki-official-support/4560
- One-by-one front-side reveal = a front-template `<script>` + CSS in the Cloze note type (NO engine fork); compatible AnkiDroid+AnkiMobile+MathJax. Gotcha: native clozes are HTML-converted before the template sees them and lack front-side reveal info → use Closet `data-cloze` attrs or stash `innerHTML` (Anki-Cloze-Interactive uses `getAttribute("data-cloze")` + revealed[]). ⇒ A5 fade/completion ladder = incremental-reveal template; which rung = desktop-prepared.

## A1 — syncable per-card state + desktop-prepare automation
### customData limits (rslib/src/storage/card/data.rs)
Lane: methods — [measured/primary]; Link: https://github.com/ankitects/anki/blob/57e67f84/rslib/src/storage/card/data.rs
- `custom_data` (JSON, key "cd"): `validate_custom_data` enforces **keys ≤8 bytes, serialized ≤100 bytes** (verbatim). E.g. `{"tt":1}` transfer-trained, `{"dr":92}` DR target. Query without parsing via SQLite `extract_custom_data(card.data,'key')` (Browse search/columns; FSRS Helper uses this). >100 B (concept graphs, sort sets, rationales) → tags or a companion store.
### AnkiConnect (port 8765)
Lane: methods; Link: https://github.com/amikey/anki-connect
- Desktop-prepare automation: POST JSON to localhost:8765; actions `findNotes`/`notesInfo`/`addNote(s)`/`updateNoteFields`/`updateNoteTags`/`updateNoteModel`/`setSpecificValueOfCard`/`suspend`/`setDueDate`/`changeDeck`. Write-backs sync to mobile. Gotchas: note open in Browser silently won't update; macOS keep foreground / disable App Nap. AnkiAIUtils uses this + cron.

## A2/A6/A10 — precedent add-ons
### AnkiAIUtils (failure-triggered field augmentation)
Lane: methods — [anecdotal]; Link: https://github.com/thiswillbeyourgithub/AnkiAIUtils
- Target failed cards (`rated:1`/a failed tag) → write NEW fields (Explainer/Mnemonics/Illustrator/Reformulator) via AnkiConnect + LiteLLM (provider-agnostic). Edits note FIELDS → renders on all clients with no mobile code (the desktop-prepare→cross-platform-review move). "Respects your own mnemonics," runs cron/batch offline (not answer path) → AI augments AROUND the student (compliant, doesn't auto-author/grade).
### MyAnswerChecker / AI-Hints / AI Explainer / AI Grader
Lane: methods — [anecdotal]; Link: https://github.com/Junibabng/MyAnswerChecker ; https://github.com/athulkrishna2015/AI-Hints ; https://github.com/yuwayanagitani/anki-ai-explainer
- MyAnswerChecker: type free-response → LLM evaluates semantically → SUGGESTS Again/Hard/Good/Easy (accuracy+time); user accepts/overrides → **compliant A6/A10 grading pattern (AI suggests, human/key decides)**. AI-Hints: generates MCQ distractors for open cards; has a unified UI script working on AnkiDroid/AnkiMobile/AnkiWeb WITHOUT the add-on (proof review tier = pure template JS) → A6 distractors (must be source-backed/human-reviewed per anti-pattern). Anki AI Explainer: reads input fields → writes HTML explanation field (skip/overwrite/append), single or batch over a search → A6 remediation in prepare tier. AI Grader: batch grade in Browser → A9 offline pass. ⚠️ all put AI in/near the answer path; NONE implement the crutch kill-switch (A10's missing guardrail).
### AnkiHub UWorld-QID tagging + Smart Search; AnKing MCAT deck
Lane: methods — [template]; Link: https://community.ankihub.net/t/how-do-i-use-uworld-qid/450988 ; https://community.ankihub.net/t/anking-mcat-deck-wiki/132979
- QID→card already exists: cards tagged with UWorld QID; "UWorld QID to Anki Search" add-on turns a pasted QID string into `uworld:NNNNN` → surface/unsuspend → A2 reuse "missed QID → tag lookup → spawn scaffolded miss-card." AnkiHub = companion sync layer beyond AnkiWeb (owner uploads/others download/moderators accept) → model for syncing >100 B artifacts (concept graphs/sort sets). Smart Search = upload notes/PPT → LLM finds matching notes → unsuspend (retrieval, not authoring; clean). AnKing MCAT (~6,293 cards) hand-merged by volunteers (MileDown+Abdullah+Coffin+Pankow) from a 90-page sheet + 300-page KA doc → A4 curated-content labor model (don't auto-tag). Tag hierarchy `#AK_MCAT_v2::…` → A4 concept graph = a tag namespace (`#confusable::inhibition::competitive`), syncs natively, dodges the 100-B ceiling; "suspend all, unsuspend by tag" = opt-in-after-baseline gating (A4).
### Image Occlusion (native 23.10) / Cloze Overlapper
Lane: methods; Link: https://github.com/glutanimate/cloze-overlapper/wiki/FAQ
- Custom card type generating many siblings from one note (A3 sort families / A5 ladders) = a dedicated note type + generator. Image Occlusion native since 23.10 → don't rebuild (anti-pattern #11); fork novelty = guided drawing/transfer prompts. Cloze Overlapper = overlapping clozes where each answer cues the next card (A5 mechanism chains).

## A9/A3/A4/A5 — learning-science how-to
### Item discrimination = point-biserial (ACER; Assessment Systems)
Lane: methods — [measured]; Link: https://www.acer.org/files/Conquest-Notes-5-ItemPointBiserialDiscrimination.pdf ; https://assess.com/the-point-biserial-item-discrimination/
- r_pb = ((M1−M0)/Sₙ)·√(n1·n0/n²); Excel CORREL / R cor.test / biserial.cor. Use CORRECTED point-biserial (exclude item from total). Per-distractor point-biserial (A6): good item = +r_pb key, strongly −r_pb distractors. Simpler: upper-minus-lower index. → A9 metric (whether "transfer-trained" discriminates better than a recall cloze).
### PFL double-transfer design (Bransford & Schwartz 1999; Mylopoulos 2014)
Lane: methods — [measured]; Link: https://aaalab.stanford.edu/papers/Rethinking_transfer_a_simple_proposal_with_multiple_implications.pdf ; https://pubmed.ncbi.nlm.nih.gov/24909528/
- PFL = double-transfer: instruct concept A → give a NEW learning opportunity on novel concept B → final task scores whether they learned B better because of A (PFL vs SPS). Embedded method: worked example mid-test + later transfer problem solvable via it. Medical RCT (n=51): initial equal (p=0.37) but basic-science group higher on PFLA (0.72 vs 0.63, p=0.05, d=0.62) → PFL discriminates instruction a snapshot misses. → A9 "trials-to-next-concept" = loggable proxy.
### Chi/Feltovich/Glaser 1981 card-sort (A3 gate, A4 items)
Lane: methods — [measured]; Link: http://matt.colorado.edu/teaching/highcog/readings/cfg81.pdf
- Method: ~24 problems (3/chapter) on cards; "sort by similarities in how they'd be solved"; NO pencil/paper; re-sort (consistency); explain groupings; time each. Experts group by deep structure, novices by surface = A3 pass/fail. Item construction: CROSS surface features with deep principles (same principle/different cover; same surface/different principle) → a correct sort can't be a surface match (kills the perturbed-accuracy shortcut).
### Backward fading + principle prompts (Renkl & Atkinson 2003)
Lane: methods — [measured]; Link: http://www.davidlewisphd.com/courses/EDD8121/readings/2002-Renkl_et_al.pdf
- Fade ladder: full worked example → completion w/ last step omitted → last two omitted → full problem (BACKWARD fading, more efficient than forward / example-problem pairs). Add a principle-naming prompt at each faded step → medium-large near AND far transfer at no extra time. Gate next stage on a phase-exit rapid test → operationalizes A5 "fade after ≥2 unaided successes + 1 transfer item." Same deep structure / different surface (reuse Chi crossing).

## A8 — exam-date DR ramp + the rejected workaround
### FSRS exam-deadline method (Anki Forums / FSRS Helper)
Lane: methods — [measured-by-consensus]; Link: https://forums.ankiweb.net/t/exam-specific-add-on-or-help-max-review-date/67433 ; https://forums.ankiweb.net/t/fsrs-mcat-advice/70140
- REJECTED (anti-pattern #10): lowering max interval "doesn't work" unless lowered daily → corrupts SR. CORRECT lever: raise Desired Retention (0.90→0.92→0.95) compresses intervals + raises workload; "Reschedule cards on change" to pull reviews in now; per-card/targeted = bucket high-yield/weak + raise their DR (matches A8 desktop-prepared per-card DR + PR #4880). Workload cap: MCAT consensus 88-92% DR (raising DR exponentially increases time) → ramp must cap + prioritize, not blanket-raise; targeted pre-exam = Filtered decks (due-before-exam / by tag). FSRS Helper "Advance" (moves future cards forward, least-impact-on-retention) + Postpone/Load-Balance/Easy-Days/Reschedule-all → A8 = a date-aware per-card-DR generalization of Advance; build ON it.

## A10 — severe-test generation + crutch A/B harness
### Counterexample/boundary-case prompt methods
Lane: methods — [template+measured]; Link: https://github.com/rpatrik96/research-agora/.../counterexample-searcher.md ; https://proceedings.mlr.press/v267/li25ax.html (COUNTERMATH)
- Severe-test prompt (generate, NEVER grade): (1) enumerate the claim's assumptions/conditions; (2) "what breaks if this is dropped/weakened?"; (3) construct concrete boundary/edge cases (n=1, empty set, extremes, limits). = A2 disconfirmer automated as a PROMPT, not a card body. Verdict format (against a human key): "output `OK` if it holds, else `[[VERDICT]] FAILED` + `[[TEST]]` <counterexample>" → adapt: given student's principle + human key, output "consistent" or a counterexample item the student answers UNASSISTED; AI never assigns the final grade (anti-pattern #6). COUNTERMATH: even strong models have weak counterexample skill → check against the human key.
### Bastani et al. 2025 (PNAS) crutch A/B harness
Lane: methods — [measured/RCT n≈1000]; Link: https://www.pnas.org/doi/10.1073/pnas.2422633122
- 3-arm RCT (Control / GPT Base / guardrailed GPT Tutor); each session = intro → ASSISTED practice (AI available) → UNASSISTED closed-laptop exam where each item is "conceptually very similar" to a practiced item; pre-registered primary = the unassisted exam, independent graders balanced across arms. Result: GPT Base +48% assisted but −17% unassisted; GPT Tutor mitigated. → A10 ships a feature ONLY if assisted-up doesn't bring unassisted-down (metric = assisted−unassisted gap on matched items). Working guardrail (GPT Tutor) = system prompt INCLUDED the correct solution + common mistakes (so AI can't give wrong feedback) + "hints not answers" (students never see it) = A10 design spec.

## A11 — CARS delivery (Jack Westin)
Lane: methods — [anecdotal; API claim UNVERIFIED]; Link: https://jackwestin.com/daily/mcat-practice-passages ; https://testpreppal.com/mcat/question-bank/jack-westin
- New original CARS passage daily via email subscription + on-site feed; QBank ~3,044 AAMC-style CARS passages / 6,700+ questions; timed mode; per-passage discussion; Chrome extension tracks progress on official AAMC; JW+ $29.99/mo; stack Vue.js; internal RAG/LLM assistant (LangGraph/FastAPI). ⚠️ UNVERIFIED: a secondary aggregator says "no public developer API" — NOT confirmed from JW docs → A11 "integrate" likely needs partnership/BD + licensing, not self-serve. A11 "build": passage content (licensed/original) + timer + per-passage question UI + error-pattern analytics (inference/tone/scope/timing) — not a flashcard deck (anti-pattern #9); content licensing is the binding cost.

## 16 load-bearing how-to facts (summary)
1. One engine, 3 tiers: rslib+rsbridge(PyO3) → Android rslib-bridge (JNI, 3 fns, submodule) → iOS C-FFI xcframework (4 fns), shared crate over protobuf; iOS precedents exist.
2. Custom-scheduling JS re-weights, can't re-rank (`{deck_name,seed}`, answer-time, no queue handle) — SPOV 4 confirmed in proto.
3. PR #4880 (2026-06-08) exposes decay+DR to JS; per-card DR write NOT native → A8 uses deck-buckets/customData/ascending-retrievability.
4. customData keys ≤8 B / ≤100 B total → tiny flags; bigger artifacts in tags / companion store; query via extract_custom_data().
5. Reviewer JS: desktop card_will_show+pycmd; mobile = template `<script>` only → two-tier.
6. Front-side incremental cloze = template script (Anki-Cloze-Interactive/Closet), works mobile, no fork → A5 cards template-level.
7. Desktop-prepare automation = AnkiConnect (updateNoteFields/Tags/setDueDate, :8765), cron/offline, syncs to mobile.
8. Failure-triggered remediation precedent = AnkiAIUtils (write new fields via AnkiConnect+LiteLLM; renders everywhere; respects student work).
9. Compliant AI grading = MyAnswerChecker (AI suggests rating; human/key decides).
10. QID→card solved (AnkiHub UWorld-QID add-on); curated MCAT content + tag-graph hand-built by volunteers (A4 model).
11. Item discrimination = corrected point-biserial (+ per-distractor for A6) — replaces accuracy/streaks (A9).
12. PFL = double-transfer (instruct A → learn novel B → score B-learning); medical RCT d=0.62; trials-to-next-concept = loggable proxy.
13. Deep-structure sort gate = Chi card-sort with surface×deep crossed items (un-gameable).
14. Support fading = backward fading + principle prompts → near+far transfer, no extra time; advance on a phase-exit test.
15. Exam-date ramp = raise DR + reschedule-on-change / FSRS-Helper Advance + filtered decks; max-interval hacks don't work.
16. AI severe-test = assumption-drop/boundary-case prompt with `[[VERDICT]]/[[TEST]]`-against-key (never final-grade); gate via the Bastani 3-arm assisted→unassisted-closed-book harness.

## Flags for constraints (surfaced): AGPL on a fork + own iOS client (AnkiMobile closed, no add-ons); per-card DR write unmerged (A8 dependency); LLM API keys/cost/prompt-injection; content licensing (UWorld/AnKing/Jack Westin owned; "no JW API" UNVERIFIED); custom-note-type schema migration + sync-conflict plan.
