"""Structured deadlock analysis (human-readable + JSON-serializable)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import networkx as nx

from threadle.analysis.graph import build_graph
from threadle.core.tracker import snapshot_state

EdgeKind = Literal["held_by", "waits_for", "unknown"]


@dataclass(frozen=True, slots=True)
class GraphEdgeView:
    """One directed edge in the wait-for graph (stable JSON shape)."""

    source: str
    target: str
    relation: EdgeKind


@dataclass(frozen=True, slots=True)
class DeadlockReport:
    """Result of analyzing the current tracker snapshot for a wait-for cycle."""

    found: bool
    raw_cycle: list[tuple[Any, Any, Any]] | None
    edges: list[GraphEdgeView] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "summary": self.summary,
            "raw_cycle": [list(t) for t in self.raw_cycle] if self.raw_cycle else None,
            "edges": [asdict(e) for e in self.edges],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def __str__(self) -> str:
        return self.summary or ("deadlock" if self.found else "no deadlock")


def _thread_label(ident: int, threads: dict[int, Any]) -> str:
    info = threads.get(ident)
    name = getattr(info, "name", None) if info is not None else None
    if name:
        return f"thread {ident} ({name})"
    return f"thread {ident}"


def _node_summary(
    node: str,
    *,
    graph: nx.DiGraph,
    threads: dict[int, Any],
) -> tuple[str, Literal["thread", "lock"]]:
    data = graph.nodes.get(node, {})
    kind = data.get("kind")
    if kind == "thread":
        ident = data.get("ident")
        if isinstance(ident, int):
            return _thread_label(ident, threads), "thread"
        return str(node), "thread"
    if kind == "lock":
        name = data.get("name", "")
        return f"lock {name!r}", "lock"
    if node.startswith("thread:"):
        rest = node.split(":", 1)[-1]
        try:
            tid = int(rest)
            return _thread_label(tid, threads), "thread"
        except ValueError:
            pass
    if node.startswith("lock:"):
        return f"lock {node.split(':', 1)[-1]!r}", "lock"
    return node, "thread"


def _edge_relation(graph: nx.DiGraph, u: str, v: str) -> EdgeKind:
    rel = graph.edges.get((u, v), {}).get("relation")
    if rel in ("held_by", "waits_for"):
        return rel  # type: ignore[return-value]
    return "unknown"


def _build_report_from_cycle(
    graph: nx.DiGraph,
    raw_cycle: list[tuple[Any, Any, Any]],
) -> DeadlockReport:
    state = snapshot_state()
    threads = state["threads"]
    edges: list[GraphEdgeView] = []
    parts: list[str] = []
    for u, v, _dir in raw_cycle:
        u_s, _ = _node_summary(str(u), graph=graph, threads=threads)
        v_s, _ = _node_summary(str(v), graph=graph, threads=threads)
        rel = _edge_relation(graph, str(u), str(v))
        edges.append(GraphEdgeView(source=str(u), target=str(v), relation=rel))
        if rel == "waits_for":
            parts.append(f"{u_s} waits for {v_s}")
        elif rel == "held_by":
            parts.append(f"{v_s} holds {u_s}")
        else:
            parts.append(f"{u_s} -> {v_s}")
    summary = "; ".join(parts)
    return DeadlockReport(found=True, raw_cycle=raw_cycle, edges=edges, summary=summary)


def analyze_deadlocks() -> DeadlockReport:
    """
    Inspect the current :mod:`threadle.core.tracker` snapshot and return a structured report.

    This is the preferred API over :func:`~threadle.analysis.deadlock.detect_deadlocks`
    when you need explanations, JSON, or stable fields instead of raw NetworkX tuples.
    """
    graph = build_graph()
    try:
        raw = nx.find_cycle(graph, orientation="original")
    except nx.NetworkXNoCycle:
        return DeadlockReport(
            found=False,
            raw_cycle=None,
            edges=[],
            summary="no wait-for cycle at this snapshot",
        )
    return _build_report_from_cycle(graph, raw)
