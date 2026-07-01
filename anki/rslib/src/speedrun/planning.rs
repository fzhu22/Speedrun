// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Prerequisite-constrained study planning (Rust port of `next_best_topic` in
//! `pylib/anki/speedrun/planning.py`, with the dashboard's illustrative weights
//! and prerequisite edges).
//!
//! Each content-category leaf is scored `yield_weight * weakness`. For a
//! high-value leaf that still has a weak prerequisite, the prerequisite is
//! surfaced instead (recursively) - you should learn what unblocks a topic
//! first. Weights are illustrative and tunable; weakness comes from the memory
//! signal (`1 - recall`, or `1.0` when unknown).

use std::collections::HashMap;
use std::collections::HashSet;

use super::outline;

/// Default yield weight for a content category not called out below.
pub(crate) const BASE_WEIGHT: f32 = 0.30;

/// A prerequisite is only "still weak enough to block" at or above this weakness.
pub(crate) const PREREQ_THRESHOLD: f32 = 0.5;

/// Treat an unknown leaf as maximally worth studying.
const UNKNOWN_WEAKNESS: f32 = 1.0;

/// Illustrative, tunable prerequisite edges as `(prerequisite, dependent)` pairs
/// of `cc:` ids: the first must be learned before the second.
pub(crate) const PREREQUISITES: &[(&str, &str)] = &[
    ("cc:5E", "cc:1D"),
    ("cc:5B", "cc:5D"),
    ("cc:4A", "cc:4B"),
];

/// Illustrative exam-yield weight for a content-category `cc:` id.
pub(crate) fn illustrative_weight(cc_id: &str) -> f32 {
    match cc_id {
        "cc:1A" => 0.90,
        "cc:1D" => 0.85,
        "cc:5E" => 0.80,
        "cc:4A" => 0.70,
        "cc:1B" => 0.60,
        "cc:3A" => 0.60,
        "cc:2A" => 0.50,
        "cc:5A" => 0.50,
        _ => BASE_WEIGHT,
    }
}

/// A single recommended content category to study next.
pub(crate) struct Recommendation {
    pub cc_id: String,
    pub score: f32,
    pub reason: String,
    pub prerequisite: bool,
}

fn weakness_of(weakness: &HashMap<String, f32>, cc_id: &str) -> f32 {
    weakness.get(cc_id).copied().unwrap_or(UNKNOWN_WEAKNESS)
}

/// Follow `dependent -> prerequisite` edges to the first still-weak prerequisite
/// that unblocks `cc_id`, or `cc_id` itself when nothing blocks it.
fn resolve(
    cc_id: &str,
    prereqs: &HashMap<String, Vec<String>>,
    weakness: &HashMap<String, f32>,
    threshold: f32,
    seen: &mut HashSet<String>,
) -> String {
    if let Some(parents) = prereqs.get(cc_id) {
        for p in parents {
            if !seen.contains(p) && weakness_of(weakness, p) >= threshold {
                seen.insert(p.clone());
                return resolve(p, prereqs, weakness, threshold, seen);
            }
        }
    }
    cc_id.to_string()
}

/// The top `k` prerequisite-constrained recommendations, highest score first
/// (ties broken by `cc:` id for determinism).
pub(crate) fn next_best_topic(
    weakness: &HashMap<String, f32>,
    weights: &HashMap<String, f32>,
    prerequisites: &[(&str, &str)],
    prereq_threshold: f32,
    k: usize,
) -> Vec<Recommendation> {
    // dependent -> [prerequisite, ...]
    let mut prereqs: HashMap<String, Vec<String>> = HashMap::new();
    for (prereq, dependent) in prerequisites {
        prereqs
            .entry((*dependent).to_string())
            .or_default()
            .push((*prereq).to_string());
    }

    let weight_of = |cc_id: &str| weights.get(cc_id).copied().unwrap_or(0.0);

    // Best score per recommended node (a prerequisite may unblock several leaves).
    let mut best: HashMap<String, Recommendation> = HashMap::new();
    for section in outline::SECTIONS {
        for category in section.categories {
            let cc_id = outline::cc_id(category.code);
            let base = weight_of(&cc_id) * weakness_of(weakness, &cc_id);
            if base <= 0.0 {
                continue;
            }
            let mut seen = HashSet::from([cc_id.clone()]);
            let target = resolve(&cc_id, &prereqs, weakness, prereq_threshold, &mut seen);
            let is_prereq = target != cc_id;
            let reason = if is_prereq {
                format!("prerequisite of {cc_id}")
            } else {
                "high yield x weakness".to_string()
            };
            let replace = best.get(&target).map(|r| base > r.score).unwrap_or(true);
            if replace {
                best.insert(
                    target.clone(),
                    Recommendation {
                        cc_id: target,
                        score: base,
                        reason,
                        prerequisite: is_prereq,
                    },
                );
            }
        }
    }

    let mut recs: Vec<Recommendation> = best.into_values().collect();
    recs.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| a.cc_id.cmp(&b.cc_id))
    });
    recs.truncate(k);
    recs
}
