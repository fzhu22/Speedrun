// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Coverage of the outline's content-category leaves (Rust port of
//! `pylib/anki/speedrun/coverage.py` as used by the dashboard).
//!
//! A content category counts as covered when a card maps to it (or to a finer
//! descendant tag that rolls up to it - that roll-up already happened when tags
//! were mapped to `cc:` codes). Coverage rolls up per section, and overall
//! coverage is `covered_leaves / total_leaves`. Only content categories count as
//! leaves, so CARS (which has no content-category spine) is not a coverage row.

use std::collections::HashMap;

use super::outline;

/// Per-section coverage of content categories, in outline order.
pub(crate) struct SectionCoverage {
    /// Outline id (e.g. `sec:bbls`), used to align with the outline for memory.
    pub section_id: &'static str,
    pub abbrev: &'static str,
    pub title: &'static str,
    pub fraction: f32,
    /// One `(code, title, covered)` per content-category leaf in this section, in
    /// outline order, so the UI can show exactly which topics are covered vs missing
    /// (spec 7c: mark every outline topic covered / not, not just a section percent).
    pub topics: Vec<(&'static str, &'static str, bool)>,
}

/// Overall + per-section coverage of the outline's content categories.
pub(crate) struct Coverage {
    pub overall: f32,
    pub covered_leaves: u32,
    pub total_leaves: u32,
    /// One row per section that has content categories, in outline order.
    pub per_section: Vec<SectionCoverage>,
}

/// Compute coverage from the set of content categories that have at least one
/// card. `cards_by_cc` is keyed by `cc:` id; a category is covered iff it is a
/// key (topic_mastery only reports tags with >=1 card).
pub(crate) fn compute_coverage(cards_by_cc: &HashMap<String, u32>) -> Coverage {
    let is_covered = |code: &str| cards_by_cc.contains_key(&outline::cc_id(code));

    let mut per_section = Vec::new();
    let mut covered_leaves = 0u32;
    for section in outline::SECTIONS {
        if section.categories.is_empty() {
            continue;
        }
        let total = section.categories.len() as u32;
        let topics: Vec<(&'static str, &'static str, bool)> = section
            .categories
            .iter()
            .map(|c| (c.code, c.title, is_covered(c.code)))
            .collect();
        let covered = topics.iter().filter(|(_, _, cov)| *cov).count() as u32;
        covered_leaves += covered;
        per_section.push(SectionCoverage {
            section_id: section.id,
            abbrev: section.abbrev,
            title: section.title,
            fraction: covered as f32 / total as f32,
            topics,
        });
    }

    let total_leaves = outline::total_leaves();
    let overall = if total_leaves > 0 {
        covered_leaves as f32 / total_leaves as f32
    } else {
        0.0
    };

    Coverage {
        overall,
        covered_leaves,
        total_leaves,
        per_section,
    }
}
