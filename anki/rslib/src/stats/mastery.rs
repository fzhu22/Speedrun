// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Speedrun: per-topic mastery query.
//!
//! Returns, per topic (a tag), how many cards are mastered and the average FSRS
//! recall, in a single pass over the collection. Anki has no native "topic"
//! concept, so cards are grouped by their note's tags (`::` denotes hierarchy).
//!
//! This is a read-only engine query: it records no undo step and mutates
//! nothing, so it is safe to call as often as the dashboard/coverage map needs.
//! Because it lives in rslib it ships to the desktop and the phone build through
//! the shared engine.

use std::collections::HashMap;
use std::collections::HashSet;

use anki_proto::stats::topic_mastery_response::Topic;
use anki_proto::stats::TopicMasteryRequest;
use anki_proto::stats::TopicMasteryResponse;
use rusqlite::params;

use crate::card::CardType;
use crate::prelude::*;
use crate::search::SortMode;

/// Mastery threshold used when the request leaves `mastered_retrievability` at
/// 0. A card at or above this FSRS retrievability (and in the Review state)
/// counts as mastered.
const DEFAULT_MASTERED_RETRIEVABILITY: f32 = 0.9;

#[derive(Default)]
struct TopicAcc {
    total: u32,
    mastered: u32,
    reviewed: u32,
    sum_retrievability: f64,
}

struct MasteryRow {
    cid: CardId,
    tags: String,
    ctype: u8,
    retrievability: Option<f64>,
}

/// Whether a tag (or one of its `::` ancestor paths) is equal to or under the
/// scope prefix. An empty prefix matches everything.
fn tag_in_scope(tag: &str, prefix: &str) -> bool {
    prefix.is_empty()
        || tag == prefix
        || (tag.starts_with(prefix) && tag[prefix.len()..].starts_with("::"))
}

impl Collection {
    /// Per-topic mastered-card counts and average recall. See the module docs
    /// for the definitions of "mastered" and "average recall".
    pub fn topic_mastery(
        &mut self,
        input: TopicMasteryRequest,
    ) -> Result<TopicMasteryResponse> {
        let threshold = if input.mastered_retrievability > 0.0 {
            input.mastered_retrievability
        } else {
            DEFAULT_MASTERED_RETRIEVABILITY
        };
        let min_for_average = input.min_cards_for_average.max(1);
        let prefix = input.tag_prefix.trim();

        // Optionally scope to a search. None means "the whole collection".
        let allowed: Option<HashSet<CardId>> = if input.search.trim().is_empty() {
            None
        } else {
            Some(
                self.search_cards(input.search.as_str(), SortMode::NoOrder)?
                    .into_iter()
                    .collect(),
            )
        };

        let timing = self.timing_today()?;
        let days_elapsed = timing.days_elapsed;
        let next_day_at = timing.next_day_at.0;
        let now = timing.now.0;

        // One pass: every card with its note's tags and computed retrievability.
        let rows: Vec<MasteryRow> = self
            .storage
            .db
            .prepare_cached(include_str!("mastery.sql"))?
            .query_and_then(
                params![days_elapsed, next_day_at, now],
                |row| -> Result<MasteryRow> {
                    Ok(MasteryRow {
                        cid: CardId(row.get(0)?),
                        tags: row.get(1)?,
                        ctype: row.get(2)?,
                        retrievability: row.get(3)?,
                    })
                },
            )?
            .collect::<Result<Vec<_>>>()?;

        let review_type = CardType::Review as u8;
        let mut topics: HashMap<String, TopicAcc> = HashMap::new();
        let mut untagged_cards: u32 = 0;

        for row in rows {
            if let Some(allowed) = &allowed {
                if !allowed.contains(&row.cid) {
                    continue;
                }
            }

            let mastered = row.ctype == review_type
                && row
                    .retrievability
                    .is_some_and(|r| r as f32 >= threshold);

            // The set of topic keys this card contributes to (deduped so a card
            // is never counted twice for the same topic).
            let mut keys: HashSet<String> = HashSet::new();
            for tag in row.tags.split_whitespace() {
                if !tag_in_scope(tag, prefix) {
                    continue;
                }
                if input.include_descendants {
                    // Contribute to the tag and every ancestor path in scope.
                    let mut path = String::new();
                    for (i, part) in tag.split("::").enumerate() {
                        if i > 0 {
                            path.push_str("::");
                        }
                        path.push_str(part);
                        if tag_in_scope(&path, prefix) {
                            keys.insert(path.clone());
                        }
                    }
                } else {
                    keys.insert(tag.to_string());
                }
            }

            if keys.is_empty() {
                untagged_cards += 1;
                continue;
            }

            for key in keys {
                let acc = topics.entry(key).or_default();
                acc.total += 1;
                if mastered {
                    acc.mastered += 1;
                }
                if let Some(r) = row.retrievability {
                    acc.reviewed += 1;
                    acc.sum_retrievability += r;
                }
            }
        }

        let mut topics: Vec<Topic> = topics
            .into_iter()
            .map(|(tag, acc)| {
                // Abstain from an average until there is enough data to back it.
                let average_recall = if acc.reviewed >= min_for_average {
                    Some((acc.sum_retrievability / acc.reviewed as f64) as f32)
                } else {
                    None
                };
                Topic {
                    tag,
                    total_cards: acc.total,
                    mastered_cards: acc.mastered,
                    reviewed_cards: acc.reviewed,
                    average_recall,
                }
            })
            .collect();
        topics.sort_by(|a, b| a.tag.cmp(&b.tag));

        Ok(TopicMasteryResponse {
            topics,
            untagged_cards,
        })
    }
}

#[cfg(test)]
mod test {
    use anki_proto::stats::TopicMasteryRequest;

    use crate::card::CardType;
    use crate::card::FsrsMemoryState;
    use crate::prelude::*;

    fn req() -> TopicMasteryRequest {
        TopicMasteryRequest {
            search: String::new(),
            tag_prefix: String::new(),
            mastered_retrievability: 0.0,
            include_descendants: false,
            min_cards_for_average: 0,
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
    /// reviewed `secs_since_review` seconds ago. A large stability reviewed just
    /// now yields a retrievability of ~1.0; a small stability reviewed long ago
    /// yields ~0.0.
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

    #[test]
    fn aggregates_by_tag_and_counts_untagged() {
        let mut col = Collection::new();
        add_card_with_tags(&mut col, &["MCAT::Bio"]);
        add_card_with_tags(&mut col, &["MCAT::Chem"]);
        add_card_with_tags(&mut col, &[]);

        let res = col.topic_mastery(req()).unwrap();

        assert_eq!(res.untagged_cards, 1);
        assert_eq!(res.topics.len(), 2);
        // sorted alphabetically
        assert_eq!(res.topics[0].tag, "MCAT::Bio");
        assert_eq!(res.topics[1].tag, "MCAT::Chem");
        assert_eq!(res.topics[0].total_cards, 1);
        // no FSRS state yet, so nothing reviewed or mastered
        assert_eq!(res.topics[0].reviewed_cards, 0);
        assert_eq!(res.topics[0].mastered_cards, 0);
        assert!(res.topics[0].average_recall.is_none());
    }

    #[test]
    fn applies_mastery_threshold_and_average_recall() {
        let mut col = Collection::new();
        let mastered = add_card_with_tags(&mut col, &["MCAT::Bio"]);
        let weak = add_card_with_tags(&mut col, &["MCAT::Bio"]);
        // strong: high stability, reviewed now -> retrievability ~1.0
        set_memory(&mut col, mastered, 10_000.0, 0);
        // weak: tiny stability, reviewed 100 days ago -> retrievability ~0.0
        set_memory(&mut col, weak, 1.0, 100 * 86_400);

        let res = col.topic_mastery(req()).unwrap();
        let bio = res.topics.iter().find(|t| t.tag == "MCAT::Bio").unwrap();

        assert_eq!(bio.total_cards, 2);
        assert_eq!(bio.reviewed_cards, 2);
        // default threshold 0.9 -> only the strong card is mastered
        assert_eq!(bio.mastered_cards, 1);
        let avg = bio.average_recall.expect("average present with 2 reviewed");
        // Mean of one ~1.0 card and one low-retrievability card. The band is
        // wide to stay robust to FSRS parameter changes, while still proving the
        // average is a real mean (neither 1.0 nor 0.0).
        assert!((0.35..0.85).contains(&avg), "unexpected average recall {avg}");
    }

    #[test]
    fn rolls_up_hierarchy_when_requested() {
        let mut col = Collection::new();
        add_card_with_tags(&mut col, &["MCAT::Bio::Enzymes"]);
        add_card_with_tags(&mut col, &["MCAT::Chem"]);

        let mut request = req();
        request.include_descendants = true;
        let res = col.topic_mastery(request).unwrap();
        let total = |tag: &str| res.topics.iter().find(|t| t.tag == tag).map(|t| t.total_cards);

        assert_eq!(total("MCAT"), Some(2));
        assert_eq!(total("MCAT::Bio"), Some(1));
        assert_eq!(total("MCAT::Bio::Enzymes"), Some(1));
        assert_eq!(total("MCAT::Chem"), Some(1));
        assert_eq!(res.untagged_cards, 0);
    }

    #[test]
    fn is_read_only_and_deterministic() {
        let mut col = Collection::new();
        add_card_with_tags(&mut col, &["MCAT::Bio"]);

        // A read-only query must not push an undo step or change the collection.
        let before = col.undo_status().last_step;
        let first = col.topic_mastery(req()).unwrap();
        let after = col.undo_status().last_step;
        assert_eq!(before, after, "topic_mastery must not record an undo step");

        let second = col.topic_mastery(req()).unwrap();
        assert_eq!(first, second, "topic_mastery must be deterministic");
    }

    /// Performance benchmark for the 50k-card target (spec sections 7h and 10).
    /// Ignored by default; run with:
    ///   cargo test -p anki topic_mastery_benchmark -- --ignored --nocapture
    /// Override the card count with TOPIC_MASTERY_BENCH_CARDS.
    #[test]
    #[ignore = "performance benchmark; run with --ignored"]
    fn topic_mastery_benchmark() {
        use std::time::Duration;
        use std::time::Instant;

        let card_count: usize = std::env::var("TOPIC_MASTERY_BENCH_CARDS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(50_000);
        let topics = [
            "MCAT::Bio",
            "MCAT::Chem",
            "MCAT::Physics",
            "MCAT::Psych",
            "MCAT::Biochem",
        ];

        let mut col = Collection::new();
        for i in 0..card_count {
            let cid = add_card_with_tags(&mut col, &[topics[i % topics.len()]]);
            // Give about half the cards FSRS state so retrievability is exercised.
            if i % 2 == 0 {
                set_memory(&mut col, cid, 100.0, (i as i64 % 30) * 86_400);
            }
        }

        let mut durations: Vec<Duration> = Vec::new();
        for _ in 0..20 {
            let start = Instant::now();
            let res = col.topic_mastery(req()).unwrap();
            assert_eq!(res.topics.len(), topics.len());
            durations.push(start.elapsed());
        }
        durations.sort();
        let p50 = durations[durations.len() / 2];
        let p95 = durations[(durations.len() * 95 / 100).saturating_sub(1)];
        let worst = *durations.last().unwrap();
        println!(
            "topic_mastery over {card_count} cards: p50={p50:?} p95={p95:?} worst={worst:?} \
             (debug_assertions={})",
            cfg!(debug_assertions)
        );

        // The spec's speed targets apply to the shipped (optimized) build, so the
        // hard threshold is only enforced for release builds. A debug build runs
        // several times slower and is not representative.
        if !cfg!(debug_assertions) {
            assert!(
                p95 < Duration::from_secs(1),
                "p95 {p95:?} exceeds the 1s dashboard target"
            );
        }
    }
}
