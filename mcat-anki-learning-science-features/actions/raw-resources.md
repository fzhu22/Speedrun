# Raw action-research — Resources lane (tools / vendors / costs, as-of 2026-06)

### Anki source + architecture (Ankitects)
Lane: resources; Link: https://github.com/ankitects/anki/blob/main/LICENSE ; .../docs/architecture.md
- Desktop source AGPL-3.0-or-later; software cost $0, but distributing a fork triggers AGPL source-sharing.
- Stack: Rust `rslib` / Python `pylib` / PyQt `aqt` / Svelte-TS `ts/` / Protobuf. Build needs Rustup + N2/Ninja + `just`.
- Serves A1 (desktop prepare in Rust/Python), A8, A9 (analytics over collection/review logs).

### fsrs-rs scheduler crate (Open Spaced Repetition)
Lane: resources; Link: https://crates.io/crates/fsrs ; https://github.com/open-spaced-repetition/fsrs-rs
- `fsrs` v6.6.1 (2026-06-09), BSD-3-Clause, $0; provides FSRS optimize/schedule/simulate → use for A8 DR-ramp simulation, don't reimplement FSRS.

### Sync server / AnkiWeb constraint (Ankitects)
Lane: resources; Link: https://docs.ankiweb.net/sync-server.html ; https://forums.ankiweb.net/t/.../21350
- Self-hosted sync exists (bundled or standalone Python/Rust); third-party sync "not recommended" (protocol changes break compat). **AnkiWeb has no public write/API; new third-party clients generally cannot be approved → do NOT budget AnkiWeb as the fork backend.** Budget self-hosted sync / APKG import-export / explicit Ankitects permission.

### Self-hosted sync hosting (DigitalOcean/Hetzner)
Lane: resources; Link: https://www.digitalocean.com/pricing/droplets ; https://www.hetzner.com/cloud
- DO Droplet 1GB/1vCPU/25GB/1TB = $6/mo; 2GB = $12/mo; snapshots $0.06/GB/mo. Hetzner ~€4-7/mo. A1 estimate: hobby sync $6-15/mo; production w/ backups/monitoring/staging ~$30-100/mo+ before staff.

### AnkiConnect (FooSoft)
Lane: resources; Link: https://git.sr.ht/~foosoft/anki-connect
- GPLv3 add-on, local HTTP API on :8765; create/query/modify local Anki data. Good for A1/A2 desktop ingestion prototypes; NOT a mobile/AnkiWeb API.

### Mobile distribution + copyleft risk (Apple/Google/FSF)
Lane: resources; Link: https://developer.apple.com/support/enrollment/ ; https://support.google.com/googleplay/.../6112435 ; https://www.fsf.org/blogs/licensing/more-about-the-app-store-gpl-enforcement
- Apple Developer $99/yr; TestFlight up to 10,000 external testers. Google Play $25 one-time; new personal accounts need a 12-tester/14-day closed test. **FSF: GPL/AGPL conflicts with App Store terms** → iOS fork needs legal review / alt distribution / dual-license. (HARD constraint for A1 iOS.)

### PyQt6 licensing (Riverbank)
Lane: resources; Link: https://www.riverbankcomputing.com/commercial/buy
- PyQt commercial $670/dev/yr — only needed if going proprietary (which AGPL Anki blocks anyway). Staying GPL/AGPL-compatible → $0.

### OpenAI API + embeddings
Lane: resources; Link: https://developers.openai.com/api/docs/models/gpt-4.1 ; .../text-embedding-3-large
- GPT-4.1 $2/1M in, $8/1M out; 4.1-mini $0.40/$1.60; 4.1-nano ~$0.10/$0.40. Embeddings: 3-small $0.02/1M, 3-large $0.13/1M.
- Estimate A10: one severe-test (2k in + 800 out) ≈ $0.0021 on 4.1-mini; 5,000/mo ≈ $10.40. Embedding 10k cards (3M tok) ≈ $0.06 (3-small).

### Google Gemini API + embeddings
Lane: resources; Link: https://ai.google.dev/gemini-api/docs/pricing
- Gemini 2.5 Flash $0.30/1M in, $2.50/1M out; 2.5 Pro $1.25/$10 (≤200k). Gemini Embedding 2 (Vertex) $0.20/1M. A10 est: 2k+800 ≈ $0.0026 Flash; 5,000/mo ≈ $13.

### Anthropic Claude API
Lane: resources; Link: https://www.anthropic.com/pricing
- Haiku ~$1/$5; Sonnet ~$3/$15; Opus ~$5/$25 (per 1M in/out). Batch + prompt caching cut repeated-key prompts. A10 est: 2k+800 ≈ $0.006 Haiku; 5,000/mo ≈ $30.

### Mistral OCR 4 + alternatives (Mistral/Google/AWS)
Lane: resources; Link: https://mistral.ai/news/ocr-4/ ; https://cloud.google.com/document-ai/pricing ; https://aws.amazon.com/textract/pricing/
- Mistral OCR 4: $4/1k pages ($2 batch); returns markdown + bounding boxes + confidence. Google Doc AI OCR $1.50/1k (then $0.60); AWS Textract $1.50/1k (then $0.60; 1k free/mo 3 mo). A2 ingest 300 pages ≈ $0.45-1.20. Google/AWS cheaper for plain text; Mistral worth it for layout/markdown.

### AAMC official prep / item bank (AAMC)
Lane: resources; Link: https://store.aamc.org/compare-all-mcat-official-prep-products ; https://www.aamc.org/services/mcat-prep-hub-terms-conditions
- Section Bank $45 ea; Practice Exams 2-6 $35 ea; Q-Pack bundle $76.50; Online-Only bundle $323.70/yr. **Terms PROHIBIT copying, derivatives, AI/LLM modeling, browser plugins interacting with Prep Hub, commercial exploitation.** AAMC content = student-owned reference for provenance ONLY, not ingestible into the item bank.

### UWorld MCAT + UAsk (UWorld)
Lane: resources; Link: https://gradschool.uworld.com/mcat/uask/ ; https://www.uworld.com/terms_conditions.aspx
- QBank from $339; Core $599; Comprehensive $1,199. **Terms PROHIBIT copying/screenshots/capture/upload to other apps.** Fork supports user-entered QID/provenance + student notes, NOT UWorld extraction (matches A2 anti-pattern: student-authored only).

### Jack Westin CARS / QBank (Jack Westin)
Lane: resources; Link: https://jackwestin.com/support/questions/what-are-your-daily-cars-passages-like-are-they-free
- Daily CARS passages free + original; 365 daily passages; all practice free for public use but copyrighted. JW+ ~$29.99/mo. A11: treat as integration/partner/redirect, NOT content to ingest wholesale.

### MCAT tutor / authoring labor (Wyzant/TestPrepPal/TutorOcean)
Lane: resources; Link: https://www.wyzant.com/MCAT_tutors.aspx ; https://testpreppal.com/mcat/tutoring
- Wyzant MCAT tutors avg ~$40-75/hr (range $20-$645). Senior/520+/physician reviewers ~$150-250+/hr. **A4/A6 item authoring is the largest non-software cost:** 100 high-quality confusable-set drills w/ distractor rationales @ 0.5-1.5 hr each ≈ $4,000-18,750 depending on reviewer mix.

### Psychometrics libraries (open source)
Lane: resources; Link: https://github.com/eribean/girth ; https://github.com/nd-ball/py-irt/
- `girth` (MIT, IRT); `py-irt` (MIT, Bayesian 1PL/2PL/4PL); `psychometrics` (CTT incl. point-biserial). A9 = $0 library cost; cost is implementation/validation.

### PostHog analytics / experiment harness (PostHog)
Lane: resources; Link: https://posthog.com/pricing
- Free tier: 1M analytics events/mo, 1M feature-flag requests/mo, 5,000 session recordings, experiments/flags. Beyond: ~$0.00005/event. A9/A10 logging + A/B gates + crutch kill-switch at $0/mo for early pilots.

### Comparable products (anchors): AnkiHub / RemNote / Memm / UWorld
Lane: resources; Link: https://community.ankihub.net/t/.../343224 ; https://www.remnote.com/mcat_landing_page ; https://memm.io/
- AnkiHub Premium $10/mo or $110/yr (Smart Search + AI chatbot). RemNote MCAT $20/mo early-bird ($10 for Pro). Memm $125/1mo, $219/3mo, $339/6mo. UWorld QBank $339+. **Build-vs-buy anchor: curated MCAT content + SRS is already $10-125/mo → the fork's differentiation MUST be the learning-science feature layer, not "MCAT flashcards."**

## Load-bearing cost facts (resources)
- Core fork software $0 (AGPL mandatory); fsrs-rs $0 (BSD-3).
- Prototype sync $6-15/mo; production self-hosted $30-100/mo+. **AnkiWeb NOT a dependable fork backend.**
- iOS $99/yr (+ AGPL/App-Store legal review); Android $25 one-time.
- LLM severe-test gen ~$10-50/mo for 5,000/mo on cheap-mid models; embeddings cents; OCR $0.45-1.20/300 pages.
- AAMC/UWorld content NOT ingestible (terms) → A2 student-authored only; A11 Jack Westin = integrate not ingest.
- **Human MCAT authoring/review is the real A4/A6/A10 cost: first library ~$4k-25k.**
- A9 analytics $0 (girth/py-irt + PostHog free tier).

## Rough build cost picture
- **Hackathon free-tier stack:** Anki source + fsrs-rs + local SQLite/log exports + AnkiConnect + cheap LLM + OpenAI embeddings + PostHog free + no store release → under $50-100 cash for a short pilot (excl. labor/content).
- **Production-ish pilot:** self-hosted sync + backups + mobile accounts + PostHog/OCR/LLM budget + paid MCAT review → software/cloud ~$100-500/mo, but curated content/review + legal/licensing dominate ($5k-25k human authoring/QA/compliance before scale).
