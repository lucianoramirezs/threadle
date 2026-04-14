"""Additional documented tests for demo-adjacent APIs (graph + CLI).

Expected outputs are spelled out so notebook authors can cross-check prose
against executable assertions.
"""

from __future__ import annotations

import subprocess
import sys

import networkx as nx

from threadle.analysis.graph import build_graph
from threadle.analysis.deadlock import detect_deadlocks
from threadle.core.tracker import register_lock, register_thread, reset_state, set_lock_owner
from threadle.core.utils import lock_node_id, thread_node_id
from threadle.timeline import events as E
from threadle.timeline.recorder import clear_events, get_events, record_event, start_tracing, stop_tracing


class TestBuildGraphNotebookContract:
    """``build_graph()`` shapes the wait-for graph used before deadlock detection."""

    def test_expected_edge_directions_after_manual_registration(self) -> None:
        """
        Expected graph semantics:

        - Edge ``lock:L -> thread:T`` means **L is held by** T.
        - Edge ``thread:T -> lock:L`` means **T waits for** L.
        """
        reset_state()
        register_lock("L1")
        register_thread(7, "worker")
        set_lock_owner("L1", 7)
        g = build_graph()
        assert g.has_edge(lock_node_id("L1"), thread_node_id(7))
        assert g.number_of_nodes() >= 2

    def test_build_graph_returns_digraph(self) -> None:
        # Expected: NetworkX directed graph (not MultiDiGraph) for simple MVP.
        reset_state()
        g = build_graph()
        assert isinstance(g, nx.DiGraph)


class TestDetectDeadlocksNotebookContract:
    """``detect_deadlocks()`` wraps ``networkx.find_cycle``."""

    def test_find_cycle_returns_none_on_empty_graph(self) -> None:
        # Expected: no exception; ``None`` when acyclic / empty.
        reset_state()
        assert detect_deadlocks() is None


class TestTimelineEventDictShape:
    """Event records match the dictionary shape described in the timeline docs."""

    def test_get_events_strips_internal_seq(self) -> None:
        # Expected: public ``get_events()`` entries have no ``_seq`` key.
        clear_events()
        start_tracing(clear=True)
        record_event(E.EVENT_START, None)
        stop_tracing()
        ev = get_events()[0]
        assert "_seq" not in ev
        assert set(ev.keys()) >= {"timestamp", "thread", "event", "lock"}


class TestCliEntrypointSmoke:
    """CLI is optional for notebooks but useful to document."""

    def test_threadle_help_exits_zero(self) -> None:
        """
        Expected process output:

        - Exit code 0
        - Stdout mentions ``threadle`` or subcommands (implementation detail).
        """
        proc = subprocess.run(
            [sys.executable, "-m", "threadle.cli.main", "-h"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert "threadle" in (proc.stdout + proc.stderr).lower() or proc.stdout
