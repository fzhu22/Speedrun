# Execution Plan (REVISED) — Forking Anki for the MCAT (A1–A12)

**Roles:** R = Rust/build eng · P = Python/data eng · J = card-template/JS eng · C = MCAT content author/reviewer · L = PM/legal/BD. **Costs as-of 2026-06-29.** Each step carries the 5 required fields + a `Binding/faithful:` line. Forks keep their 2–3 candidate approaches.

## CHANGES APPLIED (what moved, vs. the draft)
1. **Mobile write-back rule (central risk resolved).** Re-scoped every review-tier WRITE step — **A3-S4, A4-S3, A6-S3, A7-S1, A9-S1** — so **desktop-prepare reconcile is the AUTHORITATIVE write path**; mobile customData-at-answer is a **desktop/Android-only, version-contingent optimization** (test AnkiDroid #14865 on target versions, never assume); **iOS = capture-local / practice-only**. A9-S1 rebuilt to assemble metrics from the **native synced revlog** + desktop-prepared customData/tags via a **desktop analytics pass** (no mobile POST).
2. **New blocking first step A1-S0 — "client write-back/parity spike."** Empirically confirms per-client/per-version what card-JS can persist BEFORE the five WRITE steps are built; until it passes they default to desktop-reconcile.
3. **Fork-build separated from the review tier.** Review tier (A2/A3/A4/A9 + A8 READ) runs on **STOCK AnkiDroid/AnkiMobile, no fork build, no add-on** (AI-Hints precedent). **"AnkiDroid from source" CUT from MVP.** Fork build (A1-S1) = branding + the one native Rust change, **parallel and off the critical path**.
4. **A1-S1 hardened.** Space-free path; build on **WSL/Linux/Mac, not Windows/PowerShell**; **"CI-reproducible" dropped** from MVP accept; the **mandatory MVP real Rust change** (`extract_custom_data` SQLite search/column) is **committed here**. A8-S2b is the higher-value OPTIONAL change.
5. **A1-S2 relabeled** a **local single-collection script** (AnkiConnect = HTTP server inside a live Qt GUI; headless = xvfb), with new acceptance criteria: **idempotent, resumable, paginated, backup-before-prepare, clients-quiesced (single-writer `with_col`)**, plus a **scratch test profile** + **schema-stability guard**.
6. **A1-S5 corrected.** APKG round-trip = **"portable demo export/import," NOT conflict-safe convergence** (scheduling/customData not preserved; GUID-collision dup). Self-host sync (pilot) = **AGPL §13 + GDPR data-controller** duties; AnkiWeb needs **written permission**.
7. **A2-S1** now states the **disconfirmer-USE decision + DoD** (MVP = passive back-display; ROADMAP = active-retrieval front-prompt).
8. **A2-S3** given a **concrete perturbation mechanic** (original→swapped cover-story fields + a surface-dimension checklist); AI = thinking-aid only.
9. **A3-S1** given an **independent-reviewer rubric/QA + a 2–3-human pilot-sort** (surface-only sorter must fail); MVP "set" = a **small ~6-item 2×3 set labeled "demo, not transfer-validated."**
10. **A4-S1** — **hiring tutors → POST-MVP**; MVP content = **in-house expert only**; **"set" defined** (~8–12 drills).
11. **A6-S1** — explicit wall: **no AI-suggested distractor ships without human review + a cited source.**
12. **A8-S2** — the **schema-vs-stock-client fork made explicit + product-defining**; **A8-S2b reclassified as a ≈1–2-week native-write spike** (6 sub-tasks + DoD incl. FSRS-integrity regression); **A8-S2a (customData/deck-bucket, read-native) = THE plan.**
13. **Cost reality replaced** the "$0" claim: **MVP ~$0 only if APKG-only / no-LLM / no-sync / in-house**; **credible-pilot all-in $5k–25k** + a **legal-review quote gate** + store fees + hidden fork-maintenance labor.
14. **3-day MVP rewritten** to the operator's **stock-client** Wed/Fri/Sun version, with honest demo caveats.
- **GAP-2 / GAP-3 are now RESOLVED** (moved out of GAPS into the A1-S0 spike + the write-path design rule). **GAP-1, GAP-4, GAP-5 remain open.**

## Sequencing & critical path (read first)
- **The review tier runs on STOCK clients** (no fork build): custom-scheduling JS sees only `{deck_name, seed, +decay/DR READ}`, runs at answer-time, re-weights one card, **cannot re-rank the queue** → all concept-aware sequencing is **desktop-prepared**. AnkiMobile = no add-ons; AnkiDroid = no Python.
- **The fork (A1-S1) is PARALLEL and off the critical path** — it exists for branding + the one mandatory native Rust change, not for the review tier.
- **Authoritative write path = desktop-prepare reconcile (A1-S2).** The value captured in the card webview (sort result, confidence) is **not** an input to the scheduling transform → it must be reconciled desktop-side. Mobile-at-answer customData is an **Android-only, version-contingent** optimization; **iOS writes nothing synced**.
- **Critical path (MVP):** A1-S0 → A1-S2 → A1-S3 → A1-S4 → {A2, A3} → A9-S1/S2. Long pole = content authoring (A3-S1 / A4-S1), runs parallel from day 1. **A1-S1 (fork build) runs alongside, not on the path.**

---

## A1 — Two-tier foundation (Validated SPOV 4) — FOUNDATION

**A1-S0 — Client write-back / parity spike. [MVP — FIRST, BLOCKING]** How: on the team's TARGET AnkiDroid + AnkiMobile + desktop versions, empirically test what review-tier card-JS can PERSIST into the **synced** collection. Channels to test: (1) **AnkiDroid `AnkiDroidJS` get/set tags** (#17795; requires `new AnkiDroidJS({version,developer})` + user-enabled JS API; some calls open a dialog) — the only community-blessed synced write from the review flow; (2) `states.current.customData` **set-before-answer** (AnkiDroid #14865 historically broken — re-test, never assume); (3) **AnkiMobile = confirm NO synced write** (only `sessionStorage` front→back / `localStorage` device-local, resets on update). Resources: $0; 1×J; 0.5–1 day. Deps: none (runs on STOCK clients). Accept: a written matrix `{client × version × channel → persists? syncs?}` + a per-feature go/no-go; **until a channel passes, A3-S4/A4-S3/A6-S3/A7-S1/A9-S1 default to desktop-reconcile.** Binding/faithful: matrix must be empirical on target versions (GAP-2/3 resolved in principle: iOS=none, Android=tags/version-contingent); no on-device queue re-rank (anti-pattern #2).

**A1-S1 — Fork & build Anki from source; rename; land the MANDATORY real `rslib` change. [MVP — PARALLEL, OFF CRITICAL PATH]** How: clone `ankitects/anki` to a **space-free path** (the workspace path "AI Brainlifts" has a space → build dies); build on **WSL/Linux/Mac, NOT Windows/PowerShell**; Rustup (pinned) + uv + N2/Ninja + `just`; `./run` builds rslib+rsbridge (PyO3); `tools/build`→wheels. **Mandatory MVP Rust change (committed here):** SQLite search/column over `extract_custom_data(card.data,'key')` in rslib (low-risk, testable; lets the prepare/analytics tier query `{"tt":1}`/`{"dr":92}`). Own name+logo (Anki name trademarked; logo AGPL). **AnkiDroid-from-source is CUT from MVP.** Resources: $0 (AGPL); 1×R; 0.5–1 day. Deps: none; runs parallel to the review-tier path. Accept (bar lowered): **renamed fork launches + opens a collection** (`just run`/`./run` green on a Linux box) and the `extract_custom_data` search has a unit test. **"CI-reproducible" dropped from MVP.** Binding/faithful: space-free Linux path + pinned toolchain; gives the project its mandatory real Rust change; serves SPOV 4; no anti-pattern.

**A1-S2 — Desktop "prepare" tier = a LOCAL single-collection script. [MVP — CRITICAL PATH, AUTHORITATIVE WRITE]** How: Python over `pylib/anki` and/or AnkiConnect (`POST localhost:8765`: findNotes/notesInfo/addNote/updateNoteFields/updateNoteTags/setSpecificValueOfCard/changeDeck/setDueDate). **AnkiConnect is an HTTP server INSIDE a running Qt GUI** (not offline/cron) → run against a live desktop profile; headless = **xvfb**. This is the **AUTHORITATIVE write path for ALL review-tier-captured state.** Gotchas: a note open in Browser silently won't update; on macOS keep foreground + disable App Nap. Resources: $0 (AnkiConnect GPLv3, `git.sr.ht/~foosoft/anki-connect`); 1×P; 1–1.5 days. Deps: A1-S0. (Does NOT depend on the fork — runs on stock desktop.) Accept: writes field/tag/customData appearing on a 2nd device AND is **idempotent, resumable, paginated** (50k-card collections OOM otherwise), **takes a backup before prepare**, and **writes only when clients are quiesced** (single-writer `with_col`; third-party writes during unsynced changes → forced full-sync / lose-changes); ships a **scratch test profile** for note-type/template iteration (field/template edits = schema-modifying = forced full sync) + a **schema-stability guard** (abort on schema drift). Binding/faithful: write-backs survive sync; runs OFF the answer path (anti-pattern #2 avoided); single-writer discipline prevents data loss.

**A1-S3 — Cross-platform "review" tier runtime (card-template JS) on STOCK clients. [MVP — CRITICAL PATH]** How: template `<script>` JS only (proven cross-client by AI-Hints' unified UI script on **stock** AnkiDroid/AnkiMobile/AnkiWeb with **no add-on, no fork build**); reserve `card_will_show`+`pycmd`+Python for desktop-only. Persistence of anything captured here follows the A1-S0 matrix (default: desktop reconcile). Resources: $0; 1×J; 1–2 days. Deps: A1-S0. Accept: one note type renders an interactive card identically on **stock** desktop/AnkiDroid/AnkiMobile. Binding/faithful: mobile = JS-only + capture-local → anything needing a synced write routes to A1-S2; no anti-pattern.

**A1-S4 — Syncable-artifact channel (3 approaches). [MVP: a+b]** (a) tiny `customData` flags (key "cd", ≤8-byte keys/≤100-byte total; `{"tt":1}`,`{"dr":92}`; queried via the A1-S1 search) — **written by desktop reconcile** (answer-time write is the Android-only, version-contingent optimization); (b) **tag namespaces** (`#confusable::inhibition::competitive`; AnKing `#AK_MCAT_v2::…`; syncs natively, dodges the 100B cap; the **AnkiDroidJS get/set-tags channel is the only review-flow synced write A1-S0 may confirm on Android**; suspend-all/unsuspend-by-tag = opt-in gating); (c) companion store (AnkiHub-style) for big artifacts. Recommended (a)+(b) MVP, (c) later (tag-list bloat is (b)'s cost; silent truncation is (a)'s). Resources: (a)/(b) $0; (c) $6–15/mo; 1×R/P; 1 day. Deps: A1-S0, A1-S2; (a)'s native read uses the A1-S1 search. Accept: a >100-byte artifact (small sort set) round-trips desktop→stock mobile via **tags**; customData flags round-trip via **desktop reconcile**. Binding/faithful: never exceed `validate_custom_data` (silent truncation); tags = the durable cross-client channel; no anti-pattern.

**A1-S5 — Sync/transport path (FORK — 3) + schema migration. [MVP: c = demo transport ONLY]** (a) self-host `anki-sync-server` (HTTP-only→add TLS; "individual/family" scope; multi-tenant auth/scaling = your burden) — **pilot only**; triggers **AGPL §13 network-use source-offer** AND makes you the **GDPR data controller**; (b) request **written** Ankitects permission for AnkiWeb (do NOT budget AnkiWeb as a programmable backend); (c) **APKG import/export = "portable demo export/import" ONLY** — round-trip does **NOT** cleanly preserve scheduling/customData and can **duplicate on GUID collision** → demo transport, **NOT a conflict-safe convergence story.** Recommended (c) for MVP/demo, (a) for pilot. Version the schema; sync-conflict under the single-writer `with_col` lock. Resources: (a) DO $6–12/mo + ops + [legal: §13 + GDPR controller]; (b) $0 + [legal: written permission]; (c) $0. Deps: A1-S2, A1-S4. Accept: (c) two devices transport custom fields/tags via APKG **for a demo** (dup/scheduling-loss acknowledged); true convergence requires (a). Binding/faithful: AnkiWeb ToS forbids third-party clients w/o permission → (a)/(b) only; do not claim APKG = convergence.

**A1-S6 — iOS review-tier path (FORK — LEGAL — 3). [DEFER]** (a) review tier = card-template JS inside the EXISTING AnkiMobile (legal workaround: AGPL §7 vs Apple Usage Rules; VLC/GNU-Go pulled) — but **iOS has NO synced write path (A1-S0/GAP-3): capture-local / practice-only for any gated feature**; (b) 100%-own thin client to a server (no AGPL engine on-device); (c) defer iOS, Android-first (Play permits AGPL; AnkiDroid Kotlin+JNI rslib-bridge). Recommended (a)+(c). NEVER ship an own engine-bearing iOS app. Resources: Apple $99/yr only if (b). Deps: A1-S0, A1-S3, A1-S5. Accept: a fork card renders+interactive on stock AnkiMobile via template JS; gated-feature state on iOS stays local (no synced unlock until a desktop reconcile runs). Binding/faithful: §7 exception needs every holder → impossible → path (a); iOS never writes synced state.

**A1-S7 — AGPL packaging, §13 boundary, naming. [partial MVP: licensing]** How: publish modified source (AGPL-3.0-or-later); any modified-engine server (sync/prepare/LLM gateway) offers source per §13 OR sits behind a non-AGPL API boundary; own name/mark. Resources: 1×L ~0.5 day + [legal]. Deps: A1-S1. Accept: repo builds from published source; §13 compliant; own name/logo. Binding/faithful: §13 network-use is triggered by A1-S5(a) self-hosted sync.

---

## A2 — Student-authored miss→card scaffold + DISCONFIRMER (SPOV 1) — flagship [MVP]

**A2-S1 — "Miss→Card" note type w/ required DISCONFIRMER field + the disconfirmer-USE decision. [MVP]** How: fields = Provenance/QID, Student's principle, **Original cover-story → Swapped cover-story**, Trap-flag, **Disconfirmer: what one fact flips this?**, Boundary-case; renders all clients via A1-S3. **Disconfirmer-use decision + DoD: MVP = passive back-display** (disconfirmer shown on the answer side); **ROADMAP = active-retrieval prompt** (front: "what one fact would flip this?" → student answers → reveal). Resources: $0; 1×J; 0.5 day. Deps: A1-S3 (authored on desktop via A1-S2). Accept: all fields save; **MVP DoD = disconfirmer renders on the back across stock clients**; the active-retrieval front variant is logged for post-MVP. Binding/faithful: student authors the body (generation effect) — no AI auto-authoring (anti-pattern #1).

**A2-S2 — Miss ingestion (FORK — 3). [MVP: a+b]** (a) QID tag-lookup (paste UWorld/AAMC QID → `uworld:NNNNN` tag → spawn scaffold; stores only the student's OWN write-up); (b) manual paste/typing; (c) OCR of the student's OWN handwritten notes (Mistral OCR $4/1k [$2 batch] or Google/AWS $1.50/1k). NEVER screenshots of UWorld/AAMC (ToS auto-closes the account). Recommended (a)+(b). Resources: (a)/(b) $0; (c) ~$0.45–1.20/300pp. Deps: A1-S2. Accept: a miss logged from a QID/paste in <30s; no copyrighted stem stored. Binding/faithful (legal): student-authored ONLY (AAMC/UWorld ToS).

**A2-S3 — Surface-perturbation authoring scaffold with a CONCRETE mechanic (desktop-prepare). [MVP]** How: a concrete flow, not a vague "perturb." The student works a **surface-dimension checklist** that varies while the deep principle is held fixed: **cover-story/context** (original cover-story → swapped cover-story, both stored as fields), **named entities**, **units**, **numeric values**, **question framing/polarity**, **representation (prose↔diagram)**. AI (A10) may surface a severe-test PROMPT as a thinking aid only — it never writes the body. Resources: $0 (+optional LLM); 1×J/P; 0.5–1 day. Deps: A2-S1. Accept: the finished card holds one deep principle constant while ≥1 named surface dimension is provably swapped (original vs swapped cover-story both present); AI populated nothing. Binding/faithful: automation never touches the body (anti-pattern #1); the checklist makes "perturbation" concrete, not a restated concept.

**A2-S4 — Disconfirmer validation (reject blank/answer-restating). [MVP: basic]** How: client heuristics — non-empty; not a restatement of the answer; optional embedding-similarity ceiling (OpenAI text-embedding-3-small $0.02/1M); student can override. Resources: ~cents; 1×J; 0.5 day. Deps: A2-S1. Accept: blank/restating disconfirmer rejected with a revise prompt. Binding/faithful: AI heuristic, not authoritative grader (anti-pattern #6).

---

## A3 — Deep-structure SORT verification gate (SPOV 2) — needs A1 [MVP: thin]

**A3-S1 — Author principle-sharing families (surface×deep crossing) + independent QA + pilot-sort. [MVP: 1 SMALL demo set]** How: Chi/Feltovich/Glaser 1981 construction — CROSS surface×deep (same principle/diff cover; same surface/diff principle); "sort by how they'd be solved." **MVP "set" = a SMALL crossed set of ~6 items (2 deep principles × 3 surface covers = one principle PAIR), explicitly labeled "demo, not transfer-validated."** Full set = ~24 items. **Independent QA (matches A4-S1's bar):** a SECOND author independently classifies each item's surface + deep tags (must agree), AND a **pilot-sort on 2–3 humans** must confirm a **surface-only sorter FAILS** (the correct sort requires the deep principle). Resources: 1×C (in-house for MVP) + 1×C reviewer; ~0.5–1.5 hr/item. Deps: concept families (A4 graph helps); start day 1. Accept: a held-out ~6-item set where (i) two authors agree on surface+deep tags and (ii) the 2–3-person pilot-sort shows surface-only matching fails; labeled "demo, not transfer-validated." Binding/faithful: crossing independently verified; no auto-tagging (anti-pattern #3); honest demo-grade label.

**A3-S2 — Held-out split logic (desktop-prepare). [MVP]** How: Python splits each family studied vs held-out; the sort uses only held-out; emit the split as a tag/companion. Resources: $0; 1×P; 0.5 day. Deps: A1-S2, A3-S1. Accept: sort items provably disjoint from studied. Binding/faithful: held-out gate, not accuracy.

**A3-S3 — Sort-task template (review-tier JS). [MVP]** How: template `<script>` drag/tap "which two share the principle?", cross-client on STOCK clients (A1-S3). Resources: $0; 1×J; 1 day. Deps: A1-S3, A3-S2. Accept: student completes a sort on stock desktop+AnkiDroid+AnkiMobile (result captured local; persisted via A3-S4). Binding/faithful: capture-local on mobile.

**A3-S4 — "transfer-trained" status flag + gate (AUTHORITATIVE WRITE = desktop reconcile). [MVP]** How: on sort pass set `customData {"tt":1}` (≤100B) and/or a `#tt` tag; **READ native** (A1-S1 search / PR #4880). **WRITE re-scoped:** **desktop-prepare reconcile is AUTHORITATIVE** (the sort result lives in the webview, which is NOT a scheduling-transform input → must be reconciled desktop-side); **mobile customData-at-answer = Android-only, version-contingent** (test #14865 per A1-S0, never assume); **iOS = capture-local / practice-only** (no synced unlock until a desktop reconcile runs). Gate on sort pass, NOT perturbed accuracy. Resources: $0; 1×J/P; 0.5–1 day. Deps: A1-S0, A1-S2 (authoritative write), A1-S3, A1-S4, A3-S3. Accept: a passed sort → desktop reconcile flips `tt` + unlocks, syncs to stock clients; on iOS the pass is practice-only pending reconcile; fail doesn't flip. Binding/faithful: gated on held-out sort, never accuracy/streaks (anti-pattern #8); write desktop-authoritative (GAP-2 resolved).

---

## A4 — Curated discrimination-drill library (SPOV 3) — needs A1 [MVP: 1–2 sets]

**A4-S1 — Author curated confusable sets (IN-HOUSE for MVP). [MVP: 1–2 sets]** How: sets (acids/bases vs buffers; competitive / non-competitive / uncompetitive inhibition; SN1/SN2); each drill forces *why X-not-Y* (mechanism) + *what consequence differs* — not the label; volunteer hand-merge model (AnKing MileDown-style), NEVER auto-tagged. **MVP content = IN-HOUSE expert only; hiring MCAT tutors moves to POST-MVP** (Wyzant $40–75/hr; senior $150–250/hr) for scale. **"Set" defined: ~8–12 drills per confusable set** (MVP = 1–2 sets ≈ 8–24 drills). Resources: MVP 1×C (in-house); POST-MVP scale = the largest non-software cost (100 drills @0.5–1.5 hr ≈ **$4,000–18,750** at tutor rates). Deps: opt-in after baseline; start day 1. Accept: ≥1 **peer-reviewed** set of ~8–12 drills with mechanism+consequence per drill (independent reviewer, matching A3-S1). Binding/faithful: curated/human-reviewed, science-only, never auto-tag (anti-patterns #3, #9).

**A4-S2 — Concept-graph as a tag namespace. [MVP]** How: tag namespace (`#confusable::inhibition::competitive`); suspend-all / unsuspend-by-tag = opt-in; bigger metadata → companion store. Resources: $0; 1×P; 0.5 day. Deps: A1-S4. Accept: drills addressable by graph tags; unsuspend-by-tag gates them. Binding/faithful: opt-in, never auto-cluster.

**A4-S3 — Drill generator + free-response capture (AUTHORITATIVE WRITE = desktop reconcile). [MVP: thin]** How: desktop-prepare generator emits drills; the review template captures free-response in the webview; light keyword/embedding match to the human key (not authoritative AI grading). **WRITE re-scoped:** the free-response is captured **local** → **desktop reconcile is AUTHORITATIVE**; mobile-at-answer = Android-only/version-contingent (A1-S0); **iOS = capture-local / practice-only**. Resources: cents; 1×J/P; 1 day. Deps: A1-S0, A1-S2 (authoritative write), A1-S3, A4-S1, A4-S2. Accept: student gets a drill, names the mechanism, gets source-backed feedback; the response persists via desktop reconcile (Android-at-answer only if A1-S0 confirms; iOS practice-only); never final-auto-graded. Binding/faithful: human key decides correctness (anti-pattern #6); write desktop-authoritative.

---

## A5 — Support-fading difficulty engine (SPOV 10) — needs A1 [DEFER]

**A5-S1 — Per-family expertise estimator (desktop-prepare). [DEFER]** How: count per-family unaided successes + transfer passes; fade only after ≥2 unaided + 1 transfer item; store rung state **desktop-prepared** (tags/companion; ≤100B flag) — desktop reconcile authoritative, consistent with the write rule. (**GAP-4:** estimator formula — mastery threshold vs py-irt Bayesian.) Resources: $0 (py-irt MIT); 1×P; 1 day. Deps: A1-S2. Accept: advances only on threshold; reports per-family rung. Binding/faithful: per-family, never a global hard-mode (anti-pattern #4).

**A5-S2 — Author backward-fading worked examples + principle prompts. [DEFER]** How: Renkl & Atkinson backward fading — full → completion (last step omitted) → last two omitted → open; principle-naming prompt each rung; same deep structure / diff surface (Chi crossing); fade toward explaining the rejected alternative. Resources: 1×C; 0.5–1.5 hr/item. Deps: A4-S1 style. Accept: a family has a 4-rung ladder with principle prompts. Binding/faithful: high-element content only; never declarative recall.

**A5-S3 — Fade-ladder state machine + incremental-reveal template. [DEFER]** How: front-side incremental reveal = template `<script>`+CSS via Anki-Cloze-Interactive `data-cloze`/Closet (native clozes are HTML-converted → use data attrs); rung selection desktop-prepared (A5-S1); rung advance captured local → **desktop reconcile authoritative**. Resources: $0; 1×J; 1–2 days. Deps: A1-S3, A5-S1, A5-S2. Accept: student moves worked-example→completion→open across sessions; high-element only; declarative untouched. Binding/faithful: per-family fading NOT global hard-mode (anti-pattern #4); write desktop-authoritative.

---

## A6 — MC feedback + error-classification engine (SPOV 6) — needs A1 [DEFER; thin=stretch]

**A6-S1 — Commit-then-reveal MC/application card type + explicit AI-distractor WALL. [DEFER]** How: template `<script>` MC (cross-client per AI-Hints, stock clients). **Explicit wall: NO AI-suggested distractor ships without (a) human review AND (b) a cited source** — AI may only *suggest* candidates; a human + a source decide what ships. Resources: $0; 1×J; 1 day. Deps: A1-S3. Accept: card commits then reveals per-distractor rationale on all stock clients; **a provenance check blocks any distractor lacking human sign-off + a citation.** Binding/faithful: AI suggests, human+source decide (anti-patterns #1, #6).

**A6-S2 — Source-backed distractor rationales + per-distractor QA. [DEFER]** How: author "why the lure tempts / what false model / what drill follows"; per-distractor point-biserial (+key, −distractors) via girth/psychometrics. Resources: 1×C; $0 psychometrics. Deps: A6-S1, A9-S2. Accept: each distractor has a source-backed rationale; per-distractor r_pb computed. Binding/faithful: source-backed, human-authored.

**A6-S3 — Forced error-classification + ONE remediation card (WRITE = desktop reconcile, load-managed). [DEFER]** How: error-type menu (content/reasoning/trap/timing); queue ONE remediation card into FSRS (AnkiAIUtils failure-triggered field; Minimum Information Principle — no over-atomization); generated desktop-prepare. **WRITE re-scoped:** the error-class pick + remediation-card creation persist via **desktop reconcile (authoritative)**; mobile-at-answer = Android-only/version-contingent (A1-S0); **iOS = capture-local / practice-only** (remediation queued at next desktop reconcile). Resources: $0 (+optional LLM); 1×J/P; 1–2 days. Deps: A1-S0, A1-S2 (authoritative write), A6-S1. Accept: a miss yields exactly one remediation card + error-type tag via desktop reconcile; no review-debt blowup. Binding/faithful: the engine is the feature; one card (load cap); write desktop-authoritative.

---

## A7 — Confidence capture + high-confidence-wrong router (SPOV 7) — needs A1 [DEFER]

**A7-S1 — Post-commit confidence capture (WRITE = desktop reconcile). [DEFER]** How: template JS captures confidence AFTER commit (don't reward hedging). **WRITE re-scoped:** confidence is captured in the webview (NOT a scheduling-transform input) → **desktop reconcile is AUTHORITATIVE**; mobile per-state customData-at-answer = Android-only, version-contingent (A1-S0, test #14865); **iOS = capture-local / practice-only**. Resources: $0; 1×J; 0.5–1 day. Deps: A1-S0, A1-S2 (authoritative write), A1-S3, A1-S4. Accept: confidence recorded only post-commit; persists via desktop reconcile (Android-at-answer if confirmed; iOS local); ≤100B/card if via customData. Binding/faithful: post-commit only; confidence never alters intervals (anti-pattern #7); write desktop-authoritative.

**A7-S2 — High-confidence-wrong detection + false-model capture. [DEFER]** How: detect high-confidence + wrong; present a menu of candidate false models; record the pick (desktop-reconciled). Resources: $0; 1×J; 0.5 day. Deps: A7-S1. Accept: HCW items flagged + tagged with a false model. Binding/faithful: confidence used only to route.

**A7-S3 — Route HCW → misconception drill (desktop-prepare). [DEFER]** How: desktop-prepare routes HCW → a source-backed misconception drill (reuse A4/A6); NO dashboard; NO confidence-only FSRS change. Resources: $0; 1×P; 0.5–1 day. Deps: A1-S2, A7-S2. Accept: an HCW item produces a drill; confidence never alters intervals / isn't a vanity metric. Binding/faithful: confidence used ONLY to route HCW (anti-pattern #7).

---

## A8 — Exam-date desired-retention RAMP (SPOV 11) — needs A1 [DEFER]

**A8-S1 — Test-date input + ramp-curve math (desktop-prepare). [DEFER]** How: per-card DR = f(days-to-exam, yield, weakness); cap below the >97% workload cliff (MCAT consensus 88–92%); high-yield/weak first; simulate with fsrs-rs `simulate` (don't reimplement FSRS). (**GAP-5:** exact ramp curve / cap schedule.) Resources: $0 (fsrs-rs BSD-3 v6.6.1); 1×P; 1–2 days. Deps: A1-S2. Accept: a date yields a capped, prioritized per-card DR plan + projected workload. Binding/faithful: a ramp over FSRS, not a cram override.

**A8-S2 — Per-card DR write path — the PRODUCT-DEFINING schema-vs-stock-client fork. [DEFER]**
- **(a) A8-S2a = THE plan (keep stock clients) [recommended, ships]:** workaround with **no new schema field** — bucket cards into per-DR decks (per-deck DR, PR #4194 / 25.09) OR store `{"dr":92}` in **customData** (NOT a new field); review order = ascending/descending retrievability off each card's DR; **READ is native** (PR #4880 `ctx.desired_retention` + the A1-S1 search). Keeps **stock clients + AnkiWeb sync** working. Resources: $0; 1×P. Deps: A1-S2, A8-S1.
- **(b) A8-S2b = a separate engineering SPIKE (≈1–2 weeks), product-defining [OPTIONAL headline Rust change]:** a **native per-card-DR WRITE via a NEW schema column breaks stock-client + AnkiWeb sync → forces own-sync-server + own-forked-clients.** To KEEP stock clients, the native write must target **customData, NOT a new field.** Sub-tasks + DoD: (1) per-card DR storage design (choose customData to preserve stock sync), (2) protobuf/backend write, (3) schema migration, (4) sync of the field, (5) confirm the **scheduler consumes it** (already exposed by PR #4880), (6) an **FSRS-integrity regression test vs a cram-override arm** (the ramp must not corrupt intervals where a cram-override visibly would). Resources: 1×R, ≈1–2 weeks. Deps: A1-S1, A1-S2, A8-S1.

Accept: (a) per-card DR applied + read on all **stock** clients, FSRS not corrupted; (b) native write lands behind the 6-step DoD with the FSRS-integrity regression green AND a documented stock-client/sync-impact decision. Binding/faithful: a DR ramp OVER FSRS, not a cram override (anti-pattern #10); (b) must not silently break stock-client sync. **The MANDATORY MVP Rust change lives in A1-S1; A8-S2b is the OPTIONAL higher-value one.**

**A8-S3 — Workload cap + interval-corruption guard. [DEFER]** How: cap DR per yield; reschedule-on-change to pull reviews in (build on `fsrs4anki-helper` "Advance" = least-impact-on-retention); audit intervals vs a cram-override arm. Resources: $0; 1×P; 1 day. Deps: A8-S1, A8-S2. Accept: the ramp never exceeds the cap; the corruption audit passes while a cram-override arm visibly fails. Binding/faithful: cap enforced; not a cram override.

---

## A9 — Falsifiable metrics layer (SPOV 5) — [MVP: S1+S2 thin]

**A9-S1 — Metrics from the NATIVE synced revlog + a desktop analytics pass (NOT a mobile POST). [MVP]** How: **do NOT assume a mobile client POST/persist.** Assemble metrics from the **native synced revlog** (item / response / latency — already synced by stock clients) + **desktop-prepared customData/tags** (rung / family / held-out flag — written by A1-S2 reconcile) via a **desktop analytics pass** that reads the synced collection and exports `{item, response, latency, rung, family, held-out flag}` to PostHog (free 1M events/mo) or local SQLite. Ops/UX telemetry, NOT evidence of learning. Resources: $0; 1×P; 0.5–1 day. Deps: A1-S2 (the analytics pass + the prepared tags/customData); the revlog comes free from stock-client sync. Accept: a desktop pass produces events with all fields **without relying on any mobile write-back** (revlog = native; rung/family/held-out = desktop-prepared). Binding/faithful: telemetry not proof (anti-pattern #8); no mobile-POST assumption (GAP-2 resolved).

**A9-S2 — Point-biserial discrimination pipeline. [MVP]** How: corrected r_pb (exclude the item from the total; per-distractor for A6) via girth/psychometrics (MIT, $0); compare transfer-trained vs recall clozes (target Δr_pb ≥0.1). Resources: $0; 1×P; 1 day. Deps: A9-S1. Accept: r_pb per item; transfer-vs-cloze comparison reportable. Binding/faithful: discrimination, not accuracy.

**A9-S3 — PFL proxy pipeline (trials-to-next-concept). [DEFER]** How: PFL = double-transfer (instruct A → new learning on novel B → score B-learning; Bransford & Schwartz; Mylopoulos d=0.62); proxy = trials-to-acquire the next concept after remediation vs matched non-remediated. Resources: $0; 1×P; 1–2 days. Deps: A9-S1. Accept: trials-to-next-concept computed for remediated vs matched. Binding/faithful: PFL proxy, not accuracy.

**A9-S4 — Honest reporting + held-out eval + planted-bug test. [DEFER]** How: dashboard shows discrimination + PFL; REFUSES accuracy/streaks/completion% as evidence (kept as ops); planted-broken-feature detection test. Resources: $0; 1×P; 1–2 days. Deps: A9-S2, A9-S3. Accept: no accuracy/streak presented as proof; the planted-bug test shows discrimination+PFL detect it. Binding/faithful: refuses accuracy/streaks as evidence (anti-pattern #8).

---

## A10 — AI lane: severe-test generator + crutch kill-switch (SPOV 9) — needs A1 [DEFER]

**A10-S1 — Author the human key + provenance/trust record. [DEFER]** How: per concept, a key (correct solution + common mistakes) — also the PoisonedRAG defense; record provenance/trust for every AI artifact. Resources: 1×C; 0.5–1.5 hr/concept. Deps: A4-S1. Accept: every AI-touched concept has a human key + provenance. Binding/faithful: human key decides; AI never grades (anti-pattern #6).

**A10-S2 — Severe-test generation prompt (FORK — model choice). [DEFER]** How: prompt = enumerate assumptions → "what breaks if dropped?" → boundary/edge cases; verdict format vs key (`[[VERDICT]]`/`[[TEST]]` → consistent or a counterexample the student answers UNASSISTED); AI never final-grades. (a) GPT-4.1-mini (~$10.40/5k-mo); (b) Gemini 2.5 Flash (~$13); (c) Haiku 4.5 (~$30). Recommended (a), pick per eval. Resources: ~$10–30/mo. Deps: A1-S2, A10-S1. Accept: AI emits boundary-case items vs key; never a final grade. Binding/faithful: generate-only, never grader/body (anti-pattern #1).

**A10-S3 — Prompt-injection / PoisonedRAG defense. [DEFER]** How: PoisonedRAG (~5 docs→~90% ASR) → provenance + isolation; validate AI output vs the human key; retrieved text never issues instructions; no auto-execution. Resources: $0; 1×P; 1 day. Deps: A10-S1, A10-S2. Accept: a red-team doc can't make the generator emit an attacker answer that passes the key. Binding/faithful: isolation + key-validation.

**A10-S4 — Legal prerequisites (OpenAI DPA + retention disclosure + GDPR). [DEFER — legal gate]** How: sign the OpenAI DPA (team = controller); disclose 30-day abuse retention (ZDR enterprise/approval-gated); GDPR lawful basis + privacy notice + sub-processor disclosure, or geo-limit EU. Resources: 1×L + [legal — see the legal-review quote gate in Cost reality]. Deps: before A10 ships to EU. Accept: DPA signed, disclosure live, lawful basis documented (or EU geo-limited). Binding/faithful (legal): no covered data to the LLM until DPA + disclosure.

**A10-S5 — Assisted/unassisted crutch A/B harness (kill-switch). [DEFER]** How: Bastani et al. 2025 PNAS 3-arm (Control / AI-base / guardrailed): intro → ASSISTED practice → UNASSISTED closed-book exam on matched items; pre-registered primary = unassisted; ship only if the assisted−unassisted gap doesn't widen; guardrail prompt = solution + mistakes + "hints not answers"; PostHog free for flags. Resources: $0; 1×P; 2 days. Deps: A9, A10-S2. Accept: the harness measures assisted vs unassisted on matched items + auto-kills a crutch-signature feature. Binding/faithful: kills assisted-up/unassisted-down scaffolds.

---

## A11 — CARS product decision (SPOV 12) — [MVP: decision only]

**A11-S1 — Decide build-vs-integrate (FORK — 3). [MVP]** CARS = a different construct (AAMC: no specific content knowledge → recall low signal); NOT a primary deck/KPI. (a) BUILD a separate timed-passage + error-pattern module (inference/tone/scope/timing) from licensed/original or verified-free AAMC/Khan passages (**GAP-1:** verify the reuse license); (b) INTEGRATE Jack Westin (BD/licensing; "no public API" UNVERIFIED → a BD question, not self-serve); (c) DEFER CARS (science-focus; optional vocab/taxonomy micro-cards only). Resources: 1×L/PM + [legal/BD]; ~0.5 day. Deps: GAP-1. Accept: a written decision with the licensing path confirmed. Binding/faithful: not a CARS deck/KPI (anti-pattern #9).

**A11-S2a (if build) — Timed-passage module + error-pattern analytics. [DEFER]** How: passage UI + timer + per-passage questions + error-pattern analytics; content licensed/verified-free/original. Resources: content licensing = the binding cost; 1×J/P 3–5 days. Deps: A11-S1(a), A1-S3, A9. Accept: a timed passage runs with error-pattern analytics; no CARS deck; accuracy is not the KPI. Binding/faithful: passages + error-pattern, not a deck.

**A11-S2b (if integrate) — Jack Westin handoff. [DEFER]** How: redirect/partnership to JW daily free + QBank (~3,044 passages); never reproduce passages. Resources: [BD/licensing]. Deps: A11-S1(b). Accept: students reach CARS via the integration; no passages scraped. Binding/faithful: not a CARS content deck/KPI.

---

## A12 — Non-distorting motivation layer (SPOV 8) — [MVP: thin private indicator optional]

**A12-S1 — Private mastery/coverage progress UI. [MVP: optional thin]** How: private indicators over A9 events; pure product/UX. Resources: $0; 1×J; 1 day. Deps: A9-S1. Accept: a private mastery view; nothing public/comparative. Binding/faithful: private only (anti-pattern #5).

**A12-S2 — Recovery streaks + effort-credit for hard items. [DEFER]** How: recovery streaks reward RETURNING (not loss-framed unbroken streaks); effort-credit for flagged-hard / low-confidence attempts. Resources: $0; 1×J; 1 day. Deps: A9-S1. Accept: lapsing isn't punished; hard-item attempts earn credit. Binding/faithful: no loss-framing (anti-pattern #5).

**A12-S3 — Explicit exclusion guard. [DEFER]** How: a product guardrail/lint forbidding public ranking + loss-framed streak penalties (Deci; Huang 2024 LBL-negative; UMN). Resources: $0; 0.25 day. Deps: none. Accept: a checklist/guard blocks any leaderboard / loss-streak. Binding/faithful: only non-distorting motivation (anti-pattern #5).

---

## Corrected 3-day MVP (stock-client, operator version)

**Wed — prove the two-tier loop on STOCK Anki desktop (+ fork build in parallel).**
- Build the **Miss→Card note type** with **fields FROZEN by EOD** (schema-stability guard — field edits force a full sync). [A2-S1]
- A **custom-scheduling script** that READS `ctx.desired_retention` / `ctx.decay`. [A1-S3 / A8 READ]
- A **paginated AnkiConnect prepare script** that stamps a **tag + `{"tt":1}` customData** and **VISIBLY syncs to a stock phone**, idempotent/resumable/backup-first/clients-quiesced. [A1-S2, A1-S4]
- Run the **A1-S0 spike** to confirm the per-client write matrix.
- **In parallel (off the path):** fork `just run` green on a **Linux box** with the `extract_custom_data` Rust change. [A1-S1]

**Fri — A2 full + A3 thin + metrics.**
- A2 ingestion / perturbation / disconfirmer-validation. [A2-S2/S3/S4]
- A3 thin: **sort template on desktop + AnkiDroid**, **`tt` gate via DESKTOP reconcile**, **one demo-labeled small (~6-item) sort set** with independent QA + a 2–3-person pilot-sort. [A3-S1→S4]
- Metrics: the **desktop analytics pass** over the native revlog + prepared tags, and the **point-biserial** pipeline. [A9-S1, A9-S2]

**Sun — content + DR workaround + honest stock-mobile demo.**
- **1–2 in-house confusable sets** (desktop reconcile for captured responses). [A4-S1/S2/S3]
- **A8-S2a customData-only DR** (no Rust write). [A8-S1, A8-S2a]
- A demo that **runs the review tier on STOCK mobile.**
- **Honest demo caveats (say them out loud):** sort/confidence gates are **desktop-reconciled**; content is **demo-grade, not transfer-validated**; **native Rust DR write (A8-S2b), own-sync (A1-S5a), and iOS (A1-S6) are post-MVP**; APKG is **demo transport, not convergence**.

**Defer:** iOS (A1-S6), self-hosted sync (A1-S5a), A5, A6 full, A7, A8-S2b (native-write spike), A10 (LLM + DPA), A11 build/integrate, A12 beyond a private indicator.

---

## Cost reality (replaces the "$0" claim)
- **MVP ~$0 cash is true ONLY if:** APKG-only (no sync server) **and** no-LLM **and** no hired content (in-house authoring) **and** stock clients. Break any of those and cost appears.
- **Credible-pilot all-in ≈ $5k–25k**, composed of:
 - **Content authoring $5k–25k** — the dominant cost (100 drills @ tutor rates $4,000–18,750; more with senior reviewers/QA).
 - **Ops** — self-host sync DO droplet **$6–12/mo** + maintenance.
 - **LLM (A10)** — **$10–30/mo** (GPT-4.1-mini / Gemini 2.5 Flash / Haiku 4.5) + embeddings $0.02/1M.
 - **Store fees** — **Apple $99/yr** + **Google Play $25 once**.
 - **Hidden fork-maintenance labor** — tracking Anki/FSRS churn (the fork must re-merge upstream + re-test the custom-scheduling/customData surface each release).
- **Legal-review quote gate (binding):** obtain a legal quote/sign-off **before shipping** any of — **A1-S5(a) self-hosted sync** (AGPL §13 source-offer + GDPR data-controller duties), **A2-S2 ingestion** (AAMC/UWorld student-only ToS), **A10** (OpenAI DPA + 30-day retention disclosure + GDPR lawful basis), **A11** (CARS content reuse license, GAP-1). Building is free; **shipping these is gated on the legal quote.**

---

## Critical path (load-bearing sequence)
```
A1-S0 (write/parity spike) ─┐ [blocks all review-tier WRITE steps]
 ▼
A1-S2 (prepare = AUTHORITATIVE write) → A1-S3 (stock review runtime) → A1-S4 (tags/customData)
 │
 ├─► A2 (S1→S2→S3→S4) [flagship]
 ├─► A3 (S1∥ + QA/pilot-sort ; S2→S3→S4 via DESKTOP reconcile)
 ├─► A4 (S1∥ in-house ; S2→S3 via DESKTOP reconcile)
 ├─► A9 (S1 desktop analytics over native revlog → S2) → feeds A6-S2/A10-S5/A12
 ├─► A8 (S1→S2a ships ; S2b = OPTIONAL ≈1–2wk native-write spike) [DEFER]
 └─► A5 / A6 / A7 / A10 / A11 / A12 [DEFER]

PARALLEL, OFF THE PATH: A1-S1 (fork build + mandatory extract_custom_data Rust change)
LEGAL/PILOT GATES: A1-S5a (sync = §13+GDPR) ▸ A1-S6 (iOS) ; A2-S2 ; A10-S4 ; A11-S1 (GAP-1)
```
- **Content authoring (A3-S1 / A4-S1 / A5-S2 / A6-S2 / A10-S1) is the long pole — start day 1.**
- **Legal gates that block SHIPPING (not building):** A1-S5a/S7 (§13 + GDPR controller), A1-S6 (App-Store/AGPL), A2-S2 (student-only), A10-S4 (DPA/GDPR), A11-S1 (content license) — each behind the **legal-review quote gate**.

---

## Implementation Knowledge Tree (updated; full citations in raw-*.md + 01b)
- **A1:** one engine, two tiers + **stock review clients** (rslib+rsbridge → AnkiDroid JNI 3-fn `openBackend/closeBackend/runMethodRaw` → iOS C-FFI; over protobuf); custom-scheduling `SchedulingContext{deck_name, seed, decay, desired_retention}` answer-time re-weight, **no queue handle** (SPOV 4; PR #4880 commit 83d711f, 2026-06-08); `customData` ≤8B keys / ≤100B total, key `"cd"`, native `dr`/`decay` are separate fields (`validate_custom_data`, rslib `data.rs`); **AnkiConnect = HTTP server inside a live Qt GUI** (`:8765`, GPLv3, `git.sr.ht/~foosoft/anki-connect`; headless=xvfb); review = template JS on **stock** clients (AI-Hints proof, no add-on/fork); **single-writer `with_col`** → prepare must be idempotent/resumable/paginated/backup-first/quiesced; **note-type field/template edits = schema-modifying = forced full sync** (scratch profile + freeze fields); **APKG round-trip ≠ convergence** (no scheduling/customData preservation; GUID-collision dup); AGPL-3.0 (binding holder = the AGPL core / Ankitects, upstream contribs BSD-3); AnkiWeb ToS bans third-party clients w/o written permission; anki-sync-server individual/family, HTTP-only, no-REST, **§13 + GDPR controller** when self-hosted; App-Store §7 conflict (VLC/GNU-Go removals) → no own-engine iOS app; Play permits AGPL. **Mandatory Rust change = `extract_custom_data` SQLite search/column (A1-S1).**
- **A1-S0 / write path (GAP-2/3 RESOLVED):** the only synced write from the review flow is `customData` written **at answer time** by the scheduling transform (persists only on grade; `ts/reviewer/answering.ts`); the **webview-captured value is NOT a transform input** (inputs = `states` + `{deck_name,seed,decay,desired_retention}`); AnkiDroid `customData`-populate historically broken (#14865 — must set before answering); **AnkiDroidJS get/set tags (#17795) is the blessed Android synced write**; **AnkiMobile has NO synced write path** (only sessionStorage/localStorage, local). → **desktop reconcile authoritative; Android-at-answer version-contingent; iOS practice-only.**
- **A2:** UWorld-QID add-on pattern; AAMC/UWorld non-ingestible (student-authored only); user-generated > premade d=0.45/0.29 (Pan 2023); generation ~.40 (Bertsch); BMC "all faulty" (anti-pattern #1); AnkiAIUtils/MyAnswerChecker compliant patterns; **perturbation mechanic = original→swapped cover-story + surface-dimension checklist (A2-S3).**
- **A3:** Chi/Feltovich/Glaser 1981 sort (surface×deep crossing); transfer conditional d=0.40 (Pan & Rickard); **MVP set = ~6 items / 2×3, demo-labeled; independent-reviewer QA + 2–3-person pilot-sort**; `tt` flag ≤100B written via **desktop reconcile**.
- **A4:** interleaving g=0.42 / words −0.39 / expository ns (Brunmair & Richter); Rohrer = mechanism not magnitude; AnKing hand-merge + tag-graph; **MVP = in-house; tutors POST-MVP**; set = ~8–12 drills; scale authoring $4k–18,750.
- **A5:** expertise reversal d=0.505 / −0.428 (Tetzlaff 2025); backward fading + principle prompts (Renkl & Atkinson); Anki-Cloze-Interactive/Closet; rung state desktop-prepared.
- **A6:** MC lures + feedback (Butler & Roediger); Rowland g≈0.03 no-feedback ≤50%; per-distractor point-biserial (girth); AnkiAIUtils one-card remediation; **AI-distractor wall = human review + cited source.**
- **A7:** JOL bias / illusion of competence (Koriat & Bjork) → no dashboard / no confidence-only FSRS; confidence captured post-commit, **desktop-reconciled**.
- **A8:** READ native (PR #4880); per-deck DR (PR #4194 / 25.09); per-card-DR WRITE unmerged (jhhr) → **A8-S2a customData/deck-bucket workaround = THE plan (read-native, keeps stock sync)**; **A8-S2b native write = ≈1–2-wk spike, must target customData not a new column or it breaks stock-client + AnkiWeb sync → forces own-sync + own clients**; raise-DR + "Advance" lever (`fsrs4anki-helper`), cap 88–92%; fsrs-rs `simulate` (BSD-3 v6.6.1).
- **A9:** **metrics from the native synced revlog + desktop analytics pass (no mobile POST)**; corrected point-biserial; PFL double-transfer (Mylopoulos d=0.62); girth/py-irt/psychometrics $0; PostHog free 1M/mo.
- **A10:** assumption-drop / boundary-case prompt + `[[VERDICT]]/[[TEST]]` vs key; Bastani PNAS +48% assisted / −17% unassisted crutch harness; model costs $10–30/mo; OpenAI no-train-default + 30-day + ZDR approval-gated + GDPR; PoisonedRAG 5 docs→90% ASR (USENIX Sec '25).
- **A11:** AAMC CARS = no-content construct; JW daily free + ~3,044 QBank, copyrighted, "no public API" UNVERIFIED (GAP-1).
- **A12:** tangible rewards undermine intrinsic motivation; LBL-negative (Huang 2024); gamification net-positive on average (Sailer & Homner g≈0.49) = contested → ban the mechanics, not the class.

---

## GAPS (remaining open — gap-filling pass; do not guess)
- **GAP-1 (A11):** Jack Westin partnership/API + Khan/AAMC CARS-passage REUSE/redistribution license (BD/legal, not engineering).
- **GAP-4 (A5-S1/A4):** the concrete per-family expertise-estimator formula (mastery threshold vs py-irt Bayesian).
- **GAP-5 (A8-S1):** the DR ramp curve shape + cap schedule (fsrs-rs `simulate` exists; the *policy* is unspecified).

**Resolved (no longer gaps):** **GAP-2** (mobile review-tier WRITE path) and **GAP-3** (AnkiMobile `<script>` persistence limits) — answered in 01b and implemented as the **A1-S0 spike + the desktop-reconcile-authoritative write rule** (iOS = none, Android = tags / version-contingent, desktop = authoritative).
