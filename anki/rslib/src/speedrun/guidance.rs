// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Deterministic question-writing guidance for the Add-card flow.
//!
//! Rust port of `pylib/anki/speedrun/question_guidance.py`, moved into the shared
//! engine so desktop and AnkiDroid show identical tips. Pure: no AI, no DB writes.

use std::collections::HashSet;

use anki_proto::speedrun::SpeedrunGuidanceRequest;
use anki_proto::speedrun::SpeedrunGuidanceResponse;

use super::outline;
use crate::collection::Collection;
use crate::error::Result;

/// Universal "what makes a good card" rules (kept short so the Add panel never
/// scrolls). Mirrors `TOPIC_TIPS` in the Python.
const TOPIC_TIPS: &[&str] = &[
    "Test why or how, not just a definition.",
    "One idea per card, with a specific answer.",
    "Add the trap: the tempting wrong answer it catches.",
];

fn guidance_lines(code: &str) -> Vec<String> {
    let lead = if code.is_empty() {
        "Write a question that tests why or how, not just recall.".to_string()
    } else {
        format!("For {code}, write a question that makes you USE the idea, not just restate it.")
    };
    let mut lines = Vec::with_capacity(1 + TOPIC_TIPS.len());
    lines.push(lead);
    lines.extend(TOPIC_TIPS.iter().map(|s| (*s).to_string()));
    lines
}

fn tokenize(sources: &[String]) -> HashSet<String> {
    let mut out = HashSet::new();
    for s in sources {
        for tok in s.to_lowercase().split(|c: char| !c.is_alphanumeric()) {
            if !tok.is_empty() {
                out.insert(tok.to_string());
            }
        }
    }
    out
}

/// Best-effort topic from the note's tags + deck: a content-category code token
/// (e.g. a `MCAT::1A::...` tag) first, else a content-category title appearing in
/// the text. Mirrors `infer_topic` in the Python.
fn infer_topic(tags: &[String], deck_name: &str) -> Option<(String, String)> {
    let mut sources: Vec<String> = tags.to_vec();
    if !deck_name.is_empty() {
        sources.push(deck_name.to_string());
    }
    if sources.is_empty() {
        return None;
    }
    let toks = tokenize(&sources);
    for section in outline::SECTIONS {
        for cat in section.categories {
            if toks.contains(&cat.code.to_lowercase()) {
                return Some((cat.code.to_string(), cat.title.to_string()));
            }
        }
    }
    let hay = sources.join(" ").to_lowercase();
    for section in outline::SECTIONS {
        for cat in section.categories {
            if hay.contains(&cat.title.to_lowercase()) {
                return Some((cat.code.to_string(), cat.title.to_string()));
            }
        }
    }
    None
}

impl Collection {
    /// Question-writing guidance for the Add-card flow: resolve the topic (the
    /// explicit code, else inferred from tags/deck), then return the lead line +
    /// universal tips. Deterministic.
    pub fn speedrun_authoring_guidance(
        &mut self,
        input: SpeedrunGuidanceRequest,
    ) -> Result<SpeedrunGuidanceResponse> {
        let topic = if input.code.is_empty() {
            infer_topic(&input.tags, &input.deck_name)
        } else {
            let title = outline::title_for_code(&input.code).unwrap_or("");
            Some((input.code.clone(), title.to_string()))
        };
        let (code, title) = topic.unwrap_or_default();
        Ok(SpeedrunGuidanceResponse {
            lines: guidance_lines(&code),
            code,
            title,
        })
    }
}
