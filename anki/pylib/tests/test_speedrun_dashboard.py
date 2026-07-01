# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: Python-calls-Rust test for the readiness dashboard backend query."""

from tests.shared import getEmptyCol


def test_speedrun_dashboard():
    col = getEmptyCol()

    for tag in ["MCAT::BioBiochem::1A", "MCAT::ChemPhys::5E", "MCAT::PsychSoc::6A"]:
        note = col.newNote()
        note["Front"] = tag
        note["Back"] = "answer"
        note.tags = [tag]
        col.addNote(note)

    res = col.speedrun_dashboard()

    # overall coverage is an honest fraction, and the outline totals are stable
    assert 0.0 <= res.overall_coverage <= 1.0
    assert res.total_leaves == 31
    assert res.covered_leaves == 3

    # the three content sections are present; CARS has no content-category spine
    abbrevs = [s.abbrev for s in res.sections]
    assert abbrevs == ["Bio/Biochem", "Chem/Phys", "Psych/Soc"]

    # Memory abstains on a brand-new deck (nothing reviewed yet)
    for s in res.sections:
        assert not s.HasField("memory")

    # Performance always abstains for now (no exam-style items yet)
    assert res.performance_status == "insufficient data - no exam-style items yet"

    # Readiness abstains on this tiny dataset, with an explicit, non-empty reason
    assert not res.readiness_allowed
    assert res.readiness_status
    assert res.readiness_status != "allowed"

    # A prerequisite-aware plan is produced, each with a valid fading rung badge
    assert res.plan
    for item in res.plan:
        assert item.rung in {"L3", "L2", "L1", "L0"}

    col.close()
