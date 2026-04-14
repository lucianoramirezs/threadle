"""Tests for async dependency graph and cycle detection."""

from __future__ import annotations

from threadle.asyncio_trace import events as AE
from threadle.asyncio_trace.deadlock_async import detect_async_wait_cycle
from threadle.asyncio_trace.graph import build_async_dependency_graph


def test_build_graph_from_await_edges() -> None:
    raw = [
        {"timestamp": 1.0, "task_id": "A", "event": AE.EVENT_AWAIT, "awaiting": "B", "_seq": 1},
        {"timestamp": 2.0, "task_id": "B", "event": AE.EVENT_AWAIT, "awaiting": "A", "_seq": 2},
    ]
    g = build_async_dependency_graph(raw)
    assert g.has_edge("A", "B")
    assert g.has_edge("B", "A")


def test_detect_cycle_finds_loop() -> None:
    raw = [
        {"timestamp": 1.0, "task_id": "A", "event": AE.EVENT_AWAIT, "awaiting": "B", "_seq": 1},
        {"timestamp": 2.0, "task_id": "B", "event": AE.EVENT_AWAIT, "awaiting": "A", "_seq": 2},
    ]
    cyc = detect_async_wait_cycle(raw)
    assert cyc is not None
    assert len(cyc) >= 2


def test_no_cycle_when_acyclic() -> None:
    raw = [
        {"timestamp": 1.0, "task_id": "A", "event": AE.EVENT_AWAIT, "awaiting": "B", "_seq": 1},
    ]
    assert detect_async_wait_cycle(raw) is None
