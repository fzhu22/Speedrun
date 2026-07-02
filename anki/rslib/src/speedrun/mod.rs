// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Speedrun: shared, read-only backend for the MCAT readiness dashboard.
//!
//! The data behind the dashboard - coverage over the AAMC outline, per-section
//! memory, the three (never-blended) scores, and the prerequisite-aware study
//! plan - is computed once here in the shared engine so the desktop and
//! AnkiDroid render an identical dashboard. See `dashboard.rs` for the entry
//! point (`Collection::speedrun_dashboard`) and the honesty rules it upholds.

mod cardtype;
mod coverage;
mod dashboard;
mod disconfirmer;
mod fading;
mod outline;
mod performance;
mod planning;
mod service;
mod textutil;
