# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Shared helpers so every Speedrun eval harness writes a machine-readable artifact
(JSON) and, where useful, a dependency-free SVG chart, into ``docs/eval-artifacts/``.

The point: the numbers in ``docs/eval-results.md`` are then GENERATED from these
artifacts by ``build_report.py`` instead of being hand-transcribed. Each artifact carries
common provenance (name, UTC timestamp, git commit, and the model/seed the run used), so
a reader can tell exactly how a figure was produced and re-run it.

No third-party deps (charts are hand-written SVG) so this runs in the plain ``out/pyenv``.
"""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_HERE = Path(__file__).resolve().parent
ANKI_ROOT = _HERE.parent
ARTIFACT_DIR = ANKI_ROOT / "docs" / "eval-artifacts"

#: Value written to an artifact's ``model`` field when no LLM was called.
OFFLINE_MODEL = "offline-stub"


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ANKI_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def write_artifact(name: str, data: Dict[str, Any]) -> Path:
    """Write ``docs/eval-artifacts/<name>.json`` with common provenance merged in."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "git_commit": _git_commit(),
        **data,
    }
    path = ARTIFACT_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_svg(name: str, svg: str) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / f"{name}.svg"
    path.write_text(svg, encoding="utf-8")
    return path


def load_artifacts() -> Dict[str, dict]:
    """All artifact JSONs keyed by file stem (name), sorted by name."""
    out: Dict[str, dict] = {}
    if not ARTIFACT_DIR.exists():
        return out
    for p in sorted(ARTIFACT_DIR.glob("*.json")):
        try:
            out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return out


# -- dependency-free SVG charts ------------------------------------------------
# Small, theme-neutral SVGs (dark text on a transparent background) so they render in
# markdown/GitHub. No colour is required for correctness; a single accent is used.

_FG = "#1a1a1a"
_MUTED = "#888"
_GRID = "#ddd"
_ACCENT = "#3b82f6"
_WARN = "#d9822b"


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def reliability_diagram_svg(
    bins: Sequence[Dict[str, float]],
    *,
    title: str = "Memory calibration (held-out reliability diagram)",
    subtitle: str = "",
) -> str:
    """A reliability diagram: predicted probability (x) vs observed recall (y), with the
    y=x perfect-calibration diagonal. ``bins`` items need ``predicted``, ``observed`` and
    (optional) ``n``. Bin marker area scales with ``n``."""
    W, H = 480, 480
    m = 64  # margin
    pw, ph = W - 2 * m, H - 2 * m

    def X(p: float) -> float:
        return m + p * pw

    def Y(p: float) -> float:
        return H - m - p * ph

    parts: List[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="system-ui,Segoe UI,sans-serif">'
    )
    parts.append(f'<text x="{W/2}" y="24" text-anchor="middle" font-size="15" '
                 f'font-weight="600" fill="{_FG}">{_esc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{W/2}" y="42" text-anchor="middle" font-size="11" '
                     f'fill="{_MUTED}">{_esc(subtitle)}</text>')
    # grid + ticks
    for t in range(0, 11, 2):
        p = t / 10.0
        parts.append(f'<line x1="{X(p):.1f}" y1="{Y(0):.1f}" x2="{X(p):.1f}" y2="{Y(1):.1f}" '
                     f'stroke="{_GRID}" stroke-width="1"/>')
        parts.append(f'<line x1="{X(0):.1f}" y1="{Y(p):.1f}" x2="{X(1):.1f}" y2="{Y(p):.1f}" '
                     f'stroke="{_GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{X(p):.1f}" y="{Y(0)+18:.1f}" text-anchor="middle" '
                     f'font-size="10" fill="{_MUTED}">{p:.1f}</text>')
        parts.append(f'<text x="{X(0)-10:.1f}" y="{Y(p)+3:.1f}" text-anchor="end" '
                     f'font-size="10" fill="{_MUTED}">{p:.1f}</text>')
    # perfect-calibration diagonal
    parts.append(f'<line x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(1):.1f}" y2="{Y(1):.1f}" '
                 f'stroke="{_MUTED}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    # observed-vs-predicted polyline + markers
    pts = [(b.get("predicted", 0.0), b.get("observed", 0.0), b.get("n", 1)) for b in bins]
    pts = [(p, o, n) for (p, o, n) in pts if n]
    if pts:
        max_n = max(n for _p, _o, n in pts) or 1
        poly = " ".join(f"{X(p):.1f},{Y(o):.1f}" for p, o, _n in pts)
        parts.append(f'<polyline points="{poly}" fill="none" stroke="{_ACCENT}" stroke-width="2"/>')
        for p, o, n in pts:
            r = 3 + 5 * (n / max_n) ** 0.5
            parts.append(f'<circle cx="{X(p):.1f}" cy="{Y(o):.1f}" r="{r:.1f}" '
                         f'fill="{_ACCENT}" fill-opacity="0.65"/>')
    # axis labels
    parts.append(f'<text x="{W/2}" y="{H-16}" text-anchor="middle" font-size="12" '
                 f'fill="{_FG}">predicted recall (FSRS)</text>')
    parts.append(f'<text x="18" y="{H/2}" text-anchor="middle" font-size="12" fill="{_FG}" '
                 f'transform="rotate(-90 18 {H/2})">observed recall</text>')
    parts.append(f'<text x="{X(0.05):.1f}" y="{Y(0.92):.1f}" font-size="10" fill="{_MUTED}">'
                 f'dashed = perfect calibration</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def bar_svg(
    items: Sequence[Tuple[str, float]],
    *,
    title: str = "",
    subtitle: str = "",
    ymax: float = 1.0,
    ranges: Optional[Sequence[Optional[Tuple[float, float]]]] = None,
    threshold: Optional[float] = None,
    threshold_label: str = "",
    value_suffix: str = "",
    as_percent: bool = True,
) -> str:
    """Vertical bar chart. ``items`` = (label, value); optional per-bar ``ranges``
    (lo, hi) draw error bars; optional ``threshold`` draws a reference line."""
    n = len(items)
    W = max(360, 90 * n + 120)
    H = 340
    m_left, m_right, m_top, m_bot = 56, 24, 56, 64
    pw = W - m_left - m_right
    ph = H - m_top - m_bot
    slot = pw / max(1, n)
    bar_w = min(70, slot * 0.6)

    def Y(v: float) -> float:
        return m_top + ph - (v / ymax) * ph

    def fmt(v: float) -> str:
        return f"{v*100:.1f}%" if as_percent else f"{v:g}{value_suffix}"

    parts: List[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="system-ui,Segoe UI,sans-serif">'
    )
    if title:
        parts.append(f'<text x="{W/2}" y="24" text-anchor="middle" font-size="15" '
                     f'font-weight="600" fill="{_FG}">{_esc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{W/2}" y="42" text-anchor="middle" font-size="11" '
                     f'fill="{_MUTED}">{_esc(subtitle)}</text>')
    # y grid
    for t in range(0, 6):
        v = ymax * t / 5.0
        parts.append(f'<line x1="{m_left}" y1="{Y(v):.1f}" x2="{W-m_right}" y2="{Y(v):.1f}" '
                     f'stroke="{_GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{m_left-8}" y="{Y(v)+3:.1f}" text-anchor="end" font-size="10" '
                     f'fill="{_MUTED}">{fmt(v)}</text>')
    if threshold is not None:
        parts.append(f'<line x1="{m_left}" y1="{Y(threshold):.1f}" x2="{W-m_right}" '
                     f'y2="{Y(threshold):.1f}" stroke="{_WARN}" stroke-width="1.5" '
                     f'stroke-dasharray="6 4"/>')
        if threshold_label:
            parts.append(f'<text x="{W-m_right}" y="{Y(threshold)-4:.1f}" text-anchor="end" '
                         f'font-size="10" fill="{_WARN}">{_esc(threshold_label)}</text>')
    for i, (label, value) in enumerate(items):
        cx = m_left + slot * i + slot / 2
        x = cx - bar_w / 2
        y = Y(max(0.0, value))
        h = (m_top + ph) - y
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
                     f'rx="3" fill="{_ACCENT}" fill-opacity="0.75"/>')
        parts.append(f'<text x="{cx:.1f}" y="{y-6:.1f}" text-anchor="middle" font-size="11" '
                     f'font-weight="600" fill="{_FG}">{fmt(value)}</text>')
        if ranges and i < len(ranges) and ranges[i]:
            lo, hi = ranges[i]
            parts.append(f'<line x1="{cx:.1f}" y1="{Y(lo):.1f}" x2="{cx:.1f}" y2="{Y(hi):.1f}" '
                         f'stroke="{_FG}" stroke-width="1.5"/>')
            for yy in (Y(lo), Y(hi)):
                parts.append(f'<line x1="{cx-6:.1f}" y1="{yy:.1f}" x2="{cx+6:.1f}" y2="{yy:.1f}" '
                             f'stroke="{_FG}" stroke-width="1.5"/>')
        # wrap long labels onto two lines at a space near the middle
        parts.append(_label_svg(label, cx, m_top + ph + 16))
    parts.append("</svg>")
    return "\n".join(parts)


def _label_svg(label: str, cx: float, y: float, size: int = 10) -> str:
    label = str(label)
    if len(label) <= 12 or " " not in label:
        return (f'<text x="{cx:.1f}" y="{y:.1f}" text-anchor="middle" font-size="{size}" '
                f'fill="{_FG}">{_esc(label)}</text>')
    mid = label.rfind(" ", 0, len(label) // 2 + 4)
    if mid <= 0:
        mid = label.find(" ")
    a, b = label[:mid], label[mid + 1:]
    return (f'<text x="{cx:.1f}" y="{y:.1f}" text-anchor="middle" font-size="{size}" '
            f'fill="{_FG}">{_esc(a)}<tspan x="{cx:.1f}" dy="12">{_esc(b)}</tspan></text>')
