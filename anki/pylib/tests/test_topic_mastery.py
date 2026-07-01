# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun: Python-calls-Rust test for the per-topic mastery backend query."""

from tests.shared import getEmptyCol


def test_topic_mastery():
    col = getEmptyCol()

    note = col.newNote()
    note["Front"] = "one"
    note["Back"] = "two"
    note.tags = ["MCAT::Bio::Enzymes"]
    col.addNote(note)

    untagged = col.newNote()
    untagged["Front"] = "three"
    untagged["Back"] = "four"
    col.addNote(untagged)

    res = col.topic_mastery()
    assert res.untagged_cards == 1
    topics = {t.tag: t for t in res.topics}
    assert set(topics) == {"MCAT::Bio::Enzymes"}
    leaf = topics["MCAT::Bio::Enzymes"]
    assert leaf.total_cards == 1
    # a brand-new card: nothing reviewed or mastered, and the average abstains
    assert leaf.reviewed_cards == 0
    assert leaf.mastered_cards == 0
    assert not leaf.HasField("average_recall")

    # hierarchy roll-up makes the parent topics report the descendant's card
    rolled = {t.tag: t for t in col.topic_mastery(include_descendants=True).topics}
    assert rolled["MCAT"].total_cards == 1
    assert rolled["MCAT::Bio"].total_cards == 1
    assert rolled["MCAT::Bio::Enzymes"].total_cards == 1

    col.close()
