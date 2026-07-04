// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! The Speedrun Disconfirmer / Pretest note types and their authoring helpers.
//!
//! Rust port of `pylib/anki/speedrun/disconfirmer.py` and `pretest.py`, moved
//! into the shared engine so the desktop and (later) AnkiDroid create identical
//! note types and disconfirmer cards from one implementation.
//!
//! Honesty rule (load-bearing): the disconfirmer body is *student-authored* -
//! this module never fabricates it. It only validates the text the student wrote
//! (a nudge they can override) and stores it verbatim.

use anki_proto::speedrun::SpeedrunCreateDisconfirmerRequest;
use anki_proto::speedrun::SpeedrunCreateDisconfirmerResponse;
use anki_proto::speedrun::SpeedrunValidateDisconfirmerRequest;
use anki_proto::speedrun::SpeedrunValidateDisconfirmerResponse;

use super::textutil::containment;
use super::textutil::token_set;
use crate::prelude::*;
use crate::text::strip_html;

pub(crate) const DISCONFIRMER_NOTETYPE_NAME: &str = "Speedrun Disconfirmer";
pub(crate) const PRETEST_NOTETYPE_NAME: &str = "Speedrun Pretest";
/// Marks a Speedrun Disconfirmer note.
pub(crate) const NOTE_TAG: &str = "speedrun_disconfirmer";
/// Marks a held-out transfer/perturbed item (drives the fading ladder's transfer
/// gate).
pub(crate) const TRANSFER_TAG: &str = "speedrun_transfer";
/// Marks an original card that now has a disconfirmer (so it isn't prompted
/// again).
pub(crate) const DISCONFIRMED_TAG: &str = "speedrun_disconfirmed";
/// The disconfirmer was authored with an AI hint (for the anti-crutch monitor).
pub(crate) const ASSISTED_TAG: &str = "speedrun_assisted";
/// The deck new disconfirmer cards land in.
pub(crate) const DISCONFIRMER_DECK: &str = "Speedrun Disconfirmers";
/// The "::" tag prefix that scopes MCAT cards.
pub(crate) const TAG_PREFIX: &str = "MCAT";

/// Cap the title segment so tags stay readable; the code segment is the key.
const MAX_TITLE_TAG_LEN: usize = 48;

/// A content-category title turned into one tag segment: tag-search metachars and
/// punctuation dropped, whitespace -> underscores, capped at a word boundary.
/// Mirrors `_tag_safe_title` in `pylib/anki/speedrun/disconfirmer.py`.
fn tag_safe_title(title: &str) -> String {
    let cleaned: String = title
        .chars()
        .filter(|c| !"\"'*:,()&/".contains(*c))
        .collect();
    // collapse any run of whitespace or underscores into a single underscore
    let mut out = String::new();
    let mut prev_us = false;
    for c in cleaned.chars() {
        if c.is_whitespace() || c == '_' {
            if !prev_us {
                out.push('_');
                prev_us = true;
            }
        } else {
            out.push(c);
            prev_us = false;
        }
    }
    let mut result = out.trim_matches('_').to_string();
    if result.chars().count() > MAX_TITLE_TAG_LEN {
        let cut: String = result.chars().take(MAX_TITLE_TAG_LEN).collect();
        result = match cut.rsplit_once('_') {
            Some((head, _)) => head.to_string(),
            None => cut,
        };
    }
    result
}

/// The readable MCAT tag for a content-category code: `MCAT::<code>::<Title>` (or
/// just `MCAT::<code>` when no title is known). The code stays its own `::`
/// segment so coverage still maps it. Mirrors `topic_tag` in the Python.
pub(crate) fn topic_tag(code: &str) -> String {
    let base = format!("{TAG_PREFIX}::{code}");
    match super::outline::title_for_code(code) {
        Some(title) => {
            let safe = tag_safe_title(title);
            if safe.is_empty() {
                base
            } else {
                format!("{base}::{safe}")
            }
        }
        None => base,
    }
}

const DISCONFIRMER_FIELDS: &[&str] = &[
    "Principle",
    "OriginalCoverStory",
    "SwappedCoverStory",
    "Answer",
    "Trap",
    "Disconfirmer",
    "BoundaryCase",
    "Provenance",
    "ConceptFamily",
];

const DISCONFIRMER_FRONT: &str = r##"<div class="sr-card">
  <div class="sr-q">{{SwappedCoverStory}}</div>
  <div class="sr-prompt">What one fact would flip this answer?</div>
</div>
"##;

const DISCONFIRMER_BACK: &str = r##"{{FrontSide}}
<hr id="answer">
<div class="sr-card">
  <div class="sr-a"><span class="lbl">Answer</span>{{Answer}}</div>
  {{#Disconfirmer}}<div class="sr-disc"><span class="lbl">Disconfirmer - what flips it</span>{{Disconfirmer}}</div>{{/Disconfirmer}}
  {{#Principle}}<div class="sr-row"><span class="lbl">Principle</span>{{Principle}}</div>{{/Principle}}
  {{#Trap}}<div class="sr-row"><span class="lbl">Trap</span>{{Trap}}</div>{{/Trap}}
  {{#BoundaryCase}}<div class="sr-row"><span class="lbl">Boundary case</span>{{BoundaryCase}}</div>{{/BoundaryCase}}
  {{#OriginalCoverStory}}<div class="sr-perturb"><span class="lbl">Surface perturbation</span>{{OriginalCoverStory}} &rarr; {{SwappedCoverStory}}</div>{{/OriginalCoverStory}}
  {{#Provenance}}<div class="sr-prov">Source: {{Provenance}}</div>{{/Provenance}}
</div>
"##;

const DISCONFIRMER_CSS: &str = r##".card { font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, Arial; color: inherit; }
.sr-card { max-width: 640px; margin: 0 auto; text-align: left; }
.sr-q { font-size: 20px; font-weight: 600; margin-bottom: 14px; }
.sr-prompt { font-style: italic; opacity: .75; }
.sr-a { font-size: 18px; margin: 8px 0; }
.sr-disc { background: rgba(255,180,84,.15); border-left: 3px solid #ffb454; padding: 8px 10px; border-radius: 6px; margin: 10px 0; }
.sr-row { margin: 6px 0; }
.sr-perturb { margin: 8px 0; opacity: .85; }
.sr-prov { opacity: .6; font-size: 12px; margin-top: 10px; }
.lbl { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .4px; opacity: .6; }
"##;

const PRETEST_FIELDS: &[&str] = &["Question", "Answer", "Explanation", "Source", "ConceptFamily"];

const PRETEST_FRONT: &str = r##"<div class="sr-card">
  <div class="sr-q">{{Question}}</div>
  <div class="sr-prompt">Commit your best guess, then reveal.</div>
  {{type:Answer}}
</div>
"##;

const PRETEST_BACK: &str = r##"{{FrontSide}}
<hr id="answer">
<div class="sr-card">
  <div class="sr-a"><span class="lbl">Answer</span>{{type:Answer}}</div>
  {{#Explanation}}<div class="sr-why"><span class="lbl">Why</span>{{Explanation}}</div>{{/Explanation}}
  {{#Source}}<div class="sr-prov">Source: {{Source}}</div>{{/Source}}
</div>
"##;

const PRETEST_CSS: &str = r##".card { font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, Arial; color: inherit; }
.sr-card { max-width: 640px; margin: 0 auto; text-align: left; }
.sr-q { font-size: 20px; font-weight: 600; margin-bottom: 10px; }
.sr-prompt { font-style: italic; opacity: .75; margin-bottom: 12px; }
.sr-a { font-size: 18px; margin: 8px 0; }
.sr-why { background: rgba(84,160,255,.15); border-left: 3px solid #54a0ff; padding: 8px 10px; border-radius: 6px; margin: 10px 0; }
.sr-prov { opacity: .6; font-size: 12px; margin-top: 10px; }
.lbl { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .4px; opacity: .6; }
"##;

// -- Speedrun Performance Item (the Qbank / memory->performance bridge) --------
//
// A held-out, exam-style multiple-choice item. The whole answering experience is
// in the card template (SPOV 1: cross-platform review tier). The student taps an
// option; the front records the pick + latency in `window.srPerf`; the back reveals
// the correct answer + rationale and a verdict that tells the student which grade to
// press. The durable, natively-synced outcome is the review grade (revlog): a passing
// grade (Good/Easy) = correct. Field names match the testdeck fixture so an imported
// `.apkg` maps onto this one note type.

pub(crate) const PERF_NOTETYPE_NAME: &str = "Speedrun Performance Item";

const PERF_FIELDS: &[&str] = &[
    "ConceptId",
    "Stem",
    "OptionA",
    "OptionB",
    "OptionC",
    "OptionD",
    "Correct",
    "Rationale",
    "Variant",
];

const PERF_FRONT: &str = r##"<div class="sr-card sr-perf">
  <div class="sr-stem">{{Stem}}</div>
  <div class="sr-opts">
    <button type="button" class="sr-opt" data-opt="A">A. {{OptionA}}</button>
    <button type="button" class="sr-opt" data-opt="B">B. {{OptionB}}</button>
    <button type="button" class="sr-opt" data-opt="C">C. {{OptionC}}</button>
    <button type="button" class="sr-opt" data-opt="D">D. {{OptionD}}</button>
  </div>
  <div class="sr-prompt">Pick an option, then reveal.</div>
</div>
<script>
(function(){
  var start = Date.now();
  window.srPerf = { pick: null, ms: 0 };
  var opts = document.querySelectorAll('.sr-opt');
  for (var i = 0; i < opts.length; i++) {
    opts[i].addEventListener('click', function(ev){
      window.srPerf.pick = ev.currentTarget.getAttribute('data-opt');
      window.srPerf.ms = Date.now() - start;
      for (var j = 0; j < opts.length; j++) { opts[j].classList.remove('sel'); }
      ev.currentTarget.classList.add('sel');
    });
  }
})();
</script>
"##;

const PERF_BACK: &str = r##"{{FrontSide}}
<hr id="answer">
<div class="sr-card sr-perf">
  <div class="sr-a"><span class="lbl">Correct answer</span>{{Correct}}</div>
  {{#Rationale}}<div class="sr-why"><span class="lbl">Why</span>{{Rationale}}</div>{{/Rationale}}
  <div id="sr-verdict" class="sr-verdict"></div>
</div>
<script>
(function(){
  var correct = ("{{Correct}}" || "").trim().charAt(0).toUpperCase();
  var pick = (window.srPerf && window.srPerf.pick) || null;
  var el = document.getElementById("sr-verdict");
  if (!el) return;
  if (!pick) { el.textContent = "No option picked - grade honestly."; return; }
  var ok = pick === correct;
  el.textContent = ok
    ? ("You picked " + pick + " - correct. Press Good.")
    : ("You picked " + pick + " - incorrect (answer: " + correct + "). Press Again.");
  el.className = "sr-verdict " + (ok ? "ok" : "no");
})();
</script>
"##;

const PERF_CSS: &str = r##".card { font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, Arial; color: inherit; }
.sr-card { max-width: 640px; margin: 0 auto; text-align: left; }
.sr-stem { font-size: 18px; font-weight: 600; margin-bottom: 14px; }
.sr-opts { display: grid; gap: 8px; margin-bottom: 12px; }
.sr-opt { text-align: left; padding: 10px 12px; border: 1px solid rgba(127,127,127,.4); border-radius: 8px; background: rgba(127,127,127,.06); color: inherit; font: inherit; cursor: pointer; }
.sr-opt.sel { border-color: #54a0ff; background: rgba(84,160,255,.15); }
.sr-prompt { font-style: italic; opacity: .75; }
.sr-a { font-size: 18px; margin: 8px 0; }
.sr-why { background: rgba(84,160,255,.12); border-left: 3px solid #54a0ff; padding: 8px 10px; border-radius: 6px; margin: 10px 0; }
.sr-verdict { margin-top: 10px; font-weight: 600; }
.sr-verdict.ok { color: #2ea37a; }
.sr-verdict.no { color: #d9534f; }
.lbl { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .4px; opacity: .6; }
"##;

/// Build (but do not add) a Speedrun note type from its field list, template and
/// css, with the given sort field.
fn build_notetype(
    name: &str,
    fields: &[&str],
    qfmt: &str,
    afmt: &str,
    css: &str,
    sort_field: &str,
) -> Notetype {
    let mut nt = Notetype {
        name: name.to_string(),
        ..Default::default()
    };
    for field in fields {
        nt.add_field(*field);
    }
    nt.add_template("Card 1", qfmt, afmt);
    nt.config.css = css.to_string();
    nt.config.sort_field_idx = fields.iter().position(|f| f == &sort_field).unwrap_or(0) as u32;
    nt
}

fn disconfirmer_notetype() -> Notetype {
    build_notetype(
        DISCONFIRMER_NOTETYPE_NAME,
        DISCONFIRMER_FIELDS,
        DISCONFIRMER_FRONT,
        DISCONFIRMER_BACK,
        DISCONFIRMER_CSS,
        "SwappedCoverStory",
    )
}

fn pretest_notetype() -> Notetype {
    build_notetype(
        PRETEST_NOTETYPE_NAME,
        PRETEST_FIELDS,
        PRETEST_FRONT,
        PRETEST_BACK,
        PRETEST_CSS,
        "Question",
    )
}

fn perf_notetype() -> Notetype {
    build_notetype(
        PERF_NOTETYPE_NAME,
        PERF_FIELDS,
        PERF_FRONT,
        PERF_BACK,
        PERF_CSS,
        "Stem",
    )
}

/// The value of a note's named field, if the note type has such a field.
fn named_field<'a>(note: &'a Note, nt: &Notetype, name: &str) -> Option<&'a str> {
    nt.fields
        .iter()
        .position(|f| f.name == name)
        .and_then(|idx| note.fields().get(idx))
        .map(String::as_str)
}

fn set_named_field(note: &mut Note, nt: &Notetype, name: &str, value: &str) {
    if let Some(idx) = nt.fields.iter().position(|f| f.name == name) {
        let _ = note.set_field(idx, value);
    }
}

/// The concept family for a note: its `ConceptFamily` field, else the suffix of
/// its first `MCAT::` tag. Mirrors `family_from_note` in the Python (the raw
/// suffix, used to tag/label the new card - not the normalised cc code).
pub(crate) fn family_from_note(note: &Note, nt: &Notetype) -> Option<String> {
    if let Some(value) = named_field(note, nt, "ConceptFamily") {
        let value = value.trim();
        if !value.is_empty() {
            return Some(value.to_string());
        }
    }
    let prefix = format!("{TAG_PREFIX}::");
    note.tags
        .iter()
        .find_map(|tag| tag.strip_prefix(&prefix).map(str::to_string))
}

/// Validate a student-authored disconfirmer. Returns a revise message, or "" if
/// acceptable. Mirrors `validate_disconfirmer` in the Python: rejects a blank
/// disconfirmer and one that merely restates the answer (a nudge, not a grader).
pub(crate) fn validate_disconfirmer(text: &str, answer: &str) -> String {
    let stripped = text.trim();
    if stripped.is_empty() {
        return "The disconfirmer can't be empty - name the one fact that would flip the answer."
            .to_string();
    }
    let answer_tokens = token_set(answer);
    if answer_tokens.len() >= 2
        && containment(&answer_tokens, &token_set(stripped)) >= 0.9
    {
        return "This looks like it just restates the answer. Say what single fact, if true, \
                would make the answer change."
            .to_string();
    }
    String::new()
}

impl Collection {
    /// Add a Speedrun note type if one of that name is missing; return its id.
    /// Caller must be inside a transaction.
    fn ensure_speedrun_notetype_inner(&mut self, mut nt: Notetype) -> Result<NotetypeId> {
        if let Some(existing) = self.get_notetype_by_name(&nt.name)? {
            return Ok(existing.id);
        }
        let usn = self.usn()?;
        nt.set_modified(usn);
        self.add_notetype_inner(&mut nt, usn, true)?;
        Ok(nt.id)
    }

    /// Create the Speedrun Disconfirmer + Pretest + Performance Item note types if
    /// missing (idempotent). A single undoable step.
    pub fn speedrun_ensure_notetypes(&mut self) -> Result<()> {
        self.transact(Op::AddNotetype, |col| {
            col.ensure_speedrun_notetype_inner(disconfirmer_notetype())?;
            col.ensure_speedrun_notetype_inner(pretest_notetype())?;
            col.ensure_speedrun_notetype_inner(perf_notetype())?;
            Ok(())
        })?;
        Ok(())
    }

    /// Read-only: validate a disconfirmer ("" = ok).
    pub fn speedrun_validate_disconfirmer(
        &mut self,
        input: SpeedrunValidateDisconfirmerRequest,
    ) -> Result<SpeedrunValidateDisconfirmerResponse> {
        Ok(SpeedrunValidateDisconfirmerResponse {
            problem: validate_disconfirmer(&input.text, &input.answer),
        })
    }

    /// Turn a missed card into a linked Speedrun Disconfirmer note (the miss ->
    /// card loop). The missed card's front/back become the cover-story/answer;
    /// the new card lands in the dedicated deck, and the original note is tagged
    /// so it isn't prompted again. `assisted` records that an AI hint was used.
    ///
    /// A single undoable step: undo removes the new note and clears the original
    /// note's disconfirmed tag.
    pub fn speedrun_create_disconfirmer(
        &mut self,
        input: SpeedrunCreateDisconfirmerRequest,
    ) -> Result<SpeedrunCreateDisconfirmerResponse> {
        let cid = CardId(input.card_id);
        let card = self.storage.get_card(cid)?.or_not_found(cid)?;
        let source = self
            .storage
            .get_note(card.note_id)?
            .or_not_found(card.note_id)?;
        let source_nt = self
            .get_notetype(source.notetype_id)?
            .or_invalid("missing note type")?;

        let family = family_from_note(&source, &source_nt).unwrap_or_default();
        let front = source
            .fields()
            .first()
            .map(|f| strip_html(f).into_owned())
            .unwrap_or_default();
        let back = source
            .fields()
            .get(1)
            .map(|f| strip_html(f).into_owned())
            .unwrap_or_default();
        let provenance = format!("from card {}", cid.0);

        // Ensure the disconfirmer note type exists (idempotent), then resolve id.
        let nt_id = match self.get_notetype_by_name(DISCONFIRMER_NOTETYPE_NAME)? {
            Some(nt) => nt.id,
            None => {
                self.speedrun_ensure_notetypes()?;
                self.get_notetype_by_name(DISCONFIRMER_NOTETYPE_NAME)?
                    .or_invalid("disconfirmer note type")?
                    .id
            }
        };
        // The dedicated deck is created outside the note transaction.
        let deck_id = self.get_or_create_normal_deck(DISCONFIRMER_DECK)?.id;

        let disconfirmer = input.disconfirmer;
        let principle = input.principle;
        let assisted = input.assisted;
        let source_id = source.id;

        let out = self.transact(Op::AddNote, |col| {
            let nt = col
                .get_notetype(nt_id)?
                .or_invalid("disconfirmer note type")?;
            let mut note = nt.new_note();
            set_named_field(&mut note, &nt, "SwappedCoverStory", &front);
            set_named_field(&mut note, &nt, "OriginalCoverStory", &front);
            set_named_field(&mut note, &nt, "Answer", &back);
            set_named_field(&mut note, &nt, "Disconfirmer", &disconfirmer);
            set_named_field(&mut note, &nt, "Principle", &principle);
            set_named_field(&mut note, &nt, "Provenance", &provenance);
            set_named_field(&mut note, &nt, "ConceptFamily", &family);

            let mut tags = vec![NOTE_TAG.to_string()];
            if !family.is_empty() {
                tags.push(topic_tag(&family));
            }
            if assisted {
                tags.push(ASSISTED_TAG.to_string());
            }
            note.tags = tags;
            col.add_note_inner(&mut note, deck_id)?;
            let new_id = note.id;

            // Tag the original so it isn't prompted for a disconfirmer again.
            let mut original = col.storage.get_note(source_id)?.or_not_found(source_id)?;
            if !original.tags.iter().any(|t| t == DISCONFIRMED_TAG) {
                original.tags.push(DISCONFIRMED_TAG.to_string());
                col.update_note_inner(&mut original)?;
            }
            Ok(new_id)
        })?;

        Ok(SpeedrunCreateDisconfirmerResponse {
            note_id: out.output.0,
        })
    }
}

#[cfg(test)]
mod test {
    use anki_proto::speedrun::SpeedrunCreateDisconfirmerRequest;
    use anki_proto::speedrun::SpeedrunValidateDisconfirmerRequest;

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

    #[test]
    fn ensure_notetypes_is_idempotent() {
        let mut col = Collection::new();
        assert!(col.get_notetype_by_name(DISCONFIRMER_NOTETYPE_NAME).unwrap().is_none());

        col.speedrun_ensure_notetypes().unwrap();
        let disc = col
            .get_notetype_by_name(DISCONFIRMER_NOTETYPE_NAME)
            .unwrap()
            .expect("disconfirmer note type created");
        let pretest = col
            .get_notetype_by_name(PRETEST_NOTETYPE_NAME)
            .unwrap()
            .expect("pretest note type created");
        assert_eq!(disc.fields.len(), DISCONFIRMER_FIELDS.len());
        assert_eq!(pretest.fields.len(), PRETEST_FIELDS.len());

        // Running again must not create duplicates or fail.
        col.speedrun_ensure_notetypes().unwrap();
        assert_eq!(
            col.get_notetype_by_name(DISCONFIRMER_NOTETYPE_NAME).unwrap().unwrap().id,
            disc.id
        );
    }

    #[test]
    fn validate_rejects_blank_and_restatement() {
        let mut col = Collection::new();
        // blank
        let res = col
            .speedrun_validate_disconfirmer(SpeedrunValidateDisconfirmerRequest {
                text: "   ".to_string(),
                answer: "the conjugate base dominates".to_string(),
            })
            .unwrap();
        assert!(res.problem.contains("can't be empty"));

        // restates the answer (all content words reappear)
        let res = col
            .speedrun_validate_disconfirmer(SpeedrunValidateDisconfirmerRequest {
                text: "the conjugate base dominates".to_string(),
                answer: "conjugate base dominates".to_string(),
            })
            .unwrap();
        assert!(res.problem.contains("restates the answer"));

        // a genuine disconfirmer -> ok ("")
        let res = col
            .speedrun_validate_disconfirmer(SpeedrunValidateDisconfirmerRequest {
                text: "If the pH dropped below the pKa, the protonated acid would dominate instead."
                    .to_string(),
                answer: "conjugate base dominates".to_string(),
            })
            .unwrap();
        assert_eq!(res.problem, "");
    }

    /// (e) create_disconfirmer builds a linked note and a single undo reverts it
    /// (transact/undo works, no corruption).
    #[test]
    fn create_disconfirmer_builds_note_and_undo_reverts() {
        let mut col = Collection::new();
        let cid = add_card(
            &mut col,
            "Why does raising the pH above the pKa shift the equilibrium?",
            "The conjugate base dominates.",
            &["MCAT::BioBiochem::1A::AminoAcids"],
        );
        let source_id = col.storage.get_card(cid).unwrap().unwrap().note_id;

        let res = col
            .speedrun_create_disconfirmer(SpeedrunCreateDisconfirmerRequest {
                card_id: cid.0,
                disconfirmer: "If the pH dropped back below the pKa, the acid form would dominate."
                    .to_string(),
                principle: "Henderson-Hasselbalch".to_string(),
                assisted: false,
            })
            .unwrap();
        assert_ne!(res.note_id, 0);

        // The new note exists, is a disconfirmer, and carries the family tag.
        let new_note = col.storage.get_note(NoteId(res.note_id)).unwrap().unwrap();
        assert!(new_note.tags.iter().any(|t| t == NOTE_TAG));
        assert!(new_note.tags.iter().any(|t| t == "MCAT::BioBiochem::1A::AminoAcids"));
        assert_eq!(
            named_field(
                &new_note,
                &col.get_notetype(new_note.notetype_id).unwrap().unwrap(),
                "Disconfirmer"
            )
            .unwrap(),
            "If the pH dropped back below the pKa, the acid form would dominate."
        );

        // The original is tagged so it won't be prompted again.
        let original = col.storage.get_note(source_id).unwrap().unwrap();
        assert!(original.tags.iter().any(|t| t == DISCONFIRMED_TAG));

        // A single undo removes the new note and clears the original's tag.
        col.undo().unwrap();
        assert!(col.storage.get_note(NoteId(res.note_id)).unwrap().is_none());
        let original = col.storage.get_note(source_id).unwrap().unwrap();
        assert!(!original.tags.iter().any(|t| t == DISCONFIRMED_TAG));
    }
}
