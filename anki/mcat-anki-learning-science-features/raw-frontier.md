# Raw research — Frontier lane (how top scorers modify Anki; feature requests; current-year releases)

## A. Building cards for APPLICATION, not recognition
### How to Use Anki Effectively for the MCAT (Jack Westin, 2025-2026)
Stance: frontier — [practitioner-opinion]; Link: https://jackwestin.com/blog/how-to-use-anki-effectively-for-the-mcat/
DOK 1 - Facts:
- MCAT "rewards both fast recall and application"; deck "should include cards that match both" — recommends a "Basic open-ended (question to explanation)" card type: "Explain X like you're teaching it," "Predict what happens if I change variable Y," "Compare A vs B."
- Gives a "highest-value card template for MCAT passage performance": front = "In your own words, explain [concept]. Then give one example of how the MCAT could test it in a passage"; back = definition (2-4 sentences) + key cause→effect + one common trap + one mini example.
- "Engage each card like it is a passage question … force yourself to explain, not just recognize"; "say answers out loud." CARS "mistakes are better fixed with strategy, not Anki cards." Loop: Daily Passages + QBank → generate mistake-prevention cards.

### Anki MCAT guides (MCAT Study Planner; WozPrep; StudyCards AI; 2025-2026)
Stance: frontier — [practitioner-opinion]; Link: https://mcatstudyplanner.com/blog/how-to-study-mcat-using-anki/ ; https://www.wozprep.org/articles/practice-question-to-anki-card ; https://studycardsai.com/blog/how-to-use-anki-for-mcat-milesdown
DOK 1 - Facts:
- Hybrid: premade decks for core facts (P/S terms, amino acids, pathways); self-made cards "only for things you miss — especially from AAMC + UWorld." Convert definition→application; "focus on Why and How"; add mini-vignette/context cards.
- Explicit error-tagging scheme: `AAMC_FL1_ChemPhys_Q42`, `FL2_ContentGap`, `FL3_ReasoningError`, `UWorld-Chem_Q145`.
- "If your cards are just screenshots of UWorld, you're missing the point. Make your cards teach you what you didn't know. Focus on reasoning." Method: identify the core concept misunderstood, phrase it general enough for future questions, make multiple cards if a question revealed multiple weaknesses.
- StudyCards AI contrasts a recall card (Bohr Effect) with the actual exam item (right-shifted O2 dissociation curve in respiratory acidosis), prescribing "mental simulation" to bridge the gap; three-phase roadmap (Content Review → Application Integration → Final Taper); AnkiHub UWorld-QID tagging; learning steps "1m 10m."

### AnKing "understand first, then unsuspend" + Pankow P/S + Image Occlusion
Stance: frontier — [forum/practitioner/self-reported]; Link: https://community.ankihub.net/t/lesson-7-unsuspending-cards.../595892 ; https://testpreppal.com/mcat/flashcards/pankow ; https://github.com/glutanimate/image-occlusion-enhanced
DOK 1 - Facts:
- AnKing deck ships all cards suspended (35,000+ cards); workflow = Browse → topic tag → select all → Toggle Suspend; "do not unsuspend a topic you haven't studied … if you memorize but don't understand the physiology, you'll fail to apply it to a vignette. Anki is for retention, not initial learning."
- Mr. Pankow P/S = 2,254 cards by AAMC categories 6A-9A + Khan Academy P/S blocks; "predominantly cloze deletions with multiple variations"; mirrors KA 300-page/86-page docs; folded into AnKing MCAT.
- Image occlusion "essential for anatomy"/pathways/mechanisms; recommended mode "Hide All, Reveal One," one fact per mask.

## B. Recurring FEATURE REQUESTS (forums)
### Deadline / exam-date scheduling (Anki Forums) — most-requested missing feature
Stance: frontier — [forum]; Link: https://forums.ankiweb.net/t/deadline-exam-date-feature/56675
DOK 1 - Facts:
- "One of the most commonly requested scheduling-related features is setting a deadline such that all cards are reviewed at least once before that deadline … surprised Anki doesn't have that." There is NO native due-date; workaround = filtered decks (`prop:due>45 prop:due<90`) + lower max interval. Proposed impl: interval drawn from `[0.75*(days−1), days−1]` to avoid pileup. AnkiHub caution: "cramming right before an exam is less effective than spaced repetition."

### Interleaving controls (Anki Forums + benthamite/anki-interleaver)
Stance: frontier — [forum/release-note]; Link: https://forums.ankiweb.net/t/display-new-learning-cards-in-a-certain-way/52998 ; https://github.com/benthamite/anki-interleaver
DOK 1 - Facts:
- "There's no way to strictly interleave the cards like that (BCDBCDBCD)" natively; approximation = gather order Deck + sort Random. Users split on whether Anki SHOULD add interleaving. A 2025 third-party tool `anki-interleaver` (via AnkiConnect) interleaves new cards across decks preserving within-deck order. AnkiHub: card yield "does not determine its position in Anki, as this runs counter to … interleaving."

### True Retention / stats; self-testing / explain modes (cross-source)
Stance: frontier — [release-note/practitioner]; Link: https://github.com/open-spaced-repetition/fsrs4anki-helper ; https://www.mindomax.com/anki-mcat-flashcards
DOK 1 - Facts:
- True Retention = FSRS Helper feature (not native), Tools→FSRS Helper→Show true retention; also "Remedy Hard Misuse," "Steps Stats." Add-on stats don't show in normal Stats window after 2.1.33 (shift-click) — recurring friction.
- Practitioners force production (open-ended "explain"/"predict," say out loud) as a manual workaround for no built-in free-response self-grading; tag mistake cards into a filtered deck for self-testing.

## C. CARS — practitioners say Anki is the WRONG tool
Stance: frontier — [practitioner-opinion/self-reported]; Link: https://www.mindomax.com/anki-mcat-flashcards ; https://aspiringmd.com/should-i-do-jack-westin-cars-passages-daily/
DOK 1 - Facts:
- "Anki does not work well for CARS … skills that improve through daily passage practice, not flashcard review." A 520-scorer: "CARS was the only section where I did not use Anki. There's nothing to memorize." Jack Westin CARS = 1 passage/day + same-day video; scale to 2-4/day near test. Final-phase CARS split ~0-40% Anki / 60-70% practice (one guide ~90% on timed passages). A CARS feature would need passage delivery + reasoning/error-pattern tracking (fallacy/tone/question-type), NOT content memorization.

## D. What Anki / AnkiDroid / AnkiHub are shipping
### Anki 23.10 + FSRS-default plan + manual
Stance: frontier — [release-note]; Link: https://github.com/ankitects/anki/releases/tag/23.10 ; https://github.com/ankitects/anki/issues/3616 ; https://docs.ankiweb.net/deck-options.html
DOK 1 - Facts:
- FSRS integrated since 23.10 ("no longer need custom scheduling"); built-in Image Occlusion notetype; .apkg imports can exclude scheduling. Plan: FSRS default for first-time installs. FSRS global-only; default DR 90%; ">97% overwhelming"; fewer reviews for equal retention; experimental FSRS short-term scheduling (empty learning steps). Requires 23.10 / AnkiMobile 23.10 / AnkiDroid 2.17+ (parity constraint).

### AnkiDroid 2.20→2.22; AnkiHub AI features; FSRS history
Stance: frontier — [release-note/vendor/public-post]; Link: https://docs.ankidroid.org/changelog.html ; https://www.ankihub.net/ ; https://community.ankihub.net/t/team-ankihub-updates-april-2026/595532 ; https://www.lesswrong.com/posts/G7fpGCi8r7nCKXsQk/the-history-of-fsrs-for-anki
DOK 1 - Facts:
- AnkiDroid 2.20 (Dec 2024): Anki 24.11 + FSRS 5.0, FSRS Simulator, Easy Days, load balancing, forgetting-curve card info, sort by descending retrievability. 2.21 (Jul 2025): Card Browser perf + FSRS columns; 2.22 with Anki 25.07/FSRS6 imminent. New whiteboard/handwriting overhaul (stylus, persistence) — defaults MENU_ONLY.
- AnkiHub markets AI: "Smart Search" (videos/notes/PDF→cards), "AnkiHub Chatbot," weekly deck updates; April 2026 switched Smart Search reader to Mistral OCR. Reception mixed (Smart Search "couldn't find any flashcards"; rebuilding; removing the slider).
- Jarrett Ye (L-M-Sherlock, MaiMemo) = FSRS creator; publicly says "FSRS-6 is coming," recency-weighting cut error ~4.5%; wrote a Medium post endorsing LLM card generation. Third-party: FSRS-6 trained ~700M reviews; "FSRS-7 (2026): fractional intervals" [emerging].

## E. Transfer science MCAT tutors lean on (handoff to foundations/advocate)
Stance: frontier — [peer-reviewed/practitioner]; Link: https://sc-pan.github.io/pdf/PR_2018W.pdf ; https://www.retrievalpractice.org/ ; https://pdf.poojaagarwal.com/Agarwal_2018_JEdPsych.pdf
DOK 1 - Facts:
- Pan & Rickard (via retrievalpractice transfer guide): testing→transfer d=0.40, strongest "to application and inference questions, to medical diagnoses"; weakest "to rearranged stimulus-response items" (swapping front/back transfers poorly); moderators response congruency + elaborated retrieval; intercept ~0 with none present.
- Agarwal 2018: "higher order learning can be enhanced directly by higher order retrieval practice"; a match between quiz and test question type (transfer-appropriate processing) beats a mismatch → to perform on application items you must PRACTICE application items.
- The Learning Scientists: flashcards work only if "actually trying to retrieve, rather than just flipping the card."

### "Anki builds recognition, not reasoning" critiques (2026 practitioner)
Stance: frontier — [practitioner-opinion/self-reported]; Link: https://studytoolguide.com/study-tools/anki-medical-students-review-2026 ; https://medboardeducation.com/anki-step-2-ck... ; https://fluera.dev/blog/spaced-repetition-medical-school/ ; https://www.yousmle.com/anking/
DOK 1 - Facts:
- StudyToolGuide 2026: "The single study that examined USMLE Step 2 CK found no significant advantage for Anki users" [citation-gate FIX: primary study = Wothe et al., 252.5 vs 247.0, p=0.440, not an independent predictor]; "Avoid cloze-deletion cards that simply hide one word in a long sentence — they encourage recognition rather than recall." MedBoardEducation: "you cannot drill clinical reasoning with flashcards." Fluera: SRS "is not the tool for … testing integration across topics." Yousmle: "Flashcards don't necessarily help you with applying it." r/medicalschoolanki >175k members; AnKing free deck downloaded 200k+.

## Summary (frontier, one-line)
1. #1 application tactic = mine every missed UWorld/AAMC question into a small atomic reasoning-gap card (not a screenshot).
2. Jack Westin publishes a passage-performance card template ("explain + how the MCAT could test it in a passage").
3. Dominant workflow = AnKing "understand first via video/QBank, then unsuspend by tag" (all 35k suspended).
4. Practitioners prescribe why/how/predict/mini-vignette cards to convert definition→application.
5. UWorld-QID tagging (AnkiHub) maps wrong-answer IDs to cards.
6. Mr. Pankow P/S (2,254) = canonical KA-sheet→cloze pattern by AAMC categories.
7. Image occlusion standard for anatomy/pathways ("Hide All, Reveal One").
8. "Deadline/exam-date scheduling" = most-requested missing feature, NO native support.
9. NO native topic interleaving toggle; users split; 2025 third-party script fills the gap.
10. True Retention + richer stats only in FSRS Helper (not native Stats window).
11. Consensus: Anki is WRONG for CARS; use Jack Westin daily passages.
12. A CARS feature must deliver passages + track reasoning/error patterns, not content.
13. FSRS integrated since 23.10, planned default; fewer reviews for equal retention.
14. Image Occlusion built-in since 23.10.
15. AnkiDroid 2.20→2.22 shipped FSRS 5→6 + whiteboard/handwriting (closing mobile parity).
16. AnkiHub ships AI (Smart Search/chatbot/Mistral OCR) but reception rocky / rebuilding.
17. FSRS author publicly endorses LLM card-gen; announced FSRS-6/-7.
18. Transfer science: practice application-type retrieval to transfer to application (Pan d=0.40 strongest to application; Agarwal transfer-appropriate processing).
19. 2026 reviews: Anki builds recognition; no significant Step 2 CK advantage; one-word cloze "encourages recognition."
20. Community: r/medicalschoolanki >175k; AnKing deck 200k+ downloads.

## Experts (frontier)
The AnKing (Nick Flint et al.) https://www.theanking.com/med-student ; Jarrett Ye L-M-Sherlock https://github.com/l-m-sherlock ; glutanimate https://github.com/glutanimate ; AnkiDroid team / David Allison https://docs.ankidroid.org/changelog.html ; Damien Elmes https://github.com/ankitects/anki ; Jack Westin https://jackwestin.com/ ; MileDown/JackSparrow2048/Mr. Pankow (deck creators); The Learning Scientists (Weinstein & Sumeracki) https://www.learningscientists.org/ ; Pooja Agarwal https://www.retrievalpractice.org/ ; Steven C. Pan https://sc-pan.github.io/.

## Flags (frontier)
- Vendor/SEO bias: StudyCards AI, Oboeru, MindoMax, MCAT Study Planner, Jack Westin pages are content-marketing for paid products; technique facts corroborate across sources but treat product/"X% retention" claims as [vendor-claim].
- Almost all "high scorers do X" = [self-reported]/[practitioner-opinion], not controlled; only the transfer science (Pan 2019, Agarwal 2018) + the cited Step-2-CK null are peer-reviewed (and that null is observational/single-study).
- "Anki = recognition not application" sources mutually cite the SAME single Step-2-CK study + Reddit folklore → correlated, not independent confirmation.
- FSRS-7 "fractional intervals 2026" from a third-party blog [emerging] — verify vs open-spaced-repetition repo; solid current state = FSRS-6 in Anki 25.07 / AnkiDroid 2.22.

## CHILD BRAINLIFT CANDIDATE (frontier)
- Topic: Can spaced-repetition flashcard retrieval actually be engineered to build APPLICATION/transfer (higher-order MCAT reasoning), or is transfer fundamentally outside a card-based system? Big (transfer literature + practitioner design space), genuinely contested (Pan d=0.40 with moderators vs "you cannot drill clinical reasoning with flashcards" + Step-2-CK null), load-bearing (the whole fork's premise — if transfer is card-achievable the SPOVs point to specific features; if not, value collapses to "better recognition tooling + QBank handoff").
- Orchestrator note: this IS the parent run's core question (can features push Anki past recognition toward application) → resolve inline.
