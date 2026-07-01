// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Speedrun readiness dashboard: the shared, read-only data behind the desktop
//! and AnkiDroid dashboards.
//!
//! This is the Rust port of the DATA assembly in
//! `qt/aqt/speedrun/dashboard.py`. It ties together the per-topic mastery query,
//! the embedded AAMC outline, coverage roll-up, prerequisite-aware planning, and
//! the per-family fading rung, and returns them as one message. The HTML/UI is
//! built separately (TypeScript); nothing here renders.
//!
//! Honesty rules enforced here (the project's grading depends on them):
//! - The three scores are never blended into one number. Memory is per-section
//!   average recall (abstains when no card has been reviewed), Performance always
//!   abstains for now (no exam-style items yet), and Readiness abstains unless
//!   both the coverage give-up line and the minimum review count are met.
//! - This is a read-only query: it opens no write transaction, records no undo
//!   step, and is deterministic (proven by unit tests).

use std::collections::HashMap;

use anki_proto::speedrun::speedrun_dashboard_response::PlanItem;
use anki_proto::speedrun::speedrun_dashboard_response::SectionRow;
use anki_proto::speedrun::SpeedrunDashboardRequest;
use anki_proto::speedrun::SpeedrunDashboardResponse;
use anki_proto::stats::TopicMasteryRequest;

use super::coverage;
use super::outline;
use super::planning;
use crate::prelude::*;

/// Applied when the request leaves `tag_prefix` empty.
const DEFAULT_TAG_PREFIX: &str = "MCAT";
/// Applied when the request leaves `mastered_retrievability` at 0.
const DEFAULT_MASTERED_RETRIEVABILITY: f32 = 0.9;
/// Applied when the request leaves `give_up_line` at 0.
const DEFAULT_GIVE_UP_LINE: f32 = 0.5;
/// Applied when the request leaves `min_reviews_for_readiness` at 0.
const DEFAULT_MIN_REVIEWS: u32 = 200;
/// How many recommendations the plan surfaces.
const PLAN_LEN: usize = 5;
/// Config key holding the per-family fading state (`family_code -> {"rung": ..}`).
const FADING_CONFIG_KEY: &str = "speedrun_fading";
/// Performance always abstains for now: there are no exam-style items yet.
const PERFORMANCE_ABSTAIN: &str = "insufficient data - no exam-style items yet";

/// The family's current fading rung: the persisted rung from the config map when
/// present, otherwise a conservative estimate from the average recall. Mirrors
/// `fading.current_rung` / `estimate_rung` in the Python.
fn current_rung(fading_cfg: &serde_json::Value, family_code: &str, avg_recall: Option<f32>) -> String {
    if let Some(rung) = fading_cfg
        .get(family_code)
        .and_then(|entry| entry.get("rung"))
        .and_then(|rung| rung.as_str())
    {
        return rung.to_string();
    }
    estimate_rung(avg_recall).to_string()
}

/// Conservative initial rung from average FSRS recall (`None` = no data). Never
/// seeds L0 from recall alone; L0 is only reachable by demonstrated advancement.
fn estimate_rung(avg_recall: Option<f32>) -> &'static str {
    match avg_recall {
        None => "L3",
        Some(r) if r < 0.6 => "L3",
        Some(r) if r < 0.85 => "L2",
        Some(_) => "L1",
    }
}

/// 95% Wilson score interval for a proportion `p` observed over `n` samples,
/// clamped to [0, 1]. This is the memory score's honest range: it is wide when
/// only a few cards back the estimate and tightens as `n` grows, so the
/// dashboard never implies more certainty than the data supports.
fn wilson_interval(p: f32, n: u32) -> (f32, f32) {
    const Z: f32 = 1.96; // ~95% two-sided
    let n = n as f32;
    let z2 = Z * Z;
    let denom = 1.0 + z2 / n;
    let center = (p + z2 / (2.0 * n)) / denom;
    let margin = (Z / denom) * ((p * (1.0 - p) / n) + (z2 / (4.0 * n * n))).sqrt();
    ((center - margin).max(0.0), (center + margin).min(1.0))
}

impl Collection {
    /// Read-only data for the Speedrun readiness dashboard. See the module docs
    /// for the honesty rules this upholds.
    pub fn speedrun_dashboard(
        &mut self,
        input: SpeedrunDashboardRequest,
    ) -> Result<SpeedrunDashboardResponse> {
        // Apply defaults for any field left at 0/empty.
        let tag_prefix = if input.tag_prefix.trim().is_empty() {
            DEFAULT_TAG_PREFIX.to_string()
        } else {
            input.tag_prefix.clone()
        };
        let mastered_retrievability = if input.mastered_retrievability > 0.0 {
            input.mastered_retrievability
        } else {
            DEFAULT_MASTERED_RETRIEVABILITY
        };
        let give_up_line = if input.give_up_line > 0.0 {
            input.give_up_line
        } else {
            DEFAULT_GIVE_UP_LINE
        };
        let min_reviews = if input.min_reviews_for_readiness > 0 {
            input.min_reviews_for_readiness
        } else {
            DEFAULT_MIN_REVIEWS
        };

        // Reuse the per-topic mastery query for total cards + average recall.
        let mastery = self.topic_mastery(TopicMasteryRequest {
            search: String::new(),
            tag_prefix,
            mastered_retrievability,
            include_descendants: false,
            min_cards_for_average: 1,
        })?;

        // Map tags -> content categories, aggregating a reviewed-card-weighted
        // mean recall per content category (a category may gather several tags).
        let mut cards_by_cc: HashMap<String, u32> = HashMap::new();
        let mut recall_weighted_sum: HashMap<String, f64> = HashMap::new();
        let mut reviewed_by_cc: HashMap<String, u32> = HashMap::new();
        for topic in &mastery.topics {
            let Some(cc) = outline::cc_from_tag(&topic.tag) else {
                continue;
            };
            *cards_by_cc.entry(cc.clone()).or_default() += topic.total_cards;
            if let Some(avg) = topic.average_recall {
                *recall_weighted_sum.entry(cc.clone()).or_default() +=
                    avg as f64 * topic.reviewed_cards as f64;
                *reviewed_by_cc.entry(cc).or_default() += topic.reviewed_cards;
            }
        }
        let recall_by_cc: HashMap<String, f32> = reviewed_by_cc
            .iter()
            .filter(|(_, &n)| n > 0)
            .map(|(cc, &n)| (cc.clone(), (recall_weighted_sum[cc] / n as f64) as f32))
            .collect();

        // Coverage of the content-category leaves.
        let cov = coverage::compute_coverage(&cards_by_cc);

        // Weakness (1 - recall, or 1.0 when unknown) + illustrative weights, then
        // the prerequisite-constrained plan.
        let mut weakness: HashMap<String, f32> = HashMap::new();
        let mut weights: HashMap<String, f32> = HashMap::new();
        for section in outline::SECTIONS {
            for category in section.categories {
                let cc = outline::cc_id(category.code);
                let w = recall_by_cc.get(&cc).map(|r| 1.0 - r).unwrap_or(1.0);
                weakness.insert(cc.clone(), w);
                weights.insert(cc.clone(), planning::illustrative_weight(&cc));
            }
        }
        let plan = planning::next_best_topic(
            &weakness,
            &weights,
            planning::PREREQUISITES,
            planning::PREREQ_THRESHOLD,
            PLAN_LEN,
        );

        // Per-family fading state (read-only).
        let fading_cfg = self
            .get_config_optional::<serde_json::Value, _>(FADING_CONFIG_KEY)
            .unwrap_or(serde_json::Value::Null);

        let plan: Vec<PlanItem> = plan
            .into_iter()
            .map(|rec| {
                let code = rec
                    .cc_id
                    .strip_prefix("cc:")
                    .unwrap_or(rec.cc_id.as_str())
                    .to_string();
                let title = outline::title_for_code(&code)
                    .map(str::to_string)
                    .unwrap_or_else(|| code.clone());
                let rung = current_rung(&fading_cfg, &code, recall_by_cc.get(&rec.cc_id).copied());
                PlanItem {
                    code,
                    title,
                    rung,
                    reason: rec.reason,
                    score: rec.score,
                    prerequisite: rec.prerequisite,
                }
            })
            .collect();

        // Per-section rows: coverage from `cov`, memory as the mean of per-cc
        // recall over the section's categories that have data (abstain if none).
        // `cov.per_section` is in outline order over the non-empty sections, so it
        // zips cleanly with the same filtered outline sections.
        let sections: Vec<SectionRow> = outline::SECTIONS
            .iter()
            .filter(|s| !s.categories.is_empty())
            .zip(cov.per_section.iter())
            .map(|(section, sc)| {
                debug_assert_eq!(section.id, sc.section_id, "section rows must stay aligned");
                let recalls: Vec<f32> = section
                    .categories
                    .iter()
                    .filter_map(|c| recall_by_cc.get(&outline::cc_id(c.code)).copied())
                    .collect();
                // Cards with a defined recall backing this section (the interval's n).
                let reviewed_cards: u32 = section
                    .categories
                    .iter()
                    .filter_map(|c| reviewed_by_cc.get(&outline::cc_id(c.code)).copied())
                    .sum();
                let memory = if recalls.is_empty() {
                    None
                } else {
                    Some(recalls.iter().sum::<f32>() / recalls.len() as f32)
                };
                // Honest range around the point estimate; abstains exactly when
                // memory does (no reviewed cards -> no interval).
                let (memory_low, memory_high) = match memory {
                    Some(p) if reviewed_cards > 0 => {
                        let (lo, hi) = wilson_interval(p, reviewed_cards);
                        (Some(lo), Some(hi))
                    }
                    _ => (None, None),
                };
                SectionRow {
                    section: sc.title.to_string(),
                    abbrev: sc.abbrev.to_string(),
                    coverage: sc.fraction,
                    memory,
                    memory_low,
                    memory_high,
                    reviewed_cards,
                }
            })
            .collect();

        // Give-up gate: readiness needs both enough coverage and enough reviews.
        let total_reviews: u32 =
            self.storage
                .db
                .query_row("SELECT count() FROM revlog", [], |row| row.get(0))?;
        let coverage_ok = cov.overall >= give_up_line;
        let reviews_ok = total_reviews >= min_reviews;
        let readiness_allowed = coverage_ok && reviews_ok;
        let readiness_status = if readiness_allowed {
            "allowed".to_string()
        } else {
            let mut reasons = Vec::new();
            if !coverage_ok {
                reasons.push(format!(
                    "coverage {:.0}% < {:.0}%",
                    cov.overall * 100.0,
                    give_up_line * 100.0
                ));
            }
            if !reviews_ok {
                reasons.push(format!("only {total_reviews} of {min_reviews} reviews"));
            }
            format!("ABSTAIN - {}", reasons.join("; "))
        };

        Ok(SpeedrunDashboardResponse {
            overall_coverage: cov.overall,
            covered_leaves: cov.covered_leaves,
            total_leaves: cov.total_leaves,
            sections,
            readiness_allowed,
            give_up_line,
            total_reviews,
            performance_status: PERFORMANCE_ABSTAIN.to_string(),
            readiness_status,
            plan,
        })
    }
}

#[cfg(test)]
mod test {
    use anki_proto::speedrun::SpeedrunDashboardRequest;

    use crate::card::CardType;
    use crate::card::FsrsMemoryState;
    use crate::prelude::*;
    use crate::revlog::RevlogEntry;
    use crate::speedrun::planning;

    fn req() -> SpeedrunDashboardRequest {
        SpeedrunDashboardRequest {
            tag_prefix: String::new(),
            mastered_retrievability: 0.0,
            give_up_line: 0.0,
            min_reviews_for_readiness: 0,
        }
    }

    fn add_card_with_tags(col: &mut Collection, tags: &[&str]) -> CardId {
        let nt = col.basic_notetype();
        let mut note = nt.new_note();
        note.tags = tags.iter().map(|t| t.to_string()).collect();
        col.add_note(&mut note, DeckId(1)).unwrap();
        col.storage.all_cards_of_note(note.id).unwrap()[0].id
    }

    /// Turn a card into a Review card with the given FSRS stability, last
    /// reviewed `secs_since_review` seconds ago (mirrors the mastery.rs helper).
    fn set_memory(col: &mut Collection, cid: CardId, stability: f32, secs_since_review: i64) {
        let mut review_time = col.timing_today().unwrap().now;
        review_time.0 -= secs_since_review;
        let mut card = col.storage.get_card(cid).unwrap().unwrap();
        card.ctype = CardType::Review;
        card.memory_state = Some(FsrsMemoryState {
            stability,
            difficulty: 5.0,
        });
        card.decay = None;
        card.last_review_time = Some(review_time);
        col.storage.update_card(&card).unwrap();
    }

    /// Insert `n` graded review-log rows so `total_reviews` can be controlled.
    fn add_revlogs(col: &mut Collection, n: usize) {
        for _ in 0..n {
            col.storage
                .add_revlog_entry(&RevlogEntry::default(), true)
                .unwrap();
        }
    }

    /// (a) A card on a finer descendant tag covers its content category, and the
    /// overall/per-section coverage rolls up correctly. CARS has no leaves, so it
    /// is not a coverage row.
    #[test]
    fn coverage_rolls_up_from_descendant_tags() {
        let mut col = Collection::new();
        add_card_with_tags(&mut col, &["MCAT::BioBiochem::1A::AminoAcids"]);
        add_card_with_tags(&mut col, &["MCAT::ChemPhys::5E"]);
        // out-of-scope + untagged cards must not affect coverage
        add_card_with_tags(&mut col, &["Other::Thing"]);
        add_card_with_tags(&mut col, &[]);

        let res = col.speedrun_dashboard(req()).unwrap();

        assert_eq!(res.total_leaves, 31);
        assert_eq!(res.covered_leaves, 2);
        assert!((res.overall_coverage - 2.0 / 31.0).abs() < 1e-6);

        let abbrevs: Vec<&str> = res.sections.iter().map(|s| s.abbrev.as_str()).collect();
        assert_eq!(abbrevs, ["Bio/Biochem", "Chem/Phys", "Psych/Soc"]);

        let bio = res
            .sections
            .iter()
            .find(|s| s.abbrev == "Bio/Biochem")
            .unwrap();
        assert!((bio.coverage - 1.0 / 9.0).abs() < 1e-6);
        let chem = res
            .sections
            .iter()
            .find(|s| s.abbrev == "Chem/Phys")
            .unwrap();
        assert!((chem.coverage - 1.0 / 10.0).abs() < 1e-6);
        let psych = res
            .sections
            .iter()
            .find(|s| s.abbrev == "Psych/Soc")
            .unwrap();
        assert_eq!(psych.coverage, 0.0);
        // nothing reviewed yet -> memory abstains
        assert!(bio.memory.is_none());
    }

    /// (b) Planning surfaces a still-weak prerequisite ahead of its dependent,
    /// and steps aside once the prerequisite is strong enough.
    #[test]
    fn planning_surfaces_weak_prerequisite_before_dependent() {
        // cc:5E is a prerequisite of cc:1D. All-unknown -> both maximally weak.
        let weights: std::collections::HashMap<String, f32> = outline_weights();
        let mut weakness: std::collections::HashMap<String, f32> = std::collections::HashMap::new();
        for cc in weights.keys() {
            weakness.insert(cc.clone(), 1.0);
        }

        let plan = planning::next_best_topic(
            &weakness,
            &weights,
            planning::PREREQUISITES,
            planning::PREREQ_THRESHOLD,
            5,
        );
        // the dependent (1D) is not recommended on its own; its prerequisite is
        let has_dependent = plan.iter().any(|r| r.cc_id == "cc:1D");
        assert!(!has_dependent, "the weak prerequisite must come before its dependent");
        let prereq = plan
            .iter()
            .find(|r| r.cc_id == "cc:5E")
            .expect("prerequisite should be surfaced");
        assert!(prereq.prerequisite);
        assert_eq!(prereq.reason, "prerequisite of cc:1D");

        // Now make the prerequisite strong (weakness below threshold): the
        // dependent is recommended directly and 5E is no longer a prerequisite.
        weakness.insert("cc:5E".to_string(), 0.1);
        let plan = planning::next_best_topic(
            &weakness,
            &weights,
            planning::PREREQUISITES,
            planning::PREREQ_THRESHOLD,
            5,
        );
        let dependent = plan
            .iter()
            .find(|r| r.cc_id == "cc:1D")
            .expect("dependent should now be recommended directly");
        assert!(!dependent.prerequisite);
        assert_eq!(dependent.reason, "high yield x weakness");
        assert!(plan.iter().all(|r| r.reason != "prerequisite of cc:1D"));
    }

    /// (c) The give-up gate: readiness is allowed only when BOTH the coverage
    /// line and the minimum review count are met; otherwise it abstains with an
    /// explicit reason naming what failed.
    #[test]
    fn give_up_gate_requires_coverage_and_reviews() {
        let mut col = Collection::new();
        add_card_with_tags(&mut col, &["MCAT::BioBiochem::1A"]);

        // Default thresholds: coverage << 50% and 0 < 200 reviews -> both fail.
        let res = col.speedrun_dashboard(req()).unwrap();
        assert!(!res.readiness_allowed);
        assert!(res.readiness_status.contains("coverage"));
        assert!(res.readiness_status.contains("reviews"));
        assert_eq!(res.total_reviews, 0);

        add_revlogs(&mut col, 5);

        // Coverage passes (tiny line) but reviews still fail (default 200).
        let mut r = req();
        r.give_up_line = 0.01;
        let res = col.speedrun_dashboard(r).unwrap();
        assert!(!res.readiness_allowed);
        assert!(res.readiness_status.contains("reviews"));
        assert!(!res.readiness_status.contains("coverage"));
        assert_eq!(res.total_reviews, 5);

        // Reviews pass (low bar) but coverage fails (default 50% line).
        let mut r = req();
        r.min_reviews_for_readiness = 5;
        let res = col.speedrun_dashboard(r).unwrap();
        assert!(!res.readiness_allowed);
        assert!(res.readiness_status.contains("coverage"));
        assert!(!res.readiness_status.contains("reviews"));

        // Both pass -> allowed.
        let mut r = req();
        r.give_up_line = 0.01;
        r.min_reviews_for_readiness = 5;
        let res = col.speedrun_dashboard(r).unwrap();
        assert!(res.readiness_allowed);
        assert_eq!(res.readiness_status, "allowed");
    }

    /// (d) The call is read-only (records no undo step) and deterministic.
    #[test]
    fn is_read_only_and_deterministic() {
        let mut col = Collection::new();
        add_card_with_tags(&mut col, &["MCAT::BioBiochem::1A"]);

        let before = col.undo_status().last_step;
        let first = col.speedrun_dashboard(req()).unwrap();
        let after = col.undo_status().last_step;
        assert_eq!(before, after, "speedrun_dashboard must not record an undo step");

        let second = col.speedrun_dashboard(req()).unwrap();
        assert_eq!(first, second, "speedrun_dashboard must be deterministic");
    }

    /// (e) The three scores stay separate: Memory abstains until a card is
    /// reviewed (and is per-section), while Performance always abstains for now.
    #[test]
    fn memory_abstains_and_scores_stay_separate() {
        let mut col = Collection::new();
        let strong = add_card_with_tags(&mut col, &["MCAT::BioBiochem::1A"]);
        add_card_with_tags(&mut col, &["MCAT::ChemPhys::5E"]);

        let res = col.speedrun_dashboard(req()).unwrap();
        for s in &res.sections {
            assert!(s.memory.is_none(), "memory must abstain before any review");
            assert!(
                s.memory_low.is_none() && s.memory_high.is_none(),
                "the range abstains together with memory"
            );
            assert_eq!(s.reviewed_cards, 0);
        }
        assert_eq!(
            res.performance_status,
            "insufficient data - no exam-style items yet"
        );

        // Review the 1A card to a high recall.
        set_memory(&mut col, strong, 10_000.0, 0);
        let res = col.speedrun_dashboard(req()).unwrap();
        let bio = res
            .sections
            .iter()
            .find(|s| s.abbrev == "Bio/Biochem")
            .unwrap();
        let mem = bio.memory.expect("memory present after a review");
        assert!(mem > 0.5, "a freshly-reviewed strong card should read high, got {mem}");
        // The honest range is present, valid, and (with a single card) wide.
        let lo = bio.memory_low.expect("range present with memory");
        let hi = bio.memory_high.expect("range present with memory");
        assert!((0.0..=1.0).contains(&lo) && (0.0..=1.0).contains(&hi) && lo <= hi);
        assert!(lo <= mem, "the lower bound sits at or below the point estimate");
        assert!(hi - lo > 0.1, "one reviewed card should give a wide band, got {lo}..{hi}");
        assert_eq!(bio.reviewed_cards, 1);
        // A section with no reviewed cards keeps abstaining (point and range).
        let chem = res
            .sections
            .iter()
            .find(|s| s.abbrev == "Chem/Phys")
            .unwrap();
        assert!(chem.memory.is_none());
        assert!(chem.memory_low.is_none() && chem.memory_high.is_none());
        assert_eq!(chem.reviewed_cards, 0);
        // Performance remains a separate, still-abstaining field (never blended).
        assert_eq!(
            res.performance_status,
            "insufficient data - no exam-style items yet"
        );
    }

    /// (f) The Wilson band is valid, sits in [0,1], and tightens as more cards
    /// back the estimate - the honesty guarantee behind the memory range.
    #[test]
    fn wilson_interval_narrows_with_more_data() {
        let (lo_small, hi_small) = super::wilson_interval(0.8, 3);
        let (lo_big, hi_big) = super::wilson_interval(0.8, 300);
        for (lo, hi) in [(lo_small, hi_small), (lo_big, hi_big)] {
            assert!((0.0..=1.0).contains(&lo) && (0.0..=1.0).contains(&hi) && lo <= hi);
        }
        assert!(
            (hi_small - lo_small) > (hi_big - lo_big),
            "more reviewed cards must tighten the band"
        );
        assert!(hi_big - lo_big < 0.1, "with lots of data the band hugs the point");
    }

    /// Illustrative weights for every content category, as the dashboard builds.
    fn outline_weights() -> std::collections::HashMap<String, f32> {
        let mut weights = std::collections::HashMap::new();
        for section in crate::speedrun::outline::SECTIONS {
            for category in section.categories {
                let cc = crate::speedrun::outline::cc_id(category.code);
                let w = planning::illustrative_weight(&cc);
                weights.insert(cc, w);
            }
        }
        weights
    }
}
