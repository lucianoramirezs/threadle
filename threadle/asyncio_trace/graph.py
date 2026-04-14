"""Dependency graph between asyncio tasks from recorded ``await`` edges."""

from __future__ import annotations

from typing import Any

import networkx as nx

from threadle.asyncio_trace import events as AE
from threadle.asyncio_trace.recorder import snapshot_raw_async_events


def build_async_dependency_graph(raw_events: list[dict[str, Any]] | None = None) -> nx.DiGraph:
    """
    Build a directed graph: edge ``u -> v`` means task ``u`` recorded an
    ``await`` whose ``awaiting`` field names ``v`` (best-effort string match).
    """
    if raw_events is None:
        raw_events = snapshot_raw_async_events()
    g = nx.DiGraph()
    for ev in sorted(raw_events, key=lambda e: (e["timestamp"], e.get("_seq", 0))):
        tid = ev["task_id"]
        g.add_node(tid)
        if ev["event"] != AE.EVENT_AWAIT:
            continue
        target = ev.get("awaiting")
        if not target:
            continue
        g.add_node(target)
        g.add_edge(tid, target, event="await", timestamp=ev["timestamp"])
    return g
