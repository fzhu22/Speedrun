"""Core data model for the Speedrun concept knowledge graph (PRD Section 8).

The **spine** (``part_of`` edges) is ground truth imported from the AAMC outline and is
forced to ``GROUND_TRUTH`` at construction. Typed cross-edges (``tests``,
``prerequisite_of``) may carry :class:`Provenance` and only feed readiness once their
status is ``GROUND_TRUTH`` or ``VALIDATED`` (the honesty rule, enforced by
:meth:`Edge.feeds_readiness`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class NodeKind(str, Enum):
    """The kind of thing a node represents."""

    SECTION = "section"
    FOUNDATIONAL_CONCEPT = "foundational_concept"
    CONTENT_CATEGORY = "content_category"
    TOPIC = "topic"  # concept-family leaf (finer than a content category)
    CARD = "card"
    MISCONCEPTION = "misconception"


class EdgeType(str, Enum):
    """Typed relationships between nodes."""

    PART_OF = "part_of"  # child -> parent (hierarchy / spine)
    TESTS = "tests"  # card -> concept
    PREREQUISITE_OF = "prerequisite_of"  # prerequisite -> dependent


class ValidationStatus(str, Enum):
    """Whether an edge is trusted enough to feed readiness."""

    GROUND_TRUTH = "ground_truth"  # imported spine; no validation needed
    PROPOSED = "proposed"  # AI-proposed, not yet checked
    VALIDATED = "validated"  # passed held-out validation
    REJECTED = "rejected"  # failed validation; never feeds readiness


#: Edge types imported as ground truth (no validation, no provenance required).
GROUND_TRUTH_EDGE_TYPES = frozenset({EdgeType.PART_OF})

#: Statuses whose edges are allowed to feed readiness (PRD Section 8 AC2).
READINESS_STATUSES = frozenset(
    {ValidationStatus.GROUND_TRUTH, ValidationStatus.VALIDATED}
)


@dataclass(frozen=True)
class Provenance:
    """A named source for an AI-proposed edge (the traceability rule)."""

    source: str
    locator: str = ""  # page / section / chunk id within the source
    note: str = ""

    def __post_init__(self) -> None:
        if not self.source or not self.source.strip():
            raise ValueError("Provenance.source must be a non-empty named source")


@dataclass
class Node:
    """A vertex in the concept graph."""

    id: str
    kind: NodeKind
    title: str
    section: Optional[str] = None  # the section id this node rolls up to
    yield_weight: float = 0.0  # exam weight in [0, 1]; a tunable planning input
    meta: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Node.id is required")
        if not 0.0 <= self.yield_weight <= 1.0:
            raise ValueError(f"yield_weight must be in [0, 1], got {self.yield_weight}")


@dataclass
class Edge:
    """A typed, directed relationship between two nodes.

    ``part_of`` edges are forced to ``GROUND_TRUTH`` at construction; other typed edges
    keep their given status and only feed readiness once ground-truth or validated.
    """

    src: str
    dst: str
    type: EdgeType
    status: ValidationStatus = ValidationStatus.PROPOSED
    provenance: Optional[Provenance] = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.src == self.dst:
            raise ValueError(f"self-loop not allowed on node {self.src!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
        if self.type in GROUND_TRUTH_EDGE_TYPES:
            # Spine edges are ground truth by definition.
            self.status = ValidationStatus.GROUND_TRUTH

    @property
    def key(self) -> Tuple[str, str, str]:
        """A stable identity for de-duplication and gold-key matching."""
        return (self.src, self.dst, self.type.value)

    @property
    def feeds_readiness(self) -> bool:
        """True only for ground-truth or validated edges (AC2)."""
        return self.status in READINESS_STATUSES


class ConceptGraph:
    """An in-memory typed graph with the spine + cross-edges.

    Indices are kept for the two traversals that matter: outgoing and incoming
    edges by type. ``add_edge`` refuses dangling endpoints and duplicate edges so
    a malformed graph fails loudly at build time.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._edge_keys: set = set()

    # -- nodes -----------------------------------------------------------------
    def add_node(self, node: Node, *, replace: bool = False) -> None:
        if node.id in self._nodes and not replace:
            raise ValueError(f"duplicate node id: {node.id!r}")
        self._nodes[node.id] = node

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def nodes(self, kind: Optional[NodeKind] = None) -> List[Node]:
        if kind is None:
            return list(self._nodes.values())
        return [n for n in self._nodes.values() if n.kind == kind]

    # -- edges -----------------------------------------------------------------
    def add_edge(self, edge: Edge) -> None:
        if edge.src not in self._nodes:
            raise KeyError(f"edge references unknown src node: {edge.src!r}")
        if edge.dst not in self._nodes:
            raise KeyError(f"edge references unknown dst node: {edge.dst!r}")
        if edge.key in self._edge_keys:
            raise ValueError(f"duplicate edge: {edge.key}")
        self._edges.append(edge)
        self._edge_keys.add(edge.key)

    def edges(self, type: Optional[EdgeType] = None) -> List[Edge]:
        if type is None:
            return list(self._edges)
        return [e for e in self._edges if e.type == type]

    def out_edges(self, src: str, type: Optional[EdgeType] = None) -> List[Edge]:
        return [
            e
            for e in self._edges
            if e.src == src and (type is None or e.type == type)
        ]

    def in_edges(self, dst: str, type: Optional[EdgeType] = None) -> List[Edge]:
        return [
            e
            for e in self._edges
            if e.dst == dst and (type is None or e.type == type)
        ]

    def readiness_edges(self, type: Optional[EdgeType] = None) -> List[Edge]:
        """Only the edges allowed to move a number (ground-truth or validated)."""
        return [e for e in self.edges(type) if e.feeds_readiness]

    def find_edge(self, key: Tuple[str, str, str]) -> Optional[Edge]:
        for e in self._edges:
            if e.key == key:
                return e
        return None

    # -- dunders ---------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: object) -> bool:
        return node_id in self._nodes

    def __repr__(self) -> str:
        return (
            f"ConceptGraph(nodes={len(self._nodes)}, edges={len(self._edges)})"
        )
