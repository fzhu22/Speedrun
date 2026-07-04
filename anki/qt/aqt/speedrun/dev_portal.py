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
import json
import os
from typing import Dict, Optional

import aqt
import aqt.main
from anki.speedrun import EdgeType, NodeKind, load_outline_graph, outline_data
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


def _tier(cc_id: str, cards: Dict[str, int], recall: Dict[str, float]) -> str:
    """Map a content category to a color tier from its cards + recall (for the graph)."""
    if cards.get(cc_id, 0) == 0:
        return "uncovered"
    r = recall.get(cc_id)
    if r is None:
        return "progress"
    if r >= 0.8:
        return "strong"
    if r >= 0.5:
        return "weak"
    return "low"


def _graph_elements(graph, cards: Dict[str, int], recall: Dict[str, float]) -> list:
    """Cytoscape nodes + edges for the AAMC spine, content categories colored by progress."""
    elements: list = []
    for n in graph.nodes():
        if n.kind == NodeKind.SECTION:
            kind, label = "section", (n.meta.get("abbrev") or n.title)
        elif n.kind == NodeKind.FOUNDATIONAL_CONCEPT:
            kind, label = "fc", n.id.replace("fc:", "")
        elif n.kind == NodeKind.CONTENT_CATEGORY:
            kind, label = "cc", n.id.replace("cc:", "")
        else:
            continue
        data = {"id": n.id, "label": label, "kind": kind, "title": n.title}
        if kind == "cc":
            data["tier"] = _tier(n.id, cards, recall)
        elements.append({"data": data})
    for e in graph.edges(EdgeType.PART_OF):  # emit parent -> child for a top-down tree
        elements.append(
            {"data": {"id": f"po::{e.src}::{e.dst}", "source": e.dst, "target": e.src, "kind": "part_of"}}
        )
    for pre, dep in PREREQUISITES:
        if graph.has_node(pre) and graph.has_node(dep):
            elements.append(
                {"data": {"id": f"pr::{pre}::{dep}", "source": pre, "target": dep, "kind": "prereq"}}
            )
    return elements


def _cytoscape_js() -> str:
    """The vendored cytoscape library, inlined into the page (see vendor/README.md)."""
    path = os.path.join(os.path.dirname(__file__), "vendor", "cytoscape.min.js")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


#: The graph bootstrap. Colors are read from the live theme CSS variables so the graph
#: matches light/dark automatically; ``__DATA__`` is replaced with the elements JSON.
_GRAPH_INIT = """
(function(){
  try {
    var root = getComputedStyle(document.documentElement);
    function v(n, f){ var x=(root.getPropertyValue(n)||'').trim(); return x||f; }
    var C = {
      fg:v('--fg','#333'), fgSubtle:v('--fg-subtle','#888'), border:v('--border','#ccc'),
      elevated:v('--canvas-elevated','#fff'), inset:v('--canvas-inset','#eee'),
      card:v('--accent-card','#4c8dff'), note:v('--accent-note','#37b24d'),
      danger:v('--accent-danger','#e03131'), flag2:v('--flag-2','#f08c00')
    };
    var cy = cytoscape({
      container: document.getElementById('sr-graph'),
      elements: __DATA__,
      wheelSensitivity: 0.2,
      style: [
        { selector:'node', style:{ 'label':'data(label)','color':C.fg,'font-size':11,
          'text-valign':'center','text-halign':'center','shape':'round-rectangle',
          'width':'label','height':'label','padding':'6px','background-color':C.elevated,
          'border-width':1,'border-color':C.border } },
        { selector:'node[kind="section"]', style:{ 'background-color':C.card,'color':'#fff','font-weight':'bold','font-size':12 } },
        { selector:'node[kind="fc"]', style:{ 'background-color':C.inset,'color':C.fgSubtle } },
        { selector:'node[tier="strong"]', style:{ 'background-color':C.note,'color':'#fff','border-color':C.note } },
        { selector:'node[tier="weak"]', style:{ 'background-color':C.flag2,'color':'#fff','border-color':C.flag2 } },
        { selector:'node[tier="low"]', style:{ 'background-color':C.danger,'color':'#fff','border-color':C.danger } },
        { selector:'node[tier="progress"]', style:{ 'border-color':C.card,'border-width':2 } },
        { selector:'node[tier="uncovered"]', style:{ 'background-color':C.inset,'color':C.fgSubtle,'border-style':'dashed' } },
        { selector:'edge', style:{ 'width':1,'line-color':C.border,'curve-style':'bezier',
          'target-arrow-shape':'triangle','target-arrow-color':C.border,'arrow-scale':0.7 } },
        { selector:'edge[kind="prereq"]', style:{ 'width':2,'line-style':'dashed','line-color':C.flag2,'target-arrow-color':C.flag2 } }
      ],
      layout: { name:'breadthfirst', directed:true, roots:'[kind="section"]', spacingFactor:1.15, padding:12 }
    });
    cy.on('tap','node',function(e){
      var el=document.getElementById('sr-graph-caption');
      if(el){ el.textContent = e.target.data('title') || e.target.data('label'); }
    });
    cy.fit(undefined, 20);
  } catch (err) {
    var g=document.getElementById('sr-graph');
    if(g){ g.textContent = 'Graph failed to render: ' + err; }
  }
})();
"""


def _graph_block(graph, cards: Dict[str, int], recall: Dict[str, float]) -> str:
    """Legend + graph container + inlined cytoscape and init script."""
    data_json = json.dumps(_graph_elements(graph, cards, recall)).replace("</", "<\\/")
    init = _GRAPH_INIT.replace("__DATA__", data_json)
    legend = (
        "<div class='legend'>"
        "<span class='lg sec'>Section</span><span class='lg fc'>Concept</span>"
        "<span class='lg strong'>Strong</span><span class='lg weak'>Improving</span>"
        "<span class='lg low'>Weak</span><span class='lg progress'>Studying</span>"
        "<span class='lg uncovered'>No cards</span>"
        "<span class='lg prereq'>prerequisite</span>"
        "</div>"
    )
    return (
        legend
        + "<div id='sr-graph'></div>"
        + "<p id='sr-graph-caption' class='muted'>Tap a node to see its full name.</p>"
        + "<script>" + _cytoscape_js() + "</script>"
        + "<script>" + init + "</script>"
    )


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
    parts.append("<section class='card'><h2>Summary</h2><table class='kv'>")
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
    parts.append("</table></section>")

    # Concept graph (interactive)
    n_sec = len(graph.nodes(NodeKind.SECTION))
    n_fc = len(graph.nodes(NodeKind.FOUNDATIONAL_CONCEPT))
    n_cc = len(cc_nodes)
    n_edges = len(graph.edges())
    parts.append("<section class='card'><h2>Concept graph</h2>")
    parts.append(
        f"<p class='muted'>{n_sec} sections &middot; {n_fc} foundational concepts &middot; "
        f"{n_cc} content categories &middot; {n_edges} <code>part_of</code> edges + "
        f"{len(PREREQUISITES)} prerequisite edges. Drag to move, scroll to zoom; content "
        "categories are colored by your recall.</p>"
    )
    parts.append(_graph_block(graph, cards, recall))
    parts.append("</section>")

    # Per content category
    parts.append("<section class='card'><h2>Content categories</h2>")
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
    parts.append("</section>")

    # Prerequisite edges
    parts.append("<section class='card'><h2>Prerequisite edges</h2><ul>")
    for pre, dep in PREREQUISITES:
        p_code = pre.replace("cc:", "")
        d_code = dep.replace("cc:", "")
        parts.append(
            f"<li><code>{_esc(p_code)}</code> &rarr; <code>{_esc(d_code)}</code> "
            f"(learn {_esc(p_code)} before {_esc(d_code)})</li>"
        )
    parts.append("</ul></section>")

    # Study plan (real engine output)
    parts.append("<section class='card'><h2>Study plan (live engine output)</h2>")
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
    parts.append("</section>")

    # Live vs dormant
    parts.append("<section class='card'><h2>Graph model status</h2>")
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
    parts.append("</section>")

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
.wrap { max-width: 940px; margin: 0 auto; padding: 12px 16px 28px; color: var(--fg);
    font-size: 14px; line-height: 1.5; }
.wrap h1 { font-size: 1.4em; font-weight: 600; margin: 6px 0 2px; }
.card { background: var(--canvas-elevated); border: 1px solid var(--border-subtle);
    border-radius: var(--border-radius-medium, 10px); padding: 12px 16px 14px; margin: 14px 0; }
.card h2 { font-size: 1.05em; font-weight: 600; color: var(--fg); margin: 0 0 10px;
    padding-bottom: .3em; border-bottom: 1px solid var(--border); }
.muted { color: var(--fg-subtle); font-size: 0.85em; margin: 6px 0; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; font-size: 0.85em; }
table.kv th { text-align: left; width: 230px; color: var(--fg-subtle); font-weight: 600; }
table.kv td, table.kv th { padding: 3px 6px; vertical-align: top; }
table.grid th { text-align: left; color: var(--fg-subtle); font-weight: 600;
    border-bottom: 1px solid var(--border); padding: 5px 6px; }
table.grid td { padding: 4px 6px; border-top: 1px solid var(--border-subtle); vertical-align: top; }
table.grid td.title { max-width: 340px; }
.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
tr.miss td { opacity: 0.5; }
td.ok, .ok { color: var(--accent-note); font-weight: 600; }
td.warn, .warn { color: var(--flag-2); font-weight: 600; }
ul { margin: 4px 0; padding-left: 22px; }
/* knowledge graph */
.legend { display: flex; flex-wrap: wrap; gap: 8px; margin: 2px 0 10px; font-size: 0.78em; }
.lg { padding: 2px 9px; border-radius: 999px; border: 1px solid var(--border-subtle); }
.lg.sec { background: var(--accent-card); color: #fff; border-color: var(--accent-card); }
.lg.fc { background: var(--canvas-inset); color: var(--fg-subtle); }
.lg.strong { background: var(--accent-note); color: #fff; border-color: var(--accent-note); }
.lg.weak { background: var(--flag-2); color: #fff; border-color: var(--flag-2); }
.lg.low { background: var(--accent-danger); color: #fff; border-color: var(--accent-danger); }
.lg.progress { border: 2px solid var(--accent-card); }
.lg.uncovered { background: var(--canvas-inset); color: var(--fg-subtle); border-style: dashed; }
.lg.prereq { border: 1px dashed var(--flag-2); color: var(--flag-2); }
#sr-graph { height: 460px; width: 100%; border: 1px solid var(--border-subtle);
    border-radius: var(--border-radius-medium, 10px); background: var(--canvas-inset); }
</style>
"""
