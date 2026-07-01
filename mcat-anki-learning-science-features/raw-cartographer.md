# Raw research — Cartographer lane (Anki implementation substrate + existing feature/add-on landscape)

### Anki Manual — Notes/Templates/Cloze/Image Occlusion
Stance: cartographer; Link: https://docs.ankiweb.net/editing.html ; https://docs.ankiweb.net/templates/fields.html ; https://docs.ankiweb.net/templates/intro.html
DOK 1 - Facts:
- A note = fields; a card template = the "blueprint" deciding which fields appear front/back; one note → multiple cards. Built-in note types: Basic, Basic (and reversed), Basic (type in the answer), Cloze.
- The Cloze note type is special: cannot be created from a regular type, and you CANNOT add extra card templates to it.
- Anki 23.10+ supports Image Occlusion natively ("a special case of cloze based on images"); modes "Hide All, Guess One" / "Hide One, Guess One"; Rectangle/Ellipse/Polygon.
- Templates support field replacements `{{Field}}`, special fields (`{{Tags}}`,`{{Type}}`,`{{Deck}}`,`{{Card}}`,`{{FrontSide}}`), conditional replacement `{{#Field}}...{{/Field}}`, hint fields `{{hint:Field}}`, type-in-answer `{{type:Field}}`/`{{type:cloze:Text}}`, Deck Override per template, media/LaTeX/TTS.

### Anki Manual — Deck Options (display order, burying, FSRS, custom scheduling)
Stance: cartographer; Link: https://docs.ankiweb.net/deck-options.html
DOK 1 - Facts:
- Display Order = 5 settings: New Card Gather Order, New Card Sort Order, New/Review Order, Interday Learning/Review Order, Review Sort Order.
- New/Review Order can be "Mix with reviews / Show before / Show after" — interleaving of new-vs-review is a BUILT-IN toggle. Gather order options: Deck / position / Random notes / Random cards (NOT semantic-topic interleaving).
- Review Sort Order: "Due date then random" (default), "Relative overdueness," and (FSRS) "Ascending retrievability."
- Sibling burying = three independent toggles (new/review/interday).
- Auto Advance (23.12+): auto-reveal answer / move to next after configured seconds.
- Easy Days: reduces workload on chosen weekdays (FSRS + SM-2).
- Custom Scheduling = a JavaScript field that is a GLOBAL option (applies to the entire collection), exposing the `states` object.
- FSRS is enabled GLOBALLY (not per-preset); Desired Retention (default 90%, recommend <97%) is the most important setting; parameters + DR are preset-specific. FSRS scheduling code lives in `rslib/src/scheduler/states`.

### Anki FAQs — v3 scheduler + algorithm
Stance: cartographer; Link: https://faqs.ankiweb.net/the-2021-scheduler.html ; https://faqs.ankiweb.net/what-spaced-repetition-algorithm
DOK 1 - Facts:
- The v3 scheduler is a ground-up rewrite; add-ons that modified the old scheduler's gathering/answering DON'T work and "monkey patching the scheduler is no longer possible."
- v3 pre-calculates answer-button states and lets you modify them via JavaScript in deck-options — and because it's JS, custom scheduling RUNS ON AnkiMobile + AnkiDroid too (cross-platform), unlike Python add-ons.
- FSRS = Three Component Model (Retrievability, Stability = days for R 100%→90%, Difficulty); per-card DSR fit by ML; code in `rslib/src/scheduler/states`.

### Anki Add-on docs — Hooks/Filters + Reviewer JS
Stance: cartographer; Link: https://addon-docs.ankiweb.net/hooks-and-filters.html ; https://addon-docs.ankiweb.net/reviewer-javascript.html
DOK 1 - Facts:
- Add-ons connect via hooks (no return) / filters (modify first arg); `webview_will_set_content()` injects HTML/JS; `webview_did_receive_js_message()` intercepts `pycmd()` from JS→Python; functions without a hook can be `wrap()`-ed → desktop Python add-ons can patch arbitrary parts EXCEPT the v3 scheduler gathering/answering.
- `gui_hooks.card_will_show` modifies Q/A HTML before display; reviewer fade requires `onUpdateHook`/`onShownHook`.

### Anki dev-docs — Architecture
Stance: cartographer; Link: https://dev-docs.ankiweb.net/en/latest/architecture.html ; https://github.com/ankitects/anki/blob/main/docs/architecture.md
DOK 1 - Facts:
- Layered: core Rust `rslib/` (majority of backend: scheduling, DB) → `pylib/anki/` proxies to Rust via private `rsbridge` → `qt/aqt/` PyQt GUI → web frontend `ts/` (Svelte/TS). Communicate via Protocol Buffers (not public API). Python `DBProxy` sends SQL strings to Rust (rusqlite); rslib is the "source of truth." FSRS engine = separate Rust crate `fsrs-rs`.

### FSRS4Anki Helper add-on
Stance: cartographer; Link: https://github.com/open-spaced-repetition/fsrs4anki-helper
DOK 1 - Facts:
- Provides Postpone, Advance, Load Balance, Easy Days, Disperse Siblings, Flatten. Load Balance only works on reschedule-with-helper (not normal scheduling). Disperse Siblings spreads same-note intervals "to avoid interference." True Retention = pass rate on cards with interval ≥1 day (excludes learning-phase). Auto-disperse-after-each-review "breaks Display Order settings"; Disperse + Easy Days can conflict.

### Built-in Image Occlusion PR #2367 + Review Heatmap + Speed Focus / Auto Advance
Stance: cartographer; Link: https://github.com/ankitects/anki/pull/2367 ; https://github.com/glutanimate/review-heatmap ; https://github.com/glutanimate/speed-focus-mode
DOK 1 - Facts:
- IO was "the most requested feature"; built-in IO makes ONE note with multiple cards (vs IO Enhanced add-on = multiple notes); same dev (Glutanimate) made both.
- Review Heatmap = GitHub-style activity heatmap + streak/averages; bundled into AnkiDroid 2.17.
- Speed Focus Mode (time reminders, auto-reveal, auto-Again) — core functionality "incorporated to Anki" as built-in Auto Advance (23.12+).

### AnkiDroid / AnkiMobile parity
Stance: cartographer; Link: https://ankidroid.org/changelog.html ; https://github-wiki-see.page/m/ankidroid/Anki-Android/wiki/FAQ ; https://docs.ankimobile.net/more.html ; https://forums.ankiweb.net/t/add-ons-for-ankimobile/32831
DOK 1 - Facts:
- AnkiDroid 2.17 "directly includes Anki Desktop code now": Image Occlusion, Review Heatmap+stats, FSRS, v3 default, custom-scheduling JS. BUT AnkiDroid CANNOT run Python add-ons ("mobile OSes don't let apps run code not packaged with the app — only exception is HTML/JS"); JS add-on support in progress.
- AnkiMobile (iOS) has NO add-ons (Swift+Rust core; Apple bans unreviewed third-party code) but DOES support template JavaScript + a "User Actions" hook to call a template function (e.g. `revealNext()`); MathJax yes, LaTeX no. → cross-platform features must be in-app (Rust) or card JS.

### Card JavaScript caveat
Stance: cartographer; Link: https://docs.ankiweb.net/templates/styling.html
DOK 1 - Facts:
- Card JS is "provided without any support or warranty," not guaranteed across updates; must use `document.getElementById()` not `document.write()`; behavior must be tested per-platform.

### Cloze Overlapper / Closet / Enhanced Cloze (front-side reveal constraint)
Stance: cartographer; Link: https://github.com/glutanimate/cloze-overlapper/wiki/FAQ ; https://github.com/nihil-admirari/modern-cloze-overlapper
DOK 1 - Facts:
- Anki converts native clozes to HTML BEFORE template scripts run, and clozes not belonging to the current card become plain text — so on the FRONT there is "no way of telling what's clozed out" on a sibling card. → incremental/overlapping reveal needs an add-on / the Closet framework (wraps clozes in queryable spans via in-template JS); pure-template solutions only work on the BACK side.
- Cloze Overlapper turns lists into overlapping sequential cards; modern-cloze-overlapper supports nested clozes/MathJax/context counts.

### Pop-up Dictionary / Hint Hotkeys / Frozen Fields; Gamification add-ons
Stance: cartographer; Link: https://github.com/glutanimate/popup-dictionary ; https://github.com/glutanimate/hint-hotkeys ; https://github.com/glutanimate/puppy-reinforcement ; https://github.com/lovac42/ReMemorize
DOK 1 - Facts:
- Pop-up Dictionary surfaces related cards on double-click; Hint Hotkeys reveal `{{hint:}}` fields (H one-by-one, Shift+H all); Frozen Fields "sticky" a field in the editor.
- Puppy Reinforcement = intermittent positive reinforcement images after answering; Ankimon = Pokémon-style game (>15,000 downloads); Leaderboard/Progress Bar add-ons exist. ReMemorize = advanced rescheduler (set interval/due/ease, "Forget" without resetting ease), exposes a hook for other add-ons.

### Filtered Decks / Searching (error-driven review primitives)
Stance: cartographer; Link: https://docs.ankiweb.net/filtered-decks.html ; https://docs.ankiweb.net/searching.html
DOK 1 - Facts:
- Filtered decks gather cards matching a search string into a temp deck; Custom Study presets (review failed today, study ahead, preview new). Search filters for error-driven review: `is:due`,`is:learn`,`is:review`,`is:learn is:review` (lapsed), `prop:lapses>=N`, `tag:`, `prop:due`. Filtered decks have "Reschedule based on my answers" + custom per-button intervals (built-in cram/relearn).

### Anki Releases 25.07 / 25.09 / 26.05 + FSRS-6
Stance: cartographer; Link: https://github.com/ankitects/anki/releases ; https://github.com/open-spaced-repetition/fsrs-rs/pull/313 ; https://expertium.github.io/Algorithm.html
DOK 1 - Facts:
- 25.09 added per-deck desired retention + DR info graphs; recent releases EXPOSE card decay + desired retention to the custom scheduler (PR #4880) and export `last_interval` to Python — the custom-scheduling JS surface is expanding; CMRR removed (25.07, "doesn't work well with FSRS-6"); ~26.05 beta line.
- FSRS-6 in Anki since 25.07: added optimizable decay `w20` (per-user forgetting curve), 19→21 params; default decay −0.5→−0.2 (RMSE ~5-6% better). FSRS-5/6 have only a "crude heuristic," NOT a proper short-term (same-day) memory model.

## Concise summary (cartographer)
1. Note=fields; template=blueprint; Cloze can't add templates.
2. Image Occlusion BUILT-IN since 23.10 (don't reinvent).
3. type-in-answer/hint/conditional/deck-override/TTS = built-in primitives.
4. New-vs-review interleave = built-in toggle; review order random/relative-overdueness/ascending-retrievability.
5. Anki does NOT semantically interleave by topic → concept-aware interleaving is a GAP.
6. Sibling burying built-in.
7. Custom scheduling = GLOBAL JavaScript over a `states` object (desktop+mobile), collection-wide not per-deck.
8. v3 scheduler CANNOT be monkey-patched → scheduling changes via JS box or a Rust fork.
9. Rust `rslib`+`fsrs-rs` = source of truth; pylib proxies via protobuf.
10. Python desktop add-ons can wrap functions + inject reviewer HTML/JS.
11. FSRS Helper already does Load Balance/Easy Days/Disperse Siblings/True Retention (don't reinvent spacing).
12. Auto Advance (built-in 23.12+) supersedes Speed Focus.
13. Review Heatmap bundled in AnkiDroid 2.17.
14. AnkiDroid bundles desktop code but NO Python add-ons (JS in progress).
15. AnkiMobile NO add-ons (Swift+Rust) but supports card JS + User Actions hook.
16. Front-side one-by-one/overlapping cloze reveal IMPOSSIBLE with native clozes (HTML conversion strips sibling info) → needs add-on/Closet; back-side only otherwise.
17. Filtered decks + search (`is:learn is:review`, `prop:lapses>=N`, `tag:`) = built-in error-driven/cram.
18. Current: FSRS-6 (optimizable decay, 21 params, since 25.07); per-deck DR (25.09); ~26.05 beta.

## Candidate experts / add-on authors (cartographer)
Damien Elmes "dae" (anki architecture) https://github.com/ankitects/anki ; Jarrett Ye "L-M-Sherlock" (FSRS, fsrs-rs, FSRS Helper) https://github.com/L-M-Sherlock ; Expertium (FSRS algorithm explainers) https://expertium.github.io ; Glutanimate (Image Occlusion→built-in, Review Heatmap, Speed Focus, Pop-up Dict, Hint Hotkeys, Frozen Fields, Puppy Reinforcement, Cloze Overlapper) https://glutanimate.com ; Luc-Mcgrady (FSRS simulator/DR graphs); kleinerpirat (Closet); nihil-admirari (modern-cloze-overlapper); lovac42 (ReMemorize); iamllama (built-in IO); AnKing (med/MCAT note types).

## Flags (cartographer)
ALREADY EXISTS — don't reinvent: Image Occlusion, FSRS spacing, load balancing/easy days/disperse siblings/true retention (FSRS Helper), Auto Advance auto-timer/reveal, sibling burying, new/review interleave toggle + random review order, type-in-answer, hint reveal hotkeys, review heatmap+stats (bundled in AnkiDroid), filtered-deck cram/failed-today/leech, pop-up related-cards.
REAL GAPS (verify): front-side incremental/overlapping cloze reveal (blocked by HTML conversion); concept/topic-aware interleaving (no semantic clustering); metacognitive calibration (predict-then-grade confidence + predicted-vs-actual feedback — no core feature/add-on); self-explanation/elaboration prompting (only via extra fields); PER-DECK custom scheduling (JS is collection-global); error-driven adaptive sequencing beyond filtered-deck search + leeches (no "cluster my mistakes / remediate weak concepts" engine).
COMPATIBILITY: Anki warns any interval-affecting add-on "shouldn't be used with FSRS," and card JS has no cross-version guarantee → scheduling features should live on the FSRS custom-scheduling surface or in rslib/fsrs-rs, not interval-hacking add-ons.

## CHILD BRAINLIFT CANDIDATE (cartographer)
- Topic: WHERE to implement scheduling/sequencing features — Anki's global custom-scheduling JavaScript surface vs forking the Rust scheduler (`rslib/src/scheduler/states` + `fsrs-rs`)? Big (Rust/protobuf/FSRS-6 internals vs JS sandbox vs Python hooks), contested (JS = cross-platform but global-only/sandboxed/unsupported-across-versions + v3 can't be monkey-patched; Rust fork = full power but loses upstream sync/mobile parity/FSRS update cadence), load-bearing (nearly every feature + mobile parity hinges on it).
- Orchestrator note: this is an IMPLEMENTATION-substrate question — treat as a load-bearing constraint resolved inline (informs every feature SPOV's "how"), not a separate spiky-POV run.
