// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Performance lane (brainlift SPOV 3, spec section 9 Step 2): per-section accuracy on
//! graded held-out exam-style items (the "Qbank"), read from the review log.
//!
//! This is the *review-tier read* of a two-tier feature. The desktop "prepare" tier
//! (Python `anki.speedrun.performance`) fits the model and runs the incremental-validity
//! check, writing a single syncable flag `speedrun_performance_enabled` when Performance
//! earns its place (beats recall out-of-sample). Here we only read that flag and, if set,
//! surface the *measured* per-section accuracy with a Wilson range - a separately-gated
//! score, never blended with Memory. If the flag is unset, Performance abstains entirely.

use std::collections::HashMap;

use super::dashboard::wilson_interval;
use super::disconfirmer::PERF_NOTETYPE_NAME;
use super::outline;
use crate::prelude::*;

/// A section needs at least this many graded held-out items before its performance shows.
const MIN_ITEMS_PER_SECTION: u32 = 5;
/// Set by the desktop prepare tier once the incremental-validity gate passes.
const ENABLED_CONFIG_KEY: &str = "speedrun_performance_enabled";
/// A passing grade (Hard/Good/Easy, ease >= 2) = answered correctly; Again (1) = wrong
/// (matches the record_review success convention and the item template's guidance).
const CORRECT_MIN_EASE: i64 = 2;

pub(crate) struct SectionPerf {
    pub accuracy: Option<f32>,
    pub low: Option<f32>,
    pub high: Option<f32>,
    pub items: u32,
}

pub(crate) struct PerformanceReport {
    /// section id (e.g. `sec:bbls`) -> per-section performance.
    pub by_section: HashMap<String, SectionPerf>,
    /// "allowed" or an abstain reason (the top-level performance_status).
    pub status: String,
}

/// The section id that owns a content-category id (`cc:1A` -> `sec:bbls`).
fn section_id_for_cc(cc: &str) -> Option<&'static str> {
    outline::SECTIONS.iter().find_map(|s| {
        s.categories
            .iter()
            .any(|c| outline::cc_id(c.code) == cc)
            .then_some(s.id)
    })
}

fn status_string(enabled: bool, graded_total: u32) -> String {
    if graded_total == 0 {
        // Kept identical to the prior placeholder so a fresh deck reads the same.
        "insufficient data - no exam-style items yet".to_string()
    } else if !enabled {
        "abstaining - performance model not validated (Tools > Fit Performance Model)".to_string()
    } else {
        "allowed".to_string()
    }
}

impl Collection {
    /// Read-only per-section performance from the review log of Speedrun Performance
    /// Item cards. Abstains entirely unless the gate flag is set, and per section until it
    /// has enough graded items. Records no undo step.
    pub(crate) fn speedrun_section_performance(&mut self) -> Result<PerformanceReport> {
        let enabled = self
            .get_config_optional::<bool, _>(ENABLED_CONFIG_KEY)
            .unwrap_or(false);

        let mut by_section: HashMap<String, SectionPerf> = HashMap::new();

        let Some(nt) = self.get_notetype_by_name(PERF_NOTETYPE_NAME)? else {
            return Ok(PerformanceReport {
                by_section,
                status: status_string(enabled, 0),
            });
        };

        let rows: Vec<(String, i64)> = self
            .storage
            .db
            .prepare_cached(
                "SELECT n.tags, r.ease FROM revlog r \
                 JOIN cards c ON c.id = r.cid \
                 JOIN notes n ON n.id = c.nid \
                 WHERE n.mid = ?1 AND r.ease >= 1",
            )?
            .query_map([nt.id.0], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?))
            })?
            .collect::<rusqlite::Result<Vec<_>>>()?;

        // (correct, total) per section id.
        let mut totals: HashMap<&'static str, (u32, u32)> = HashMap::new();
        let mut graded_total = 0u32;
        for (tags, ease) in rows {
            let Some(section) = tags
                .split_whitespace()
                .find_map(outline::cc_from_tag)
                .and_then(|cc| section_id_for_cc(&cc))
            else {
                continue;
            };
            let entry = totals.entry(section).or_insert((0, 0));
            entry.1 += 1;
            graded_total += 1;
            if ease >= CORRECT_MIN_EASE {
                entry.0 += 1;
            }
        }

        for (section, (correct, total)) in totals {
            if enabled && total >= MIN_ITEMS_PER_SECTION {
                let p = correct as f32 / total as f32;
                let (lo, hi) = wilson_interval(p, total);
                by_section.insert(
                    section.to_string(),
                    SectionPerf { accuracy: Some(p), low: Some(lo), high: Some(hi), items: total },
                );
            } else {
                by_section.insert(
                    section.to_string(),
                    SectionPerf { accuracy: None, low: None, high: None, items: total },
                );
            }
        }

        Ok(PerformanceReport {
            by_section,
            status: status_string(enabled, graded_total),
        })
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::revlog::RevlogEntry;

    fn add_perf_card(col: &mut Collection, tags: &[&str]) -> CardId {
        col.speedrun_ensure_notetypes().unwrap();
        let nt = col.get_notetype_by_name(PERF_NOTETYPE_NAME).unwrap().unwrap();
        let mut note = nt.new_note();
        note.tags = tags.iter().map(|t| t.to_string()).collect();
        col.add_note(&mut note, DeckId(1)).unwrap();
        col.storage.all_cards_of_note(note.id).unwrap()[0].id
    }

    fn add_answer(col: &mut Collection, cid: CardId, ease: u8) {
        let entry = RevlogEntry {
            cid,
            button_chosen: ease,
            ..Default::default()
        };
        col.storage.add_revlog_entry(&entry, true).unwrap();
    }

    fn enable(col: &mut Collection) {
        col.transact(Op::UpdateNote, |col| {
            col.set_config(ENABLED_CONFIG_KEY, &true)?;
            Ok(())
        })
        .unwrap();
    }

    /// Without the gate flag, Performance abstains even with answers - but it still
    /// counts the items behind the (withheld) estimate.
    #[test]
    fn abstains_without_gate_flag() {
        let mut col = Collection::new();
        let cid = add_perf_card(&mut col, &["MCAT::BioBiochem::1A"]);
        for _ in 0..6 {
            add_answer(&mut col, cid, 3);
        }
        let rep = col.speedrun_section_performance().unwrap();
        let sp = rep.by_section.get("sec:bbls").expect("section present");
        assert!(sp.accuracy.is_none(), "gated off until the model is validated");
        assert_eq!(sp.items, 6);
        assert!(rep.status.contains("not validated"));
    }

    /// With the flag set and enough items, Performance shows measured accuracy + a range.
    #[test]
    fn shows_accuracy_when_enabled() {
        let mut col = Collection::new();
        let cid = add_perf_card(&mut col, &["MCAT::BioBiochem::1A::AminoAcids"]);
        for ease in [3u8, 3, 3, 3, 1, 1] {
            add_answer(&mut col, cid, ease); // 4 correct (>=2), 2 wrong -> 4/6
        }
        enable(&mut col);
        let rep = col.speedrun_section_performance().unwrap();
        let sp = rep.by_section.get("sec:bbls").unwrap();
        let acc = sp.accuracy.expect("accuracy shows when enabled + enough items");
        assert!((acc - 4.0 / 6.0).abs() < 1e-6);
        assert!(sp.low.is_some() && sp.high.is_some());
        assert_eq!(sp.items, 6);
        assert_eq!(rep.status, "allowed");
    }

    /// A section below the item threshold keeps abstaining even when enabled.
    #[test]
    fn few_items_still_abstains() {
        let mut col = Collection::new();
        let cid = add_perf_card(&mut col, &["MCAT::ChemPhys::5E"]);
        for _ in 0..3 {
            add_answer(&mut col, cid, 3);
        }
        enable(&mut col);
        let rep = col.speedrun_section_performance().unwrap();
        let sp = rep.by_section.get("sec:cpbs").unwrap();
        assert!(sp.accuracy.is_none(), "below MIN_ITEMS_PER_SECTION -> abstain");
        assert_eq!(sp.items, 3);
    }

    /// The read of performance records no undo step.
    #[test]
    fn is_read_only() {
        let mut col = Collection::new();
        let cid = add_perf_card(&mut col, &["MCAT::ChemPhys::5E"]);
        for _ in 0..6 {
            add_answer(&mut col, cid, 3);
        }
        enable(&mut col);
        let before = col.undo_status().last_step;
        let _ = col.speedrun_section_performance().unwrap();
        assert_eq!(before, col.undo_status().last_step, "must not record an undo step");
    }
}
