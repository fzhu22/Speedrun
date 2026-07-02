// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Support-fading guidance ladder (PRD 6.3 / brainlift SPOV 10), moved to the
//! shared engine.
//!
//! Scaffolding fades per concept-family as competence grows and returns on
//! regression: it advances after >= 2 unaided successes + 1 transfer pass, and
//! reinstates support (regresses one rung) on any miss. Declarative-recall
//! families opt out entirely.
//!
//! Rust port of `pylib/anki/speedrun/fading.py` + the collection glue in
//! `qt/aqt/speedrun/state.py`. It fixes a real desktop bug: `state.record_answer`
//! keyed the per-family fading state by the *raw* `MCAT::` tag suffix (e.g.
//! `BioBiochem::1A::AminoAcids`), while the dashboard reads the rung by the AAMC
//! content-category CODE (`1A`), so writes and reads used different keys and the
//! ladder never advanced visibly. Here the key is normalised to the same cc code
//! the dashboard uses (via `outline::cc_from_tag`), so the two always agree.

use anki_proto::speedrun::SpeedrunRecordReviewRequest;
use anki_proto::speedrun::SpeedrunRecordReviewResponse;
use anki_proto::stats::TopicMasteryRequest;
use serde_json::Value;

use super::disconfirmer::TAG_PREFIX;
use super::disconfirmer::TRANSFER_TAG;
use super::outline;
use crate::prelude::*;

/// Unaided successes required (with a transfer pass) to fade one rung.
const ADVANCE_UNAIDED: u32 = 2;
/// Transfer passes required (with the unaided successes) to fade one rung.
const ADVANCE_TRANSFER: u32 = 1;
/// Rungs from most support (L3) to least (L0); advancing moves toward L0.
const RUNG_ORDER: [&str; 4] = ["L3", "L2", "L1", "L0"];
/// Config key holding the per-family fading state (`cc_code -> {rung,unaided,transfer}`).
const FADING_CONFIG_KEY: &str = "speedrun_fading";
/// Collection-config flag (synced) that turns support-fading on/off, written by the
/// Study Features ablation dialog. Read here so BOTH platforms obey it. Default on.
const FADING_ENABLED_KEY: &str = "speedrun_fading_enabled";
/// Per-family rung written as a syncable tag so the review tier can read it.
const RUNG_TAG_PREFIX: &str = "speedrun_rung";

fn rung_index(rung: &str) -> usize {
    RUNG_ORDER.iter().position(|r| *r == rung).unwrap_or(0)
}

/// Conservative initial rung from average FSRS recall (`None` = no data). Never
/// seeds L0 from recall alone; L0 is only reachable by demonstrated advancement.
/// Mirrors `estimate_rung` in the Python (and the dashboard's copy).
fn estimate_rung(avg_recall: Option<f32>) -> &'static str {
    match avg_recall {
        None => "L3",
        Some(r) if r < 0.6 => "L3",
        Some(r) if r < 0.85 => "L2",
        Some(_) => "L1",
    }
}

/// Apply the advance/regress rule and return the resulting rung. Mirrors
/// `next_rung` in the Python.
fn next_rung(current: &str, unaided: u32, transfer: u32, transfer_failed: bool) -> String {
    let i = rung_index(current);
    if transfer_failed && i > 0 {
        return RUNG_ORDER[i - 1].to_string(); // regress: bring support back
    }
    if unaided >= ADVANCE_UNAIDED && transfer >= ADVANCE_TRANSFER && i + 1 < RUNG_ORDER.len() {
        return RUNG_ORDER[i + 1].to_string(); // advance: fade support
    }
    current.to_string()
}

/// Update the per-family counter state for one review and return
/// `(resulting_rung, rung_changed)`. Mirrors `record_review` in the Python: on
/// advance/regress the counters reset so each step needs fresh evidence, and any
/// miss reinstates support (reset + regress one rung, bounded at L3).
pub(crate) fn apply_review(
    state: &mut Value,
    family: &str,
    success: bool,
    transfer: bool,
    avg_recall: Option<f32>,
) -> (String, bool) {
    if !state.is_object() {
        *state = serde_json::json!({});
    }
    let obj = state.as_object_mut().expect("state is an object");
    let entry = obj.entry(family.to_string()).or_insert_with(|| {
        serde_json::json!({ "rung": estimate_rung(avg_recall), "unaided": 0, "transfer": 0 })
    });

    let current = entry
        .get("rung")
        .and_then(Value::as_str)
        .unwrap_or("L3")
        .to_string();
    let mut unaided = entry.get("unaided").and_then(Value::as_u64).unwrap_or(0) as u32;
    let mut transfer_count = entry.get("transfer").and_then(Value::as_u64).unwrap_or(0) as u32;

    let updated = if success {
        unaided += 1;
        if transfer {
            transfer_count += 1;
        }
        next_rung(&current, unaided, transfer_count, false)
    } else {
        // Any miss reinstates support: reset progress and regress one rung.
        unaided = 0;
        transfer_count = 0;
        next_rung(&current, 0, 0, true)
    };

    let changed = updated != current;
    // Advancing/regressing resets the counters; otherwise keep the running count.
    let (final_unaided, final_transfer) = if changed {
        (0, 0)
    } else {
        (unaided, transfer_count)
    };
    *entry = serde_json::json!({
        "rung": updated.clone(),
        "unaided": final_unaided,
        "transfer": final_transfer,
    });
    (updated, changed)
}

/// The normalised concept-family key for a note: the AAMC content-category CODE
/// (e.g. `1A`) the dashboard uses, from the first tag that names a known content
/// category. `None` when the note maps to no content category.
fn family_cc_from_note(note: &Note) -> Option<String> {
    note.tags.iter().find_map(|tag| {
        outline::cc_from_tag(tag).map(|cc| cc.strip_prefix("cc:").map(str::to_string).unwrap_or(cc))
    })
}

impl Collection {
    /// Per-cc-code average FSRS recall, aggregated exactly as the dashboard does
    /// (reviewed-card-weighted mean over the tags that map to this content
    /// category). `None` when nothing under the category has been reviewed.
    fn speedrun_avg_recall_for_cc(&mut self, cc_code: &str) -> Result<Option<f32>> {
        let mastery = self.topic_mastery(TopicMasteryRequest {
            search: String::new(),
            tag_prefix: TAG_PREFIX.to_string(),
            mastered_retrievability: 0.0,
            include_descendants: false,
            min_cards_for_average: 1,
        })?;
        let target = outline::cc_id(cc_code);
        let mut weighted_sum = 0.0f64;
        let mut reviewed = 0u32;
        for topic in &mastery.topics {
            if outline::cc_from_tag(&topic.tag).as_deref() == Some(target.as_str()) {
                if let Some(avg) = topic.average_recall {
                    weighted_sum += avg as f64 * topic.reviewed_cards as f64;
                    reviewed += topic.reviewed_cards;
                }
            }
        }
        Ok((reviewed > 0).then(|| (weighted_sum / reviewed as f64) as f32))
    }

    /// Review-time write: update the support-fading ladder for one answered card
    /// and persist the resulting rung (config map + a syncable `speedrun_rung::Lx`
    /// tag). Declarative items are excluded. The whole update is one undoable
    /// transaction so undo works and the collection is never left inconsistent.
    pub fn speedrun_record_review(
        &mut self,
        input: SpeedrunRecordReviewRequest,
    ) -> Result<SpeedrunRecordReviewResponse> {
        // Ablation toggle (spec section 8): support-fading off -> no-op on every
        // platform. Read from synced collection config (default on).
        let fading_on = self
            .get_config_optional::<bool, _>(FADING_ENABLED_KEY)
            .unwrap_or(true);
        if !fading_on {
            return Ok(SpeedrunRecordReviewResponse {
                family: String::new(),
                rung: String::new(),
                changed: false,
            });
        }

        let cid = CardId(input.card_id);
        let card = self.storage.get_card(cid)?.or_not_found(cid)?;
        let note = self
            .storage
            .get_note(card.note_id)?
            .or_not_found(card.note_id)?;

        // The bug fix: key the ladder by the same cc code the dashboard reads.
        let Some(family) = family_cc_from_note(&note) else {
            return Ok(SpeedrunRecordReviewResponse {
                family: String::new(),
                rung: String::new(),
                changed: false,
            });
        };

        // Declarative-recall families opt out of the ladder (SPOV 10).
        if self.speedrun_note_is_declarative(&note)? {
            return Ok(SpeedrunRecordReviewResponse {
                family,
                rung: "L1".to_string(),
                changed: false,
            });
        }

        let success = input.rating >= 2; // Again(1) is the only failed-recall grade
        let transfer = note.tags.iter().any(|t| t == TRANSFER_TAG);
        let avg_recall = self.speedrun_avg_recall_for_cc(&family)?;
        let note_id = note.id;

        let (rung, changed) = self
            .transact(Op::UpdateNote, |col| {
                let mut state = col
                    .get_config_optional::<Value, _>(FADING_CONFIG_KEY)
                    .unwrap_or_else(|| serde_json::json!({}));
                let (rung, changed) = apply_review(&mut state, &family, success, transfer, avg_recall);
                col.set_config(FADING_CONFIG_KEY, &state)?;

                // Persist the rung as a single syncable tag on the note.
                let mut note = col.storage.get_note(note_id)?.or_not_found(note_id)?;
                let prefix = format!("{RUNG_TAG_PREFIX}::");
                let mut new_tags: Vec<String> = note
                    .tags
                    .iter()
                    .filter(|t| !t.starts_with(&prefix))
                    .cloned()
                    .collect();
                new_tags.push(format!("{prefix}{rung}"));
                if new_tags != note.tags {
                    note.tags = new_tags;
                    col.update_note_inner(&mut note)?;
                }
                Ok((rung, changed))
            })?
            .output;

        Ok(SpeedrunRecordReviewResponse {
            family,
            rung,
            changed,
        })
    }
}

#[cfg(test)]
mod test {
    use anki_proto::speedrun::SpeedrunRecordReviewRequest;
    use serde_json::Value;

    use super::*;

    fn add_card(col: &mut Collection, front: &str, back: &str, tags: &[&str]) -> CardId {
        let nt = col.basic_notetype();
        let mut note = nt.new_note();
        note.set_field(0, front).unwrap();
        note.set_field(1, back).unwrap();
        note.tags = tags.iter().map(|t| t.to_string()).collect();
        col.add_note(&mut note, DeckId(1)).unwrap();
        col.storage.all_cards_of_note(note.id).unwrap()[0].id
    }

    fn req(card_id: CardId, rating: u32) -> SpeedrunRecordReviewRequest {
        SpeedrunRecordReviewRequest {
            card_id: card_id.0,
            rating,
        }
    }

    fn note_tags(col: &mut Collection, cid: CardId) -> Vec<String> {
        let nid = col.storage.get_card(cid).unwrap().unwrap().note_id;
        col.storage.get_note(nid).unwrap().unwrap().tags
    }

    fn fading_cfg(col: &Collection) -> Value {
        col.get_config_optional::<Value, _>(FADING_CONFIG_KEY)
            .unwrap_or(Value::Null)
    }

    /// (a) The ladder advances one rung after 2 unaided successes + 1 transfer
    /// pass, and the family state is keyed by the AAMC content-category CODE the
    /// dashboard uses ("1A") - the regression test for the key-mismatch bug.
    #[test]
    fn advances_after_two_unaided_and_one_transfer_keyed_by_cc_code() {
        let mut col = Collection::new();
        let cid = add_card(
            &mut col,
            "Why does raising the pH shift the equilibrium?",
            "The conjugate base is favoured across the buffer region.",
            &["MCAT::BioBiochem::1A::AminoAcids", "speedrun_transfer"],
        );

        // First success: unaided=1 -> not enough to advance yet.
        let r1 = col.speedrun_record_review(req(cid, 3)).unwrap();
        assert_eq!(r1.family, "1A", "family must be the cc CODE, not the raw suffix");
        assert_eq!(r1.rung, "L3");
        assert!(!r1.changed);

        // Second success: unaided=2 + transfer>=1 -> advance L3 -> L2.
        let r2 = col.speedrun_record_review(req(cid, 3)).unwrap();
        assert_eq!(r2.family, "1A");
        assert_eq!(r2.rung, "L2");
        assert!(r2.changed);

        // The state is keyed by "1A" (what the dashboard reads), NOT the raw
        // MCAT:: suffix - so the dashboard rung and the recorded rung agree.
        let cfg = fading_cfg(&col);
        assert_eq!(
            cfg.get("1A").and_then(|e| e.get("rung")).and_then(Value::as_str),
            Some("L2")
        );
        assert!(
            cfg.get("BioBiochem::1A::AminoAcids").is_none(),
            "must not be keyed by the raw suffix (the bug)"
        );

        // And the rung is written back as a syncable tag.
        assert!(note_tags(&mut col, cid).iter().any(|t| t == "speedrun_rung::L2"));
    }

    /// (b) Any miss regresses one rung and resets the counters.
    #[test]
    fn any_miss_regresses_and_resets() {
        let mut col = Collection::new();
        let cid = add_card(
            &mut col,
            "Why is 5E rate-limiting here?",
            "Because the activation energy dominates the observed kinetics.",
            &["MCAT::ChemPhys::5E", "speedrun_transfer"],
        );

        // Advance to L2 (two unaided + transfer).
        let _ = col.speedrun_record_review(req(cid, 3)).unwrap();
        let advanced = col.speedrun_record_review(req(cid, 3)).unwrap();
        assert_eq!(advanced.rung, "L2");

        // A miss (Again=1) reinstates support: L2 -> L3, counters reset.
        let miss = col.speedrun_record_review(req(cid, 1)).unwrap();
        assert_eq!(miss.family, "5E");
        assert_eq!(miss.rung, "L3");
        assert!(miss.changed);

        let entry = fading_cfg(&col).get("5E").cloned().unwrap();
        assert_eq!(entry.get("rung").and_then(Value::as_str), Some("L3"));
        assert_eq!(entry.get("unaided").and_then(Value::as_u64), Some(0));
        assert_eq!(entry.get("transfer").and_then(Value::as_u64), Some(0));

        let tags = note_tags(&mut col, cid);
        assert!(tags.iter().any(|t| t == "speedrun_rung::L3"));
        assert!(!tags.iter().any(|t| t == "speedrun_rung::L2"));
    }

    /// (c) Declarative cards are excluded from the ladder: no state entry and no
    /// rung tag are written, and nothing "changes".
    #[test]
    fn declarative_cards_are_excluded() {
        let mut col = Collection::new();
        let cid = add_card(
            &mut col,
            "How many amino acids are proteinogenic?",
            "20",
            &["MCAT::BioBiochem::1A"],
        );

        let res = col.speedrun_record_review(req(cid, 3)).unwrap();
        assert_eq!(res.family, "1A");
        assert!(!res.changed);

        assert!(
            fading_cfg(&col).get("1A").is_none(),
            "declarative families must not enter the ladder"
        );
        assert!(
            !note_tags(&mut col, cid)
                .iter()
                .any(|t| t.starts_with("speedrun_rung::")),
            "declarative cards must not get a rung tag"
        );
    }

    /// (d) The ablation toggle: `speedrun_fading_enabled = false` makes
    /// record_review a no-op (no state, no rung tag) on every platform.
    #[test]
    fn disabled_flag_skips_fading() {
        let mut col = Collection::new();
        let cid = add_card(
            &mut col,
            "Why does raising the pH shift the equilibrium?",
            "The conjugate base is favoured across the buffer region.",
            &["MCAT::BioBiochem::1A", "speedrun_transfer"],
        );
        col.set_config_json("speedrun_fading_enabled", &false, false).unwrap();

        let res = col.speedrun_record_review(req(cid, 3)).unwrap();
        assert!(!res.changed);
        assert!(res.family.is_empty());
        assert!(fading_cfg(&col).get("1A").is_none(), "no ladder state when disabled");
        assert!(
            !note_tags(&mut col, cid).iter().any(|t| t.starts_with("speedrun_rung::")),
            "no rung tag when disabled"
        );

        // Re-enable -> the ladder resumes writing.
        col.set_config_json("speedrun_fading_enabled", &true, false).unwrap();
        let res = col.speedrun_record_review(req(cid, 3)).unwrap();
        assert_eq!(res.family, "1A");
    }

    /// The pure state machine: a miss at the most-supported rung cannot regress
    /// further, and success without a transfer pass does not advance.
    #[test]
    fn apply_review_edges() {
        // Miss at L3 stays L3 (bounded), counters cleared.
        let mut state = serde_json::json!({});
        let (rung, changed) = apply_review(&mut state, "1A", false, false, None);
        assert_eq!(rung, "L3");
        assert!(!changed);

        // Two unaided successes but NO transfer pass -> no advance.
        let mut state = serde_json::json!({});
        apply_review(&mut state, "1A", true, false, None);
        let (rung, changed) = apply_review(&mut state, "1A", true, false, None);
        assert_eq!(rung, "L3");
        assert!(!changed);
    }
}
