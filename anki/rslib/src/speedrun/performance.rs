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
use std::collections::HashSet;

use anki_proto::speedrun::SpeedrunFitPerformanceResponse;
use anki_proto::stats::TopicMasteryRequest;

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
/// Cached score-model evidence (spec section 9 Steps 1 & 2), written by the fit tier and
/// read by the read-only dashboard so it never pays the calibration recompute per load.
pub(crate) const EVIDENCE_CONFIG_KEY: &str = "speedrun_evidence";

/// Serde shape of the cached evidence (mirrors the proto `SpeedrunEvidence`).
#[derive(serde::Serialize, serde::Deserialize, Default)]
pub(crate) struct EvidenceCache {
    pub memory_log_loss: Option<f32>,
    pub memory_rmse: Option<f32>,
    pub memory_reviews: u32,
    pub perf_auc_full: f32,
    pub perf_auc_recall: f32,
    pub perf_auc_delta: f32,
    pub perf_responses: u32,
    pub perf_passed: bool,
}

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

// -- fit tier: the desktop "Fit Performance Model" step, ported to Rust --------
//
// Rust port of `pylib/anki/speedrun/performance.py` + `perf_fit.py`. Extracts one
// graded response per revlog row on a held-out Performance Item card, fits a
// calibrated logistic model, and runs the incremental-validity gate (k-fold
// out-of-sample AUC of a full model vs a recall-only model). Performance is only
// enabled if it beats recall by a margin on enough data - the SPOV 3 honesty rule.

/// Minimum graded held-out responses before Performance may be shown.
const MIN_RESPONSES: u32 = 30;
/// The full model must beat recall-only by at least this out-of-sample AUC.
const MIN_AUC_DELTA: f64 = 0.02;

/// One graded answer on a held-out exam-style item.
struct Response {
    correct: bool,
    recall: f64,
    difficulty: f64,
    latency_ms: i64,
    coverage: f64,
}

fn latency_norm(ms: i64) -> f64 {
    (ms as f64 / 60000.0).clamp(0.0, 1.0)
}

fn full_features(r: &Response) -> Vec<f64> {
    vec![r.recall, r.difficulty, latency_norm(r.latency_ms), r.coverage]
}

fn recall_features(r: &Response) -> Vec<f64> {
    vec![r.recall]
}

fn sigmoid(z: f64) -> f64 {
    if z < -60.0 {
        0.0
    } else if z > 60.0 {
        1.0
    } else {
        1.0 / (1.0 + (-z).exp())
    }
}

struct LogisticModel {
    w: Vec<f64>,
    b: f64,
    means: Vec<f64>,
    stds: Vec<f64>,
}

fn standardize(rows: &[Vec<f64>]) -> (Vec<f64>, Vec<f64>) {
    let d = rows[0].len();
    let n = rows.len() as f64;
    let mut means = vec![0.0; d];
    for r in rows {
        for k in 0..d {
            means[k] += r[k];
        }
    }
    for m in means.iter_mut() {
        *m /= n;
    }
    let mut stds = vec![0.0; d];
    for r in rows {
        for k in 0..d {
            let diff = r[k] - means[k];
            stds[k] += diff * diff;
        }
    }
    for s in stds.iter_mut() {
        let v = (*s / n).sqrt();
        *s = if v == 0.0 { 1.0 } else { v };
    }
    (means, stds)
}

/// Standardized logistic regression by batch gradient descent (deterministic),
/// mirroring `fit_logistic` in the Python (lr 0.3, l2 1.0, 800 iters).
fn fit_logistic(x: &[Vec<f64>], y: &[i32]) -> LogisticModel {
    let (means, stds) = standardize(x);
    let d = means.len();
    let n = x.len() as f64;
    let xs: Vec<Vec<f64>> = x
        .iter()
        .map(|row| (0..d).map(|k| (row[k] - means[k]) / stds[k]).collect())
        .collect();
    let mut w = vec![0.0; d];
    let mut b = 0.0;
    let (lr, l2, iters) = (0.3_f64, 1.0_f64, 800);
    for _ in 0..iters {
        let mut gw = vec![0.0; d];
        let mut gb = 0.0;
        for (xi, &yi) in xs.iter().zip(y.iter()) {
            let z = b + (0..d).map(|k| w[k] * xi[k]).sum::<f64>();
            let err = sigmoid(z) - yi as f64;
            for k in 0..d {
                gw[k] += err * xi[k];
            }
            gb += err;
        }
        for k in 0..d {
            w[k] -= lr * (gw[k] / n + l2 * w[k] / n);
        }
        b -= lr * gb / n;
    }
    LogisticModel { w, b, means, stds }
}

fn predict(m: &LogisticModel, x: &[f64]) -> f64 {
    let z = m.b
        + (0..m.w.len())
            .map(|k| m.w[k] * ((x[k] - m.means[k]) / m.stds[k]))
            .sum::<f64>();
    sigmoid(z)
}

/// Mann-Whitney AUC with average ranks for ties; 0.5 if degenerate.
fn auc(y: &[i32], scores: &[f64]) -> f64 {
    let n_pos = y.iter().filter(|&&v| v == 1).count();
    let n_neg = y.len() - n_pos;
    if n_pos == 0 || n_neg == 0 {
        return 0.5;
    }
    let mut order: Vec<usize> = (0..scores.len()).collect();
    order.sort_by(|&a, &b| {
        scores[a]
            .partial_cmp(&scores[b])
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    let mut ranks = vec![0.0; order.len()];
    let mut i = 0;
    while i < order.len() {
        let mut j = i;
        while j + 1 < order.len() && scores[order[j + 1]] == scores[order[i]] {
            j += 1;
        }
        let avg = (i + j) as f64 / 2.0 + 1.0;
        for k in i..=j {
            ranks[order[k]] = avg;
        }
        i = j + 1;
    }
    let sum_pos: f64 = (0..y.len()).filter(|&i| y[i] == 1).map(|i| ranks[i]).sum();
    (sum_pos - n_pos as f64 * (n_pos as f64 + 1.0) / 2.0) / (n_pos as f64 * n_neg as f64)
}

/// Deterministic Fisher-Yates shuffle (fixed seed), so folds are stable across
/// runs (the Python uses a seeded RNG for the same reason).
fn shuffled_indices(n: usize) -> Vec<usize> {
    let mut idx: Vec<usize> = (0..n).collect();
    let mut state: u64 = 0x2545_F491_4F6C_DD1D;
    for i in (1..n).rev() {
        state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        let j = (state >> 33) as usize % (i + 1);
        idx.swap(i, j);
    }
    idx
}

/// Out-of-sample AUC of a full model vs a recall-only model via k-fold CV.
/// Returns (auc_full, auc_recall, delta).
fn incremental_validity(responses: &[Response]) -> (f64, f64, f64) {
    let n = responses.len();
    if n < 2 {
        return (0.5, 0.5, 0.0);
    }
    let y: Vec<i32> = responses.iter().map(|r| i32::from(r.correct)).collect();
    let full: Vec<Vec<f64>> = responses.iter().map(full_features).collect();
    let rec: Vec<Vec<f64>> = responses.iter().map(recall_features).collect();
    let idx = shuffled_indices(n);
    let k = std::cmp::max(2, std::cmp::min(5, n));
    let mut full_scores = Vec::new();
    let mut rec_scores = Vec::new();
    let mut ys = Vec::new();
    for f in 0..k {
        let test: Vec<usize> = (0..n).filter(|i| i % k == f).map(|i| idx[i]).collect();
        let test_set: HashSet<usize> = test.iter().copied().collect();
        let train: Vec<usize> = idx.iter().copied().filter(|i| !test_set.contains(i)).collect();
        if train.is_empty() || test.is_empty() {
            continue;
        }
        let train_labels: HashSet<i32> = train.iter().map(|&i| y[i]).collect();
        if train_labels.len() < 2 {
            continue;
        }
        let train_full: Vec<Vec<f64>> = train.iter().map(|&i| full[i].clone()).collect();
        let train_rec: Vec<Vec<f64>> = train.iter().map(|&i| rec[i].clone()).collect();
        let train_y: Vec<i32> = train.iter().map(|&i| y[i]).collect();
        let mf = fit_logistic(&train_full, &train_y);
        let mr = fit_logistic(&train_rec, &train_y);
        for &i in &test {
            full_scores.push(predict(&mf, &full[i]));
            rec_scores.push(predict(&mr, &rec[i]));
            ys.push(y[i]);
        }
    }
    if ys.is_empty() {
        return (0.5, 0.5, 0.0);
    }
    let a_full = auc(&ys, &full_scores);
    let a_rec = auc(&ys, &rec_scores);
    (a_full, a_rec, a_full - a_rec)
}

impl Collection {
    /// Fit the performance model from the review log and set the enabled flag
    /// (the shared engine port of the desktop "Fit Performance Model" step).
    /// Performance is enabled only when it beats recall out-of-sample on enough
    /// data (SPOV 3). Returns the gate stats for display.
    pub fn speedrun_fit_performance(&mut self) -> Result<SpeedrunFitPerformanceResponse> {
        let responses = self.speedrun_perf_responses()?;
        let n = responses.len() as u32;
        let (auc_full, auc_recall, delta) = incremental_validity(&responses);
        let passed = n >= MIN_RESPONSES && delta >= MIN_AUC_DELTA;

        // Step 1 (memory calibration): evaluate FSRS on held-back reviews via its
        // time-series split. Best-effort - a collection without enough review history
        // simply leaves the memory numbers unset (the dashboard then abstains on them).
        let (memory_log_loss, memory_rmse, memory_reviews) =
            match self.evaluate_params("", 0i64.into(), 0) {
                Ok(eval) => {
                    let reviews: u32 = self
                        .storage
                        .db
                        .query_row("SELECT count() FROM revlog WHERE type IN (0,1,2)", [], |r| {
                            r.get(0)
                        })
                        .unwrap_or(0);
                    (Some(eval.log_loss), Some(eval.rmse_bins), reviews)
                }
                Err(_) => (None, None, 0),
            };

        let evidence = EvidenceCache {
            memory_log_loss,
            memory_rmse,
            memory_reviews,
            perf_auc_full: auc_full as f32,
            perf_auc_recall: auc_recall as f32,
            perf_auc_delta: delta as f32,
            perf_responses: n,
            perf_passed: passed,
        };

        self.transact(Op::UpdateNote, |col| {
            col.set_config(ENABLED_CONFIG_KEY, &passed)?;
            col.set_config(EVIDENCE_CONFIG_KEY, &evidence)?;
            Ok(())
        })?;

        Ok(SpeedrunFitPerformanceResponse {
            passed,
            n,
            auc_full: auc_full as f32,
            auc_recall: auc_recall as f32,
            delta: delta as f32,
            min_responses: MIN_RESPONSES,
            min_delta: MIN_AUC_DELTA as f32,
        })
    }

    /// One `Response` per graded answer on a held-out Performance Item card, with
    /// its content category's mean FSRS recall as the `recall` feature (the same
    /// per-cc recall the dashboard uses); difficulty/coverage are placeholders,
    /// matching the Python.
    fn speedrun_perf_responses(&mut self) -> Result<Vec<Response>> {
        let mastery = self.topic_mastery(TopicMasteryRequest {
            search: String::new(),
            tag_prefix: "MCAT".to_string(),
            mastered_retrievability: 0.9,
            include_descendants: false,
            min_cards_for_average: 1,
        })?;
        let mut recall_wsum: HashMap<String, f64> = HashMap::new();
        let mut reviewed: HashMap<String, u32> = HashMap::new();
        for t in &mastery.topics {
            if let (Some(cc), Some(avg)) = (outline::cc_from_tag(&t.tag), t.average_recall) {
                *recall_wsum.entry(cc.clone()).or_default() += avg as f64 * t.reviewed_cards as f64;
                *reviewed.entry(cc).or_default() += t.reviewed_cards;
            }
        }
        let recall_by_cc: HashMap<String, f64> = reviewed
            .iter()
            .filter(|(_, &n)| n > 0)
            .map(|(cc, &n)| (cc.clone(), recall_wsum[cc] / n as f64))
            .collect();

        let Some(nt) = self.get_notetype_by_name(PERF_NOTETYPE_NAME)? else {
            return Ok(Vec::new());
        };
        let rows: Vec<(String, i64, i64)> = self
            .storage
            .db
            .prepare_cached(
                "SELECT n.tags, r.ease, r.time FROM revlog r \
                 JOIN cards c ON c.id = r.cid \
                 JOIN notes n ON n.id = c.nid \
                 WHERE n.mid = ?1 AND r.ease >= 1",
            )?
            .query_map([nt.id.0], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?, row.get::<_, i64>(2)?))
            })?
            .collect::<rusqlite::Result<Vec<_>>>()?;

        let mut responses = Vec::with_capacity(rows.len());
        for (tags, ease, time) in rows {
            let recall = tags
                .split_whitespace()
                .find_map(outline::cc_from_tag)
                .and_then(|cc| recall_by_cc.get(&cc).copied())
                .unwrap_or(0.5);
            responses.push(Response {
                correct: ease >= CORRECT_MIN_EASE,
                recall,
                difficulty: 0.5,
                latency_ms: time,
                coverage: 0.0,
            });
        }
        Ok(responses)
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
