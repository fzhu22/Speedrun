// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Card-type classification and the disconfirmer gating decision.
//!
//! Rust port of `pylib/anki/speedrun/cardtype.py` (the deterministic AI-off
//! baseline). Not every miss deserves a disconfirmer: a pure fact should just be
//! re-studied, while an application/reasoning card is where "what would flip
//! this?" pays off. A card the student keeps missing prompts regardless of type.

use std::sync::LazyLock;

use anki_proto::speedrun::SpeedrunShouldPromptRequest;
use anki_proto::speedrun::SpeedrunShouldPromptResponse;
use regex::Regex;

use super::disconfirmer::DISCONFIRMER_NOTETYPE_NAME;
use crate::prelude::*;
use crate::text::strip_html;

/// Total recent misses (review lapses + repeated Again this session) that mark
/// the student as "clearly struggling" - at which point a disconfirmer is
/// required regardless of card type. Mirrors `STRUGGLE_THRESHOLD` in the Python.
pub(crate) const STRUGGLE_THRESHOLD: u32 = 2;

/// Whether a card is a fact to recall (no disconfirmer) or reasoning/transfer (a
/// disconfirmer helps).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum CardKind {
    Declarative,
    Application,
}

/// Reasoning cues -> application (checked first; they win regardless of answer
/// length). Order/content mirrors `_APPLICATION_MARKERS` in the Python.
const APPLICATION_MARKERS: &[&str] = &[
    "why",
    "predict",
    "compare",
    "explain",
    "how does",
    "how would",
    "what would",
    "which would",
    "if ",
    "calculate",
    "versus",
    " vs ",
    "patient",
    "scenario",
    "would happen",
    "more likely",
    "best explains",
    "what happens",
    "derive",
];

/// Fact cues -> declarative. Mirrors `_DECLARATIVE_MARKERS` in the Python.
const DECLARATIVE_MARKERS: &[&str] = &[
    "how many",
    "what is the",
    "what are the",
    "define",
    "list ",
    "name the",
    "name a",
    "where does",
    "where is",
    "what bond",
    "what type",
    "who ",
    "which gland",
    "which organelle",
    "which enzyme",
    "abbreviation",
];

/// Numeric-ish answer test, matching Python's
/// `re.fullmatch(r"[\d\.\,/\-\s]+[a-zA-Z%]*", a)` ("2 ATP", "7", "14").
static NUMERICISH: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[\d.,/\s-]+[a-zA-Z%]*$").unwrap());
/// Word run, matching Python's `_WORD = re.compile(r"\w+")`.
static WORD: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\w+").unwrap());

fn short_answer(answer: &str) -> bool {
    let a = answer.trim();
    if a.is_empty() {
        return true;
    }
    if NUMERICISH.is_match(a) {
        return true;
    }
    WORD.find_iter(a).count() <= 3
}

/// Deterministic classifier (AI-off path and the eval baseline). Mirrors
/// `heuristic_classify` in the Python.
pub(crate) fn heuristic_classify(question: &str, answer: &str) -> CardKind {
    let q = format!(" {} ", question.to_lowercase().trim());
    if APPLICATION_MARKERS.iter().any(|m| q.contains(m)) {
        return CardKind::Application;
    }
    if short_answer(answer) {
        return CardKind::Declarative;
    }
    if DECLARATIVE_MARKERS.iter().any(|m| q.contains(m)) {
        return CardKind::Declarative;
    }
    // Unsure with a longer answer: treat as application so we don't suppress a
    // potentially useful disconfirmer.
    CardKind::Application
}

/// Whether this miss should require a disconfirmer. Mirrors
/// `should_prompt_disconfirmer` with the desktop default trigger "again_hard"
/// (Again=1 and Hard=2 both count as a failed recall).
pub(crate) fn should_prompt(kind: CardKind, rating: u32, misses: u32, struggle_threshold: u32) -> bool {
    let failed = rating == 1 || rating == 2;
    if !failed {
        return false;
    }
    if misses >= struggle_threshold {
        return true;
    }
    kind == CardKind::Application
}

impl Collection {
    /// The card kind for a note: disconfirmer notes are application by
    /// construction; everything else is judged by the deterministic heuristic on
    /// its (HTML-stripped) first two fields. Mirrors the desktop
    /// `state._note_is_declarative` short-circuit.
    pub(crate) fn speedrun_note_card_kind(&mut self, note: &Note) -> Result<CardKind> {
        let nt = self
            .get_notetype(note.notetype_id)?
            .or_invalid("missing note type")?;
        if nt.name == DISCONFIRMER_NOTETYPE_NAME {
            return Ok(CardKind::Application);
        }
        let question = note
            .fields()
            .first()
            .map(|f| strip_html(f).into_owned())
            .unwrap_or_default();
        let answer = note
            .fields()
            .get(1)
            .map(|f| strip_html(f).into_owned())
            .unwrap_or_default();
        Ok(heuristic_classify(&question, &answer))
    }

    /// Item-level rote check (SPOV 10 excludes declarative recall from fading).
    pub(crate) fn speedrun_note_is_declarative(&mut self, note: &Note) -> Result<bool> {
        Ok(self.speedrun_note_card_kind(note)? == CardKind::Declarative)
    }

    /// Read-only: whether a missed card should prompt for a disconfirmer, and
    /// whether the student is struggling (misses = card.lapses + session_misses).
    pub fn speedrun_should_prompt_disconfirmer(
        &mut self,
        input: SpeedrunShouldPromptRequest,
    ) -> Result<SpeedrunShouldPromptResponse> {
        let cid = CardId(input.card_id);
        let card = self.storage.get_card(cid)?.or_not_found(cid)?;
        let note = self
            .storage
            .get_note(card.note_id)?
            .or_not_found(card.note_id)?;
        let misses = card.lapses.saturating_add(input.session_misses);
        let struggling = misses >= STRUGGLE_THRESHOLD;
        let kind = self.speedrun_note_card_kind(&note)?;
        Ok(SpeedrunShouldPromptResponse {
            should_prompt: should_prompt(kind, input.rating, misses, STRUGGLE_THRESHOLD),
            struggling,
        })
    }
}

#[cfg(test)]
mod test {
    use anki_proto::speedrun::SpeedrunShouldPromptRequest;

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

    fn req(card_id: CardId, rating: u32, session_misses: u32) -> SpeedrunShouldPromptRequest {
        SpeedrunShouldPromptRequest {
            card_id: card_id.0,
            rating,
            session_misses,
        }
    }

    #[test]
    fn heuristic_splits_declarative_from_application() {
        assert_eq!(
            heuristic_classify("How many amino acids are there?", "20"),
            CardKind::Declarative
        );
        assert_eq!(
            heuristic_classify("Why does raising pH above the pKa shift the equilibrium?", "It deprotonates the acid, favouring the conjugate base."),
            CardKind::Application
        );
    }

    /// (d) should_prompt: an application card prompts on the first miss, a
    /// declarative card does not - unless the student is clearly struggling.
    #[test]
    fn prompts_application_on_first_miss_not_declarative() {
        let mut col = Collection::new();
        let app = add_card(
            &mut col,
            "Why does myoglobin bind O2 more tightly than hemoglobin?",
            "It has a hyperbolic curve and higher affinity across partial pressures.",
            &["MCAT::BioBiochem::1A"],
        );
        let decl = add_card(&mut col, "How many amino acids are proteinogenic?", "20", &["MCAT::BioBiochem::1A"]);

        // Application, first miss (Again), no accumulated misses -> prompt.
        let res = col.speedrun_should_prompt_disconfirmer(req(app, 1, 0)).unwrap();
        assert!(res.should_prompt);
        assert!(!res.struggling);

        // Declarative, first miss -> re-study, no prompt.
        let res = col.speedrun_should_prompt_disconfirmer(req(decl, 1, 0)).unwrap();
        assert!(!res.should_prompt);
        assert!(!res.struggling);

        // Declarative but clearly struggling (session misses >= threshold) -> prompt.
        let res = col.speedrun_should_prompt_disconfirmer(req(decl, 1, 2)).unwrap();
        assert!(res.should_prompt);
        assert!(res.struggling);

        // A clean recall (Good) never prompts, even for an application card.
        let res = col.speedrun_should_prompt_disconfirmer(req(app, 3, 0)).unwrap();
        assert!(!res.should_prompt);
    }
}
