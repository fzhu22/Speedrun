"""Import the AAMC content outline as the ground-truth graph spine (PRD Section 8.1).

The outline is embedded as Python data (``OUTLINE``) - structure only, no fabricated
exam weights - so it ships with the ``anki`` package without any data-file packaging.
:func:`load_outline_graph` turns it into nodes (``section`` / ``foundational_concept`` /
``content_category``) joined by ``part_of`` edges. Everything here is ground truth: it
is *imported*, never inferred, so it does not trip the "no auto-clustered concept
clusters" anti-pattern.

Source: AAMC - "What's on the MCAT Exam?" content outline
https://students-residents.aamc.org/whats-mcat-exam/whats-mcat-exam
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict

from .models import ConceptGraph, Edge, EdgeType, Node, NodeKind, Provenance

_SPINE_SOURCE = "AAMC content outline"

#: Structure of the MCAT outline (sections -> foundational concepts -> content
#: categories). Titles are the official AAMC wording; no exam weights are encoded
#: (weights are a tunable planning input, not fabricated here).
OUTLINE: Dict = {
    "source": _SPINE_SOURCE,
    "url": "https://students-residents.aamc.org/whats-mcat-exam/whats-mcat-exam",
    "scale": {"total": [472, 528], "section": [118, 132]},
    "sections": [
        {
            "id": "sec:bbls",
            "abbrev": "Bio/Biochem",
            "title": "Biological and Biochemical Foundations of Living Systems",
            "foundational_concepts": [
                {
                    "id": "fc:1",
                    "title": "Biomolecules have unique properties that determine how they contribute to the structure and function of cells, and how they participate in the processes necessary to maintain life.",
                    "content_categories": [
                        {"id": "cc:1A", "title": "Structure and function of proteins and their constituent amino acids"},
                        {"id": "cc:1B", "title": "Transmission of genetic information from the gene to the protein"},
                        {"id": "cc:1C", "title": "Transmission of heritable information from generation to generation and the processes that increase genetic diversity"},
                        {"id": "cc:1D", "title": "Principles of bioenergetics and fuel molecule metabolism"},
                    ],
                },
                {
                    "id": "fc:2",
                    "title": "Highly organized assemblies of molecules, cells, and organs interact to carry out the functions of living organisms.",
                    "content_categories": [
                        {"id": "cc:2A", "title": "Assemblies of molecules, cells, and groups of cells within single cellular and multicellular organisms"},
                        {"id": "cc:2B", "title": "The structure, growth, physiology, and genetics of prokaryotes and viruses"},
                        {"id": "cc:2C", "title": "Processes of cell division, differentiation, and specialization"},
                    ],
                },
                {
                    "id": "fc:3",
                    "title": "Complex systems of tissues and organs sense the internal and external environments of multicellular organisms, and through integrated functioning, maintain a stable internal environment.",
                    "content_categories": [
                        {"id": "cc:3A", "title": "Structure and functions of the nervous and endocrine systems and ways these systems coordinate the organ systems"},
                        {"id": "cc:3B", "title": "Structure and integrative functions of the main organ systems"},
                    ],
                },
            ],
        },
        {
            "id": "sec:cpbs",
            "abbrev": "Chem/Phys",
            "title": "Chemical and Physical Foundations of Biological Systems",
            "foundational_concepts": [
                {
                    "id": "fc:4",
                    "title": "Complex living organisms transport materials, sense their environment, process signals, and respond to changes using processes that can be understood in terms of physical principles.",
                    "content_categories": [
                        {"id": "cc:4A", "title": "Translational motion, forces, work, energy, and equilibrium in living systems"},
                        {"id": "cc:4B", "title": "Importance of fluids for the circulation of blood, gas movement, and gas exchange"},
                        {"id": "cc:4C", "title": "Electrochemistry and electrical circuits and their elements"},
                        {"id": "cc:4D", "title": "How light and sound interact with matter"},
                        {"id": "cc:4E", "title": "Atoms, nuclear decay, electronic structure, and atomic chemical behavior"},
                    ],
                },
                {
                    "id": "fc:5",
                    "title": "The principles that govern chemical interactions and reactions form the basis for a broader understanding of the molecular dynamics of living systems.",
                    "content_categories": [
                        {"id": "cc:5A", "title": "Unique nature of water and its solutions"},
                        {"id": "cc:5B", "title": "Nature of molecules and intermolecular interactions"},
                        {"id": "cc:5C", "title": "Separation and purification methods"},
                        {"id": "cc:5D", "title": "Structure, function, and reactivity of biologically relevant molecules"},
                        {"id": "cc:5E", "title": "Principles of chemical thermodynamics and kinetics"},
                    ],
                },
            ],
        },
        {
            "id": "sec:psbb",
            "abbrev": "Psych/Soc",
            "title": "Psychological, Social, and Biological Foundations of Behavior",
            "foundational_concepts": [
                {
                    "id": "fc:6",
                    "title": "Biological, psychological, and sociocultural factors influence the ways that individuals perceive, think about, and react to the world.",
                    "content_categories": [
                        {"id": "cc:6A", "title": "Sensing the environment"},
                        {"id": "cc:6B", "title": "Making sense of the environment"},
                        {"id": "cc:6C", "title": "Responding to the world"},
                    ],
                },
                {
                    "id": "fc:7",
                    "title": "Biological, psychological, and sociocultural factors influence behavior and behavior change.",
                    "content_categories": [
                        {"id": "cc:7A", "title": "Individual influences on behavior"},
                        {"id": "cc:7B", "title": "Social processes that influence human behavior"},
                        {"id": "cc:7C", "title": "Attitude and behavior change"},
                    ],
                },
                {
                    "id": "fc:8",
                    "title": "Psychological, sociocultural, and biological factors influence the way we think about ourselves and others, as well as how we interact with others.",
                    "content_categories": [
                        {"id": "cc:8A", "title": "Self-identity"},
                        {"id": "cc:8B", "title": "Social thinking"},
                        {"id": "cc:8C", "title": "Social interactions"},
                    ],
                },
                {
                    "id": "fc:9",
                    "title": "Cultural and social differences influence well-being.",
                    "content_categories": [
                        {"id": "cc:9A", "title": "Understanding social structure"},
                        {"id": "cc:9B", "title": "Demographic characteristics and processes"},
                    ],
                },
                {
                    "id": "fc:10",
                    "title": "Social stratification and access to resources influence well-being.",
                    "content_categories": [
                        {"id": "cc:10A", "title": "Social inequality"},
                    ],
                },
            ],
        },
        {
            "id": "sec:cars",
            "abbrev": "CARS",
            "title": "Critical Analysis and Reasoning Skills",
            "note": "CARS requires no specific content knowledge (AAMC); a different construct with no content-category spine here (brainlift SPOV 12).",
            "foundational_concepts": [],
        },
    ],
}


@lru_cache(maxsize=1)
def outline_data() -> Dict:
    """Return the embedded outline structure."""
    return OUTLINE


def load_outline_graph() -> ConceptGraph:
    """Build the ground-truth spine graph from the embedded AAMC outline."""
    data = outline_data()
    graph = ConceptGraph()
    prov = Provenance(source=_SPINE_SOURCE, locator=data.get("url", ""))

    for section in data["sections"]:
        sec_id = section["id"]
        graph.add_node(
            Node(
                id=sec_id,
                kind=NodeKind.SECTION,
                title=section["title"],
                section=sec_id,
                meta=_section_meta(section),
            )
        )
        for fc in section.get("foundational_concepts", []):
            fc_id = fc["id"]
            graph.add_node(
                Node(
                    id=fc_id,
                    kind=NodeKind.FOUNDATIONAL_CONCEPT,
                    title=fc["title"],
                    section=sec_id,
                )
            )
            graph.add_edge(Edge(src=fc_id, dst=sec_id, type=EdgeType.PART_OF, provenance=prov))
            for cc in fc.get("content_categories", []):
                cc_id = cc["id"]
                graph.add_node(
                    Node(
                        id=cc_id,
                        kind=NodeKind.CONTENT_CATEGORY,
                        title=cc["title"],
                        section=sec_id,
                    )
                )
                graph.add_edge(
                    Edge(src=cc_id, dst=fc_id, type=EdgeType.PART_OF, provenance=prov)
                )
    return graph


def _section_meta(section: Dict) -> Dict[str, str]:
    meta: Dict[str, str] = {"abbrev": section.get("abbrev", "")}
    if "note" in section:
        meta["note"] = section["note"]
    return meta
