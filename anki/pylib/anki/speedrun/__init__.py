"""Speedrun MCAT concept knowledge graph - desktop "prepare" tier (PRD Section 8).

Part of the ``anki`` library so it ships with the engine and is shared by the desktop
GUI (and, via the shared engine, the phone build). The ground-truth AAMC-outline spine
is built here (desktop-side); coverage, next-best planning, and the fading/disconfirmer
mutation logic now live in the shared Rust engine, so only the spine, the typed graph
model, and the in-scope leakage check remain in Python.
"""

from __future__ import annotations

from anki.speedrun.aamc_outline import load_outline_graph, outline_data
from anki.speedrun.models import (
    GROUND_TRUTH_EDGE_TYPES,
    ConceptGraph,
    Edge,
    EdgeType,
    Node,
    NodeKind,
    Provenance,
    ValidationStatus,
)
from anki.speedrun.validation import LeakageReport, leakage_check

__all__ = [
    "ConceptGraph",
    "Edge",
    "EdgeType",
    "Node",
    "NodeKind",
    "Provenance",
    "ValidationStatus",
    "GROUND_TRUTH_EDGE_TYPES",
    "load_outline_graph",
    "outline_data",
    "leakage_check",
    "LeakageReport",
]
