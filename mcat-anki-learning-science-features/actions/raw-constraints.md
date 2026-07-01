# Raw action-research — Constraints lane (legal/compliance gates, dependencies, lead-times, risks)

## HARD BLOCKERS
### AGPL fork cannot ship its OWN engine-bearing iOS app on the App Store
Lane: constraints; Link: https://github.com/ankitects/anki/blob/main/LICENSE ; https://www.fsf.org/blogs/licensing/more-about-the-app-store-gpl-enforcement ; https://developer.pidgin.im/wiki/WhyNoiOSVersion ; https://www.gnu.org/licenses/gpl-faq.html#GPLIncompatibleLibs
- Anki is **AGPL-3.0-or-later held by MANY contributors** (+ BSD-3 parts). Apple's Usage Rules impose "further restrictions" (5-device limit, accept Apple ToS) that GPL/AGPL §7 forbids → AGPL code on the App Store is a license violation; Apple removes on complaint (**VLC & GNU Go were pulled**).
- The §7 App-Store exception can ONLY be granted by the copyright holder; a fork is a derivative, so **every** Anki contributor would have to agree — impossible. ⇒ **The fork cannot ship its own iOS app bundling the Anki engine.** Clean iOS paths: (a) run the A1 review tier as **card-template JS inside the existing proprietary AnkiMobile** (user already installed it), or (b) a 100%-own thin client to a server (no AGPL engine on-device). **(a) makes the two-tier architecture a LEGAL workaround, not just technical — reinforces Validated SPOV 4.** AnkiMobile is dae's proprietary paid closed app (no add-ons) → path (a) depends on a third party + AnkiWeb sync. (gates A1 iOS)

### AnkiWeb sync ToS forbids third-party clients without permission
Lane: constraints; Link: https://ankiweb.net/account/terms ; https://docs.ankiweb.net/sync-server.html
- ToS: AnkiWeb "may not be accessed from other [than approved] clients without first obtaining permission." dae (forum) softened: "unmodified syncing code, not causing problems… should be fine" — but the safe path is **written permission OR self-host `anki-sync-server`** (Rust/Python, official). Self-host is "targeted at individual/family use," **HTTP-only (add your own TLS), no REST/external-DB PRs accepted, 100 MB default cap** → multi-tenant auth/TLS/scaling/uptime are the team's burden. (gates A1 sync)

### Content IP — AAMC / UWorld / Jack Westin non-ingestible
Lane: constraints; Link: https://students-residents.aamc.org/media/8351/download ; https://www.uworld.com/terms_conditions.aspx ; https://jackwestin.com/terms
- **AAMC** owns the MCAT (registered copyrights + trade secrets); examinees have "no license to copy/adapt/use any part," must keep content confidential, and "not… use confidential information about the MCAT… during preparation" → a feature ingesting "the question you just saw" would induce a ToS breach + civil/criminal exposure. Only AAMC's public "What's on the MCAT" outline is a safe topic-level reference. ⇒ **A2/A4/A11 must NEVER ingest real MCAT items.**
- **UWorld** ToS forbids copy/screenshot/capture/upload to other apps (personal, non-commercial); actively auto-closes sessions on screenshot. ⇒ **A2/A6 capture the student's OWN write-up of the miss + principle, never UWorld stems.**
- **Jack Westin** original passages copyrighted, no reproduction elsewhere; it re-hosts free Khan Academy/AAMC CARS passages. ⇒ **A11 = separate passage module from free AAMC/Khan content OR a licensed/linked Jack Westin partnership — never scraped passages, never a "CARS content deck."**

## PRIVACY / SECURITY
### COPPA N/A; GDPR binds at first EU user; CCPA likely N/A at small scale
Lane: constraints; Link: https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions ; https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1798.140
- **COPPA** applies only <13 → MCAT examinees are adults → N/A. **CCPA/CPRA** binds only a business >$25M revenue / ≥100k CA consumers / ≥50% revenue from data sale → small team below thresholds at launch. **GDPR has NO size threshold** → one EU student storing review logs/confidence/LLM data triggers lawful-basis + privacy notice + access/erasure + a DPA with each sub-processor (OpenAI) + breach reporting; fines up to €20M/4%. Review logs + confidence + student work to an LLM = personal data → minimization + retention limits + sub-processor disclosure. (gates A7/A9/A10 if any EU users; mitigate by geo-limiting at launch or building the DPA chain). FERPA out-of-scope for direct-to-adult-consumer [verify if institutional channel appears].

### OpenAI API data terms
Lane: constraints; Link: https://developers.openai.com/api/docs/guides/your-data ; https://openai.com/business-data/
- API data **not used for training by default** (since 2023-03-01) BUT abuse-monitoring **retains prompts/responses ~30 days**; **Zero Data Retention is enterprise-only/approval-gated** → small team likely can't get ZDR at launch → must disclose 30-day retention + sign an **OpenAI DPA** (team=controller, OpenAI=processor) before covered student data flows. (A10 prerequisite)

### PoisonedRAG injection (USENIX Security 2025)
Lane: constraints; Link: https://www.usenix.org/system/files/usenixsecurity25-zou-poisonedrag.pdf
- **~5 malicious texts → ~90% attack-success** making an LLM emit an attacker-chosen answer; evaluated defenses insufficient; corrupts the data source (bypasses prompt-only defenses). ⇒ if A10 ingests user/source docs into a retrieval store, treat as untrusted: provenance, isolation, output validation against the **human-authored key** (which SPOV 9 already mandates), don't let retrieved text issue instructions. (A10 security)

## SEQUENCING / TECHNICAL DEPENDENCIES
### Substrate limits (code-verified, carried from brainlift)
Lane: constraints; Link: https://github.com/ankitects/anki (scheduler.proto, rslib) ; https://faqs.ankiweb.net/the-2021-scheduler.html ; https://forums.ankiweb.net/t/.../49792
- `customData` ≤100 bytes / 8-byte keys → A3 flags + A7 confidence/false-model + A8 per-card DR target can't exceed ~100 B/card → larger state in companion store/tags/desktop-prepared artifact.
- Custom scheduling = global JS, sees only `{deck_name, seed}`, runs at answer-time, re-weights one card's interval, CANNOT re-rank the queue → **no on-device semantic re-ranking** (anti-pattern); A3/A4 must be desktop-prepared. v3 not monkey-patchable; AnkiMobile no add-ons; AnkiDroid no Python (JS only). ⇒ **A1 must exist before A3/A5/A7/A8/A10 review tiers.** Forum (L-M-Sherlock 2024): DR "unaccessible to custom scheduling… only via an add-on."

### Per-card-DR write is unmerged (A8 dependency)
Lane: constraints; Link: https://github.com/ankitects/anki/pull/4880 ; https://github.com/ankitects/anki/pull/4194
- **PR #4880 (merged 2026-06-08) exposes card decay/DR READ to custom-scheduling JS.** Per-deck DR shipped via PR #4194 (25.09). **Native per-card-DR WRITE is only a community draft on a personal fork (jhhr), NOT in mainline** → **A8 must use the deck-bucket / card-field / ≤100-B customData workaround + the exposed read surface** (per SPOV 11); don't block on upstream.

### Android is the open path
Lane: constraints; Link: https://github.com/ankidroid/Anki-Android/wiki/Licences ; https://f-droid.org/docs/FAQ_-_App_Developers/
- **Google Play permits GPL/AGPL** (AnkiDroid ships GPL-3.0 app + AGPL backend) → the fork CAN ship its own Android app (publish modified source). But Google compelled scoped-storage changes (nearly delisted AnkiDroid) → budget data-safety/permissions churn. AnkiDroid = Kotlin + JNI bridge to Rust `rslib` (rebuild/maintain, not just port Python). F-Droid alt path requires all-FOSS deps (a bundled proprietary LLM SDK blocks main-repo inclusion).

## COST / TIME RISKS
- Self-hosted sync at student scale = team's burden (individual/family server, HTTP-only, DIY scaling).
- Fork maintenance is continuous: Anki frequent releases (25.07→25.09 = 85 commits/128 files), FSRS-6→7 churn (21→35 params) → track `fsrs-rs` + two upstreams (desktop + AnkiDroid JNI). Reinforces "don't reimplement FSRS."
- Apple review 1–3 weeks for new apps in 2025-26 (AI scrutiny) — mostly moot given Blocker #1. Apple $99/yr + 15-30%; Google $25 one-time + 15-30%.
- **AGPL §13 network-use:** any modified-engine server (sync/prepare/LLM gateway) must offer source to remote users → keep proprietary glue behind a clean non-AGPL API boundary [needs legal review].
- **Anki name = registered trademark; logo = AGPL** → fork needs its own name + mark.

## Summary — flagged
HARD BLOCKERS: (1) no own iOS app bundling the engine → review tier = template JS in AnkiMobile; (2) AnkiWeb sync needs permission/self-host; (3) AAMC content non-ingestible; (4) UWorld content non-ingestible; (5) Jack Westin passages non-scrapeable.
SEQUENCING: (6) A1 before A3/A4/A5/A7/A8/A10; (7) customData ≤100 B caps synced per-card state; (8) per-card-DR write unmerged → A8 workaround; (9) GDPR + (10) OpenAI DPA/retention before covered data flows to A10; (11) store accounts.
COST/TIME: (12) self-host sync ops; (13) continuous fork maintenance; (14) PoisonedRAG A10 security; (16) AGPL §13 boundary; (17) Google can compel Android changes; (18) own name/logo.
[verify]: AnkiMobile closed-source primary license; FERPA if institutional channel; current Khan/AAMC CARS-passage reuse license for A11.
