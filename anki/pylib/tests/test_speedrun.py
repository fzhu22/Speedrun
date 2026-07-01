# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Tests for the Speedrun concept knowledge graph (anki.speedrun)."""

from __future__ import annotations

from anki.speedrun import leakage_check, load_outline_graph
from anki.speedrun.models import (
    ConceptGraph,
    Edge,
    EdgeType,
    Node,
    NodeKind,
    Provenance,
    ValidationStatus,
)
from anki.speedrun.textutil import Document


# -- models -------------------------------------------------------------------


def test_part_of_is_ground_truth_and_feeds_readiness():
    e = Edge(src="cc:1A", dst="fc:1", type=EdgeType.PART_OF)
    assert e.status is ValidationStatus.GROUND_TRUTH and e.feeds_readiness


def test_readiness_edges_excludes_proposed():
    g = ConceptGraph()
    g.add_node(Node(id="c", kind=NodeKind.CARD, title="c"))
    g.add_node(Node(id="cc:1A", kind=NodeKind.CONTENT_CATEGORY, title="x"))
    g.add_edge(Edge(src="c", dst="cc:1A", type=EdgeType.TESTS, provenance=Provenance("llm")))
    assert g.edges(EdgeType.TESTS) and g.readiness_edges(EdgeType.TESTS) == []


# -- outline ------------------------------------------------------------------


def test_outline_spine_counts():
    g = load_outline_graph()
    assert len(g.nodes(NodeKind.SECTION)) == 4
    assert len(g.nodes(NodeKind.FOUNDATIONAL_CONCEPT)) == 10
    assert len(g.nodes(NodeKind.CONTENT_CATEGORY)) == 31
    assert len(g.edges(EdgeType.PART_OF)) == 41
    assert g.in_edges("sec:cars", EdgeType.PART_OF) == []  # CARS has no FCs


# -- leakage check ------------------------------------------------------------


def test_leakage_flags_verbatim_copy():
    corpus = [Document(id="d1", text="notes the mitochondria is the powerhouse of the cell producing atp end", source="n")]
    rep = leakage_check(corpus, [("t1", "the mitochondria is the powerhouse of the cell producing atp")], threshold=0.8)
    assert not rep.clean and rep.leaks[0][0] == "t1"


# -- fading ladder ------------------------------------------------------------


def test_estimate_rung_from_recall():
    from anki.speedrun import fading

    # Conservative: capped at L1, never seeds L0 from recall alone.
    assert fading.estimate_rung(None) is fading.Rung.L3
    assert fading.estimate_rung(0.3) is fading.Rung.L3
    assert fading.estimate_rung(0.6) is fading.Rung.L2
    assert fading.estimate_rung(0.8) is fading.Rung.L2
    assert fading.estimate_rung(0.95) is fading.Rung.L1
    assert fading.estimate_rung(1.0) is not fading.Rung.L0


def test_declarative_family_opts_out_of_ladder():
    from anki.speedrun import fading

    # current_rung is a read helper: declarative families report L1 without touching
    # the persisted per-family state (the advance/regress mutation lives in Rust now).
    fstate: dict = {}
    assert fading.current_rung(fstate, "1A", 0.95, declarative=True) is fading.Rung.L1
    assert fstate == {}


# -- disconfirmer validation --------------------------------------------------


def test_validate_disconfirmer_rejects_blank():
    from anki.speedrun.disconfirmer import validate_disconfirmer

    assert validate_disconfirmer("", "the mitochondria") is not None
    assert validate_disconfirmer("   ", "x") is not None


def test_validate_disconfirmer_rejects_restatement():
    from anki.speedrun.disconfirmer import validate_disconfirmer

    msg = validate_disconfirmer(
        "oxidative phosphorylation produced ATP",
        "ATP produced by oxidative phosphorylation",
    )
    assert msg is not None


def test_validate_disconfirmer_accepts_a_real_flip():
    from anki.speedrun.disconfirmer import validate_disconfirmer

    assert (
        validate_disconfirmer(
            "if the pH rose above the pKa the conjugate base would dominate",
            "they are equal at the pKa",
        )
        is None
    )


# -- the note type (needs the backend) ---------------------------------------


def test_disconfirmer_notetype_and_render():
    from tests.shared import getEmptyCol

    from anki.speedrun.disconfirmer import NOTETYPE_NAME, build_note, ensure_notetype

    col = getEmptyCol()
    try:
        nt1 = ensure_notetype(col)
        nt2 = ensure_notetype(col)  # idempotent
        assert nt1["id"] == nt2["id"]
        names = col.models.field_names(nt1)
        for field in ("Principle", "SwappedCoverStory", "Answer", "Disconfirmer", "ConceptFamily"):
            assert field in names

        deck_id = col.decks.id("Default")
        nid = build_note(
            col,
            fields={
                "SwappedCoverStory": "A reworded enzyme kinetics question",
                "Answer": "Vmax is unchanged",
                "Disconfirmer": "if the inhibitor were competitive, Km would rise",
                "Principle": "distinguish inhibition types",
            },
            family="1A",
            deck_id=deck_id,
            transfer_item=True,
        )
        note = col.get_note(nid)
        assert "MCAT::1A" in note.tags
        assert "speedrun_disconfirmer" in note.tags
        assert "speedrun_transfer" in note.tags

        card = note.cards()[0]
        question = card.question()
        answer = card.answer()
        assert "reworded enzyme kinetics" in question
        assert "flip" in question.lower()
        assert "Vmax is unchanged" in answer
        assert "competitive" in answer  # disconfirmer rendered on the back
    finally:
        col.close()


# -- sample content -----------------------------------------------------------


def test_sample_content_is_well_formed():
    from anki.speedrun.aamc_outline import load_outline_graph
    from anki.speedrun.sample_content import (
        DISCONFIRMER_SEED,
        SAMPLE_CARDS,
        total_sample_cards,
    )

    valid = {
        n.id.split(":")[-1]
        for n in load_outline_graph().nodes()
        if n.id.startswith("cc:")
    }
    assert total_sample_cards() >= 80
    for code, qas in SAMPLE_CARDS.items():
        assert code in valid, f"{code} is not an AAMC content category"
        for front, back in qas:
            assert front.strip() and back.strip()
    for spec in DISCONFIRMER_SEED:
        assert spec["family"] in valid
        assert spec["fields"]["Disconfirmer"].strip()
        assert spec["fields"]["Answer"].strip()


# -- seeding (needs the backend) ---------------------------------------------


def test_seeding_is_idempotent():
    from tests.shared import getEmptyCol

    from anki.speedrun.sample_content import (
        DISCONFIRMER_SEED,
        PRETEST_SEED,
        total_sample_cards,
    )
    from anki.speedrun.seeding import (
        PRETEST_DECK,
        SAMPLE_DECK,
        seed_disconfirmer_deck,
        seed_pretest_deck,
        seed_sample_deck,
    )

    col = getEmptyCol()
    try:
        assert seed_sample_deck(col) == total_sample_cards()
        assert seed_sample_deck(col) == 0  # idempotent
        assert col.decks.by_name(SAMPLE_DECK) is not None

        assert seed_disconfirmer_deck(col) == len(DISCONFIRMER_SEED)
        assert seed_disconfirmer_deck(col) == 0  # idempotent
        assert col.find_notes("tag:speedrun_transfer")  # transfer items tagged

        assert seed_pretest_deck(col) == len(PRETEST_SEED)
        assert seed_pretest_deck(col) == 0  # idempotent
        assert col.decks.by_name(PRETEST_DECK) is not None
    finally:
        col.close()


def test_seed_all_returns_three_counts():
    from tests.shared import getEmptyCol

    from anki.speedrun.seeding import seed_all

    col = getEmptyCol()
    try:
        counts = seed_all(col)
        assert len(counts) == 3 and all(c > 0 for c in counts)
        assert seed_all(col) == (0, 0, 0)  # idempotent
    finally:
        col.close()


# -- pretest-first (SPOV 13) -------------------------------------------------


def test_pretest_notetype_and_render():
    from tests.shared import getEmptyCol

    from anki.speedrun import pretest

    col = getEmptyCol()
    try:
        nt = pretest.ensure_notetype(col)
        assert pretest.ensure_notetype(col)["id"] == nt["id"]  # idempotent
        assert col.models.field_names(nt) == pretest.FIELDS

        deck = col.decks.id("Default")
        nid = pretest.build_note(
            col,
            fields={
                "Question": "A cell with no O2 still nets 2 ATP - which pathway?",
                "Answer": "Glycolysis",
                "Explanation": "Glycolysis is oxygen-independent.",
                "Source": "[Sample]",
            },
            family="1D",
            deck_id=deck,
        )
        card = col.get_note(nid).cards()[0]
        front, back = card.question(), card.answer()
        assert "which pathway" in front.lower()
        # The reviewer JS renders [[type:Answer]] into the input box / diff; the backend
        # render leaves the marker, which is enough to prove the type-in is wired.
        assert "[[type:Answer]]" in front  # forced typed guess on the front
        assert "[[type:Answer]]" in back  # typed-vs-correct comparison on reveal
        assert "oxygen-independent" in back  # mandatory in-session feedback (Explanation)
        assert "[Sample]" in back  # source/provenance shown
        assert "MCAT::1D" in col.get_note(nid).tags
    finally:
        col.close()


def test_pretest_toggle_off_seeds_basic():
    from tests.shared import getEmptyCol

    from anki.speedrun import pretest
    from anki.speedrun.sample_content import PRETEST_SEED
    from anki.speedrun.seeding import seed_pretest_deck

    col = getEmptyCol()
    try:
        assert pretest.pretest_enabled(col) is True  # default on
        pretest.set_pretest_enabled(col, False)
        assert pretest.pretest_enabled(col) is False

        assert seed_pretest_deck(col) == len(PRETEST_SEED)
        # With the feature off, content is plain Basic (the section-8 ablation arm).
        assert not col.find_notes(f'note:"{pretest.NOTETYPE_NAME}"')
        assert col.find_notes("tag:speedrun_pretest_seed")
    finally:
        col.close()


# -- AI: card-type classifier + gating ---------------------------------------


def test_heuristic_classify():
    from anki.speedrun.cardtype import CardType, heuristic_classify

    assert heuristic_classify("How many amino acids are standard?", "20") is CardType.DECLARATIVE
    assert heuristic_classify("What is the start codon?", "AUG") is CardType.DECLARATIVE
    assert heuristic_classify("Why is glycolysis oxygen-independent?", "It is cytoplasmic") is CardType.APPLICATION
    assert heuristic_classify("If pH rises above the pI, what is the net charge?", "Negative") is CardType.APPLICATION


def test_should_prompt_disconfirmer():
    from anki.speedrun.cardtype import CardType, should_prompt_disconfirmer

    assert should_prompt_disconfirmer(CardType.APPLICATION, 1) is True
    assert should_prompt_disconfirmer(CardType.APPLICATION, 2) is True
    assert should_prompt_disconfirmer(CardType.DECLARATIVE, 1) is False  # facts get none
    assert should_prompt_disconfirmer(CardType.APPLICATION, 3) is False  # not a miss
    assert should_prompt_disconfirmer(CardType.APPLICATION, 2, trigger="again") is False


def test_struggle_override_prompts_on_repeated_miss():
    from anki.speedrun.cardtype import (
        STRUGGLE_THRESHOLD,
        CardType,
        should_prompt_disconfirmer,
    )

    # A first miss of a pure fact is left alone (just re-study it).
    assert should_prompt_disconfirmer(CardType.DECLARATIVE, 1, misses=1) is False
    # But once the student clearly keeps missing it, prompt regardless of type.
    assert should_prompt_disconfirmer(CardType.DECLARATIVE, 1, misses=STRUGGLE_THRESHOLD) is True
    assert should_prompt_disconfirmer(CardType.DECLARATIVE, 2, misses=3) is True
    # Struggle only counts on an actual miss, never on Good/Easy.
    assert should_prompt_disconfirmer(CardType.DECLARATIVE, 3, misses=9) is False
    # A custom (higher) threshold defers the override.
    assert (
        should_prompt_disconfirmer(CardType.DECLARATIVE, 1, misses=2, struggle_threshold=3)
        is False
    )


# -- AI: ops fall back when off, use the client when present ------------------


class _FakeClient:
    model = "fake-model"

    def __init__(self, reply: str) -> None:
        self._reply = reply

    def complete(self, system: str, user: str) -> str:
        return self._reply


def test_classify_fallback_and_client():
    from anki.speedrun import ai
    from anki.speedrun.cardtype import CardType

    assert ai.classify_card_type(None, "How many bones?", "206") is CardType.DECLARATIVE
    assert ai.classify_card_type(_FakeClient("application"), "x", "y") is CardType.APPLICATION
    # unparseable reply -> heuristic fallback
    assert ai.classify_card_type(_FakeClient("???"), "How many bones?", "206") is CardType.DECLARATIVE


def test_hint_fallback_and_client():
    from anki.speedrun import ai

    text, prov = ai.disconfirmer_hint(None, "q", "a")
    assert text and prov.source == "template"
    text2, prov2 = ai.disconfirmer_hint(_FakeClient("What assumption breaks here?"), "q", "a")
    assert "assumption" in text2.lower()
    assert prov2.source.startswith("AI:")


def test_openai_client_builds_request(monkeypatch):
    import requests

    from anki.speedrun import ai

    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "application"}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json)
        return _Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    client = ai.OpenAICompatibleClient(base_url="https://x/v1", model="m", api_key="k")
    assert client.complete("sys", "user") == "application"
    assert captured["url"].endswith("/chat/completions")
    assert captured["json"]["model"] == "m"
    assert captured["headers"]["Authorization"] == "Bearer k"


# -- AI: held-out eval (beat the baseline + cutoff + leakage) -----------------


def test_ai_eval_compare_cutoff_leakage():
    from anki.speedrun import ai, ai_eval
    from anki.speedrun.cardtype import heuristic_classify

    base = ai_eval.evaluate(heuristic_classify)
    assert base["accuracy"] >= ai_eval.CUTOFF  # the baseline clears the bar

    gold = {(q, a): t for q, a, t in ai_eval.CARD_TYPE_GOLD}
    perfect = lambda q, a: gold[(q, a)]  # noqa: E731 - a perfect stand-in "AI"
    res = ai_eval.compare(perfect, heuristic_classify)
    assert res["ai"] == 1.0
    assert res["ai"] > res["heuristic"]  # beats the baseline
    assert ai_eval.passes_cutoff(res["ai"])
    assert ai_eval.fewshot_leakage(ai.FEWSHOT_EXAMPLES).clean


# -- AI: anti-crutch kill-switch ---------------------------------------------


def test_anticrutch_killswitch():
    from anki.speedrun import anticrutch

    st = anticrutch.empty_state()
    for _ in range(8):
        anticrutch.record_outcome(st, assisted=False, correct=True)
    for _ in range(6):
        anticrutch.record_outcome(st, assisted=True, correct=False)
    for _ in range(2):
        anticrutch.record_outcome(st, assisted=True, correct=True)
    assert anticrutch.crutch_signature(st) is True
    assert anticrutch.should_offer_ai_hints(st) is False


def test_anticrutch_needs_enough_data():
    from anki.speedrun import anticrutch

    st = anticrutch.empty_state()
    anticrutch.record_outcome(st, assisted=True, correct=True)
    assert anticrutch.should_offer_ai_hints(st) is True  # too little data to kill


# -- card-type cache + auto-classify -> gating -------------------------------


def test_cardcache_roundtrip_and_gating():
    from tests.shared import getEmptyCol

    from anki.speedrun import ai, cardcache
    from anki.speedrun.cardtype import CardType, should_prompt_disconfirmer

    col = getEmptyCol()
    try:
        basic = col.models.by_name("Basic")
        deck = col.decks.id("Default")

        n1 = col.new_note(basic)  # application
        n1["Front"] = "Why does glycolysis not require oxygen?"
        n1["Back"] = "It occurs in the cytoplasm without the ETC"
        n1.tags = ["MCAT::1D"]
        col.add_note(n1, deck)

        n2 = col.new_note(basic)  # declarative fact
        n2["Front"] = "How many amino acids are standard?"
        n2["Back"] = "20"
        n2.tags = ["MCAT::1A"]
        col.add_note(n2, deck)

        assert cardcache.cached_card_type(col.get_note(n1.id)) is None

        search = "tag:MCAT::* -tag:speedrun_ctype::*"
        items = cardcache.uncached_items(col, search, 60)
        assert len(items) == 2

        # classify (AI off -> heuristic) and cache
        for nid, q, a in items:
            cardcache.set_cached_card_type(col, col.get_note(nid), ai.classify_card_type(None, q, a))

        assert cardcache.uncached_items(col, search, 60) == []  # all cached now

        t1 = cardcache.cached_card_type(col.get_note(n1.id))
        t2 = cardcache.cached_card_type(col.get_note(n2.id))
        assert t1 is CardType.APPLICATION
        assert t2 is CardType.DECLARATIVE
        assert should_prompt_disconfirmer(t1, 1) is True  # application miss -> prompt
        assert should_prompt_disconfirmer(t2, 1) is False  # fact -> no prompt
    finally:
        col.close()
