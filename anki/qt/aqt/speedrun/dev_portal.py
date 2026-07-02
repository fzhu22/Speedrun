# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Speedrun developer portal.

A read-only inspection view of everything the Speedrun engine derives: the AAMC concept
graph (the ground-truth spine), per-content-category coverage / memory / weakness /
planning score, the prerequisite edges, the live study plan, and which parts of the
graph model are live versus dormant scaffolding.

It renders static HTML built in Python from the engine (`topic_mastery`,
`speedrun_dashboard`, `load_outline_graph`) - it makes no backend calls from the page
itself, so it is unaffected by the page API-access rules.
"""

from __future__ import annotations

import html
from typing import Dict, Optional

import aqt
import aqt.main
from anki.speedrun import NodeKind, load_outline_graph, outline_data
from aqt.qt import *
from aqt.utils import disable_help_button, restoreGeom, saveGeom
from aqt.webview import AnkiWebView, AnkiWebViewKind

DIALOG_NAME = "SpeedrunDevPortal"

# Mirror of the planner constants in rslib/src/speedrun/planning.rs. Display-only: the
# authoritative planner runs in the Rust engine (the "Study plan" section shows its real
# output); these are surfaced so the per-category table can show the planning inputs.
# Keep in sync with planning.rs.
YIELD_WEIGHTS: Dict[str, float] = {
    "cc:1A": 0.90,
    "cc:1D": 0.85,
    "cc:5E": 0.80,
    "cc:4A": 0.70,
    "cc:1B": 0.60,
    "cc:3A": 0.60,
    "cc:2A": 0.50,
    "cc:5A": 0.50,
}
BASE_WEIGHT = 0.30
PREREQUISITES = [("cc:5E", "cc:1D"), ("cc:5B", "cc:5D"), ("cc:4A", "cc:4B")]
PREREQ_THRESHOLD = 0.5


def _weight(cc_id: str) -> float:
    return YIELD_WEIGHTS.get(cc_id, BASE_WEIGHT)


def _cc_from_tag(tag: str, known_codes: set) -> Optional[str]:
    """Most-specific `::` part that names a known content category (matches the engine)."""
    for part in reversed(tag.split("::")):
        part = part.strip()
        if part in known_codes:
            return f"cc:{part}"
    return None


def _pct(value: Optional[float]) -> str:
    return "-" if value is None else f"{round(value * 100)}%"


def _esc(text: str) -> str:
    return html.escape(str(text))


def _kv(key: str, value: str) -> str:
    return f"<tr><th>{_esc(key)}</th><td>{value}</td></tr>"


def build_html(col) -> str:
    """Build the static dev-portal HTML from the engine (read-only)."""
    graph = load_outline_graph()
    cc_nodes = graph.nodes(NodeKind.CONTENT_CATEGORY)
    known_codes = {n.id.replace("cc:", "") for n in cc_nodes}

    dash = col.speedrun_dashboard()
    mastery = col.topic_mastery(tag_prefix="MCAT", min_cards_for_average=1)

    # Aggregate the per-tag mastery query up to content categories.
    cards: Dict[str, int] = {}
    reviewed: Dict[str, int] = {}
    mastered: Dict[str, int] = {}
    recall_wsum: Dict[str, float] = {}
    for t in mastery.topics:
        cc = _cc_from_tag(t.tag, known_codes)
        if not cc:
            continue
        cards[cc] = cards.get(cc, 0) + t.total_cards
        reviewed[cc] = reviewed.get(cc, 0) + t.reviewed_cards
        mastered[cc] = mastered.get(cc, 0) + t.mastered_cards
        if t.HasField("average_recall"):
            recall_wsum[cc] = recall_wsum.get(cc, 0.0) + t.average_recall * t.reviewed_cards
    recall: Dict[str, float] = {
        cc: recall_wsum[cc] / reviewed[cc]
        for cc in reviewed
        if reviewed.get(cc, 0) > 0 and cc in recall_wsum
    }

    prereq_by_dep: Dict[str, list] = {}
    for pre, dep in PREREQUISITES:
        prereq_by_dep.setdefault(dep, []).append(pre)

    parts = [_STYLE, "<div class='wrap'>"]
    parts.append("<h1>Speedrun Dev Portal</h1>")
    parts.append(
        "<p class='muted'>Read-only view of the concept graph, coverage, and planning "
        "internals derived by the engine.</p>"
    )

    # Summary
    gate = "allowed" if dash.readiness_allowed else "abstaining"
    parts.append("<h2>Summary</h2><table class='kv'>")
    parts.append(
        _kv(
            "Coverage",
            f"{_pct(dash.overall_coverage)} ({dash.covered_leaves}/{dash.total_leaves} content categories)",
        )
    )
    parts.append(_kv("Total reviews", f"{dash.total_reviews:,}"))
    parts.append(_kv("Readiness gate", f"{gate} - {_esc(dash.readiness_status)}"))
    parts.append(_kv("Performance", _esc(dash.performance_status)))
    parts.append(_kv("Give-up line (coverage)", _pct(dash.give_up_line)))
    parts.append(_kv("Prereq threshold (weakness)", f"{PREREQ_THRESHOLD:.2f}"))
    parts.append("</table>")

    # Concept graph structure
    n_sec = len(graph.nodes(NodeKind.SECTION))
    n_fc = len(graph.nodes(NodeKind.FOUNDATIONAL_CONCEPT))
    n_cc = len(cc_nodes)
    n_edges = len(graph.edges())
    parts.append("<h2>Concept graph (ground-truth spine)</h2>")
    parts.append(
        f"<p class='muted'>{n_sec} sections &middot; {n_fc} foundational concepts &middot; "
        f"{n_cc} content categories &middot; {n_edges} <code>part_of</code> edges. "
        "Nodes map to your cards by tag.</p>"
    )

    # Per content category
    parts.append("<h2>Content categories</h2>")
    parts.append(
        "<table class='grid'><thead><tr>"
        "<th>Sec</th><th>Code</th><th>Title</th><th class='n'>Weight</th>"
        "<th class='n'>Cards</th><th class='n'>Rev</th><th class='n'>Mastered</th>"
        "<th class='n'>Recall</th><th class='n'>Weakness</th><th class='n'>Score</th>"
        "<th>Prereqs</th></tr></thead><tbody>"
    )
    for section in outline_data()["sections"]:
        abbrev = section.get("abbrev", "")
        for fc in section.get("foundational_concepts", []):
            for cc in fc.get("content_categories", []):
                cc_id = cc["id"]
                code = cc_id.replace("cc:", "")
                w = _weight(cc_id)
                n_cards = cards.get(cc_id, 0)
                r = recall.get(cc_id)
                weakness = (1.0 - r) if r is not None else 1.0
                score = w * weakness
                pres = prereq_by_dep.get(cc_id, [])
                pres_txt = ", ".join(p.replace("cc:", "") for p in pres) if pres else "-"
                row_cls = "" if n_cards else " class='miss'"
                parts.append(
                    f"<tr{row_cls}>"
                    f"<td>{_esc(abbrev)}</td><td><b>{_esc(code)}</b></td>"
                    f"<td class='title'>{_esc(cc['title'])}</td>"
                    f"<td class='n'>{w:.2f}</td>"
                    f"<td class='n'>{n_cards}</td>"
                    f"<td class='n'>{reviewed.get(cc_id, 0)}</td>"
                    f"<td class='n'>{mastered.get(cc_id, 0)}</td>"
                    f"<td class='n'>{_pct(r)}</td>"
                    f"<td class='n'>{weakness:.2f}</td>"
                    f"<td class='n'>{score:.2f}</td>"
                    f"<td>{_esc(pres_txt)}</td>"
                    "</tr>"
                )
    parts.append("</tbody></table>")
    parts.append(
        "<p class='muted'>Weakness = 1 - recall (or 1.00 when unreviewed). "
        "Score = weight x weakness. Rows with no cards are dimmed.</p>"
    )

    # Prerequisite edges
    parts.append("<h2>Prerequisite edges</h2><ul>")
    for pre, dep in PREREQUISITES:
        p_code = pre.replace("cc:", "")
        d_code = dep.replace("cc:", "")
        parts.append(
            f"<li><code>{_esc(p_code)}</code> &rarr; <code>{_esc(d_code)}</code> "
            f"(learn {_esc(p_code)} before {_esc(d_code)})</li>"
        )
    parts.append("</ul>")

    # Study plan (real engine output)
    parts.append("<h2>Study plan (live engine output)</h2>")
    if dash.plan:
        parts.append(
            "<table class='grid'><thead><tr><th class='n'>#</th><th>Code</th>"
            "<th>Title</th><th>Rung</th><th class='n'>Score</th><th>Reason</th>"
            "<th>Prereq</th></tr></thead><tbody>"
        )
        for i, item in enumerate(dash.plan, start=1):
            parts.append(
                f"<tr><td class='n'>{i}</td><td><b>{_esc(item.code)}</b></td>"
                f"<td class='title'>{_esc(item.title)}</td><td>{_esc(item.rung)}</td>"
                f"<td class='n'>{item.score:.2f}</td><td>{_esc(item.reason)}</td>"
                f"<td>{'yes' if item.prerequisite else '-'}</td></tr>"
            )
        parts.append("</tbody></table>")
    else:
        parts.append("<p class='muted'>No recommendation yet.</p>")

    # Live vs dormant
    parts.append("<h2>Graph model status</h2>")
    parts.append(
        "<table class='grid'><thead><tr><th>Piece</th><th>State</th><th>Where</th></tr>"
        "</thead><tbody>"
        "<tr><td>Outline spine (sections/categories, part_of)</td><td class='ok'>live</td>"
        "<td><code>rslib/speedrun/outline.rs</code></td></tr>"
        "<tr><td>Coverage + give-up gate</td><td class='ok'>live</td>"
        "<td><code>rslib/speedrun/coverage.rs</code></td></tr>"
        "<tr><td>Yield weights + prerequisite planning</td><td class='ok'>live</td>"
        "<td><code>rslib/speedrun/planning.rs</code></td></tr>"
        "<tr><td>Typed ConceptGraph (nodes/edges/provenance)</td><td class='warn'>scaffolding</td>"
        "<td><code>pylib/anki/speedrun/models.py</code></td></tr>"
        "<tr><td>tests / misconception edges, AI-proposed edges</td><td class='warn'>dormant</td>"
        "<td>not wired to the live dashboard</td></tr>"
        "</tbody></table>"
    )

    parts.append("</div>")
    return "".join(parts)


class SpeedrunDevPortal(QDialog):
    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        self.mw = mw
        self.setWindowTitle("Speedrun Dev Portal")
        disable_help_button(self)
        restoreGeom(self, "speedrunDevPortal", default_size=(960, 760))

        layout = QVBoxLayout(self)
        buttons = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        qconnect(self.refresh_btn.clicked, self.refresh)
        buttons.addWidget(self.refresh_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.web = AnkiWebView(self, kind=AnkiWebViewKind.DEFAULT)
        layout.addWidget(self.web)

        self._ready = False
        self.refresh()
        self.show()
        self._ready = True

    def event(self, evt: QEvent) -> bool:
        if (
            evt is not None
            and evt.type() == QEvent.Type.WindowActivate
            and getattr(self, "_ready", False)
            and self.web is not None
        ):
            self.refresh()
        return super().event(evt)

    def refresh(self) -> None:
        try:
            self.web.stdHtml(build_html(self.mw.col), context=self)
        except Exception as exc:  # never let the dev portal hard-crash the GUI
            self.web.stdHtml(
                f"<pre style='padding:16px'>Dev portal error:\n{_esc(str(exc))}</pre>"
            )

    def reject(self) -> None:
        saveGeom(self, "speedrunDevPortal")
        self.web = None  # type: ignore[assignment]
        aqt.dialogs.markClosed(DIALOG_NAME)
        QDialog.reject(self)

    def closeWithCallback(self, callback) -> None:
        self.reject()
        callback()


_STYLE = """
<style>
.wrap { max-width: 900px; margin: 0 auto; padding: 8px 14px 28px; font-size: 14px; line-height: 1.45; }
.wrap h1 { font-size: 1.4em; margin: 6px 0 2px; }
.wrap h2 { font-size: 0.8em; text-transform: uppercase; letter-spacing: .5px;
    color: var(--fg-subtle); margin: 22px 0 8px; }
.wrap .muted { color: var(--fg-subtle); font-size: 0.85em; margin: 4px 0; }
.wrap code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; font-size: 0.85em; }
table.kv th { text-align: left; width: 220px; color: var(--fg-subtle); font-weight: 600; }
table.kv td, table.kv th { padding: 3px 6px; vertical-align: top; }
table.grid th { text-align: left; color: var(--fg-subtle); font-weight: 600;
    border-bottom: 1px solid var(--border-subtle); padding: 5px 6px; }
table.grid td { padding: 4px 6px; border-top: 1px solid var(--border-subtle); vertical-align: top; }
table.grid td.title { max-width: 320px; }
.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
tr.miss td { opacity: 0.5; }
td.ok, .ok { color: #2ea37a; font-weight: 600; }
td.warn, .warn { color: #d9883b; font-weight: 600; }
ul { margin: 4px 0; padding-left: 22px; }
</style>
"""
