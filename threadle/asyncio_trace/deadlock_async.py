"""Heuristic cycle detection on the async dependency graph (recorded awaits only)."""

from __future__ import annotations

from typing import Any

import networkx as nx

from threadle.asyncio_trace.graph import build_async_dependency_graph


def detect_async_wait_cycle(raw_events: list[dict[str, Any]] | None = None) -> list[tuple[Any, Any]] | None:
    """
    Return a directed cycle in the await-dependency graph, or ``None`` if acyclic.

    This is **heuristic**: it only sees dependencies passed as ``awaiting=``
    to :func:`threadle.asyncio_trace.decorators.traced_await`.
    """
    g = build_async_dependency_graph(raw_events)
    if g.number_of_edges() == 0:
        return None
    try:
        return nx.find_cycle(g, orientation="original")
    except nx.NetworkXNoCycle:
        return None
