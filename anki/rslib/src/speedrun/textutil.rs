// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Tiny, dependency-free text helpers for the Speedrun disconfirmer validator.
//!
//! Rust port of the subset of `pylib/anki/speedrun/textutil.py` used by
//! `validate_disconfirmer`: lowercase alphanumeric tokenisation (dropping short
//! and stop-words) and an asymmetric containment ratio. Deliberately simple and
//! deterministic - no embedding model or network access (the AI-off path).

use std::collections::HashSet;
use std::sync::LazyLock;

use regex::Regex;

/// Lowercase alphanumeric runs, matching Python's `_TOKEN_RE = r"[a-z0-9]+"`.
static TOKEN_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"[a-z0-9]+").unwrap());

/// Words dropped from token sets so validation focuses on content words. Mirrors
/// `_STOPWORDS` in the Python `textutil`.
static STOPWORDS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    "the a an and or of to in on for with within from into by as is are be that this \
     these those their its his her how ways way and/or main groups single"
        .split_whitespace()
        .collect()
});

/// The set of content tokens in `text`: lowercased `[a-z0-9]+` runs longer than
/// two characters that are not stop-words.
pub(crate) fn token_set(text: &str) -> HashSet<String> {
    let lower = text.to_lowercase();
    TOKEN_RE
        .find_iter(&lower)
        .map(|m| m.as_str())
        .filter(|t| t.len() > 2 && !STOPWORDS.contains(t))
        .map(str::to_string)
        .collect()
}

/// Fraction of `needle` tokens present in `haystack` (asymmetric; 0 when
/// `needle` is empty).
pub(crate) fn containment(needle: &HashSet<String>, haystack: &HashSet<String>) -> f32 {
    if needle.is_empty() {
        return 0.0;
    }
    let shared = needle.iter().filter(|t| haystack.contains(*t)).count();
    shared as f32 / needle.len() as f32
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn tokenises_and_drops_short_and_stopwords() {
        let toks = token_set("The pH is above the pKa value");
        // "the"/"is" are stop-words; "ph" is too short (<=2). "pka" is kept.
        assert!(toks.contains("above"));
        assert!(toks.contains("value"));
        assert!(toks.contains("pka"));
        assert!(!toks.contains("the"));
        assert!(!toks.contains("is"));
        assert!(!toks.contains("ph"));
    }

    #[test]
    fn containment_is_asymmetric() {
        let a = token_set("amino acid side chain");
        let b = token_set("the amino acid side chain determines folding");
        // every content token of a appears in b
        assert!((containment(&a, &b) - 1.0).abs() < 1e-6);
        // but not the reverse (b has "determines"/"folding" absent from a)
        assert!(containment(&b, &a) < 1.0);
        // empty needle -> 0
        assert_eq!(containment(&HashSet::new(), &b), 0.0);
    }
}
