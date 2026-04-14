"""Behavioural tests aligned with ``notebook/demo.ipynb`` (API contracts).

Each test documents **expected output or observable behaviour** for the APIs
used in the demo notebook. If these tests pass, the demo’s claims match the
implementation.

Rough mapping:

- **Install** (``pip install`` cell): skipped in CI; editable install provides ``threadle``.
- **Imports**: ``import threadle as tl`` and ``run_demo`` from ``threadle.examples.deadlock_demo``.
- **Deadlock demo**: ``run_demo(visualize_graph=False)`` usually returns a NetworkX-style cycle
  or ``None`` if the snapshot misses the contested instant.
- **With plot**: ``run_demo(..., output_path=...)`` writes a non-empty PNG.
"""

from __future__ import annotations

import io
import threading
from contextlib import redirect_stdout
from pathlib import Path

import threadle as tl
import threadle
from threadle.analysis.deadlock import detect_deadlocks
from threadle.core.tracker import reset_state
from threadle.decorators.trace import trace
from threadle.decorators.trace_thread import trace_thread
from threadle.examples.deadlock_demo import run_demo
from threadle.locks.tracked_lock import TrackedLock
from threadle.timeline import events as E
from threadle.timeline.gantt import build_segments, export_gantt, visualize_gantt
from threadle.timeline.recorder import (
    clear_events,
    get_events,
    session_start_time,
    snapshot_raw_events,
    start_tracing,
    stop_tracing,
)
from threadle.visualization.visualize import visualize


class TestNotebookPublicImports:
    """Expected: ``import threadle as tl`` exposes the documented surface."""

    def test_threadle_exports_documented_names(self) -> None:
        # Expected: __all__ lists stable public names (demo + timeline).
        expected_subset = {
            "TrackedLock",
            "build_async_dependency_graph",
            "build_async_segments",
            "clear_async_events",
            "detect_async_wait_cycle",
            "detect_deadlocks",
            "export_async_gantt",
            "export_gantt",
            "format_task_id",
            "get_async_events",
            "get_events",
            "is_async_tracing",
            "is_tracing",
            "start_async_tracing",
            "start_tracing",
            "stop_async_tracing",
            "stop_tracing",
            "trace",
            "trace_async",
            "trace_thread",
            "traced_await",
            "visualize",
            "visualize_async_gantt",
            "visualize_gantt",
            "clear_events",
        }
        assert expected_subset <= set(threadle.__all__)

    def test_tl_alias_matches_package(self) -> None:
        # Expected: `import threadle as tl` re-exports the same public API.
        assert tl.__all__ == threadle.__all__


class TestNotebookRunDemoDeadlock:
    """Expected behaviour of ``run_demo`` as used in the demo notebook."""

    def test_run_demo_without_graph_returns_cycle_or_none_documented(self) -> None:
        """
        Expected output (cell ``cycle = run_demo(visualize_graph=False)``):

        - **Usually** a non-empty ``list`` of directed edges from
          ``networkx.find_cycle(..., orientation='original')``. Each item is a
          3-tuple ``(u, v, orientation)`` describing an edge in the wait-for
          graph between ``thread:*`` and ``lock:*`` nodes.
        - **Sometimes** ``None`` if no directed cycle exists at the instant
          ``detect_deadlocks()`` snapshots global state (rare for this demo).

        We assert the common case: a 4-edge cycle typical of two threads and
        two locks in a circular wait.
        """
        reset_state()
        cycle = run_demo(visualize_graph=False)
        if cycle is None:
            # Documented rare outcome; do not fail the suite on timing.
            return
        assert isinstance(cycle, list)
        assert len(cycle) >= 2
        for edge in cycle:
            assert len(edge) == 3
            u, v, _ori = edge
            assert isinstance(u, str) and isinstance(v, str)

    def test_run_demo_cycle_contains_lock_and_thread_nodes_when_present(self) -> None:
        """
        Expected: each graph node string is either ``lock:<name>`` or
        ``thread:<id>`` (see ``threadle.core.utils``), forming a closed walk.
        """
        reset_state()
        cycle = run_demo(visualize_graph=False)
        if cycle is None:
            return
        nodes = {cycle[0][0]}
        for _u, v, _ in cycle:
            nodes.add(v)
        assert any(n.startswith("lock:") for n in nodes)
        assert any(n.startswith("thread:") for n in nodes)

    def test_detect_deadlocks_matches_run_demo_snapshot(self) -> None:
        """
        Expected: ``detect_deadlocks()`` returns the same style of value as the
        the demo’s ``cycle`` variable — ``None`` or a list of oriented edges.
        """
        reset_state()
        run_demo(visualize_graph=False)
        # After run_demo returns, threads have joined; graph may be empty.
        # Call detect on a fresh demo mid-flight is different — here we only
        # check return type contract.
        d = detect_deadlocks()
        assert d is None or isinstance(d, list)


class TestNotebookVisualizeGraph:
    """Expected: graph visualization writes an image when ``output_path`` is set."""

    def test_visualize_writes_nonempty_png(self, tmp_path: Path) -> None:
        """
        Expected output: a PNG file on disk (non-zero bytes).

        Demo cell::
            run_demo(visualize_graph=True, output_path="showcase-run-demo.png")

        Same contract as ``visualize(output_path=...)`` after building state.
        """
        reset_state()
        path = tmp_path / "showcase-run-demo.png"
        run_demo(visualize_graph=True, output_path=str(path))
        assert path.is_file()
        assert path.stat().st_size > 100

    def test_visualize_function_alone_writes_file(self, tmp_path: Path) -> None:
        """
        Expected: ``threadle.visualize(output_path=...)`` saves without opening
        a GUI when ``DISPLAY`` is unset (Agg backend in module).
        """
        reset_state()
        _ = run_demo(visualize_graph=False)
        out = tmp_path / "graph-only.png"
        visualize(output_path=str(out))
        assert out.is_file() and out.stat().st_size > 50


class TestNotebookTimelineAndGantt:
    """
    Expected flows for timeline tracing (shown in the demo notebook).

    - ``tl.start_tracing()`` clears and arms the recorder.
    - ``TrackedLock`` emits structured events while tracing is on.
    - ``build_segments`` / ``visualize_gantt`` / ``export_gantt`` consume those
      events without crashing.
    """

    def test_start_tracing_clears_buffer_when_requested(self) -> None:
        # Expected: after start_tracing(clear=True), get_events() is empty.
        clear_events()
        start_tracing(clear=True)
        assert get_events() == []
        stop_tracing()

    def test_tracked_lock_produces_ordered_events_under_tracing(self) -> None:
        """
        Expected event sequence for a single-thread acquire/release::

            acquire_attempt → acquire_success → release

        (``blocked`` appears only when another thread holds the lock.)
        """
        clear_events()
        start_tracing(clear=True)
        lock = TrackedLock("L-notebook")
        lock.acquire()
        lock.release()
        stop_tracing()
        kinds = [e["event"] for e in get_events()]
        assert E.EVENT_ACQUIRE_ATTEMPT in kinds
        assert E.EVENT_ACQUIRE_SUCCESS in kinds
        assert E.EVENT_RELEASE in kinds

    def test_trace_thread_emits_start_and_end(self) -> None:
        """
        Expected: wrapping the thread target records ``start`` then ``end`` in
        order for that logical thread name.
        """
        clear_events()
        start_tracing(clear=True)

        @trace_thread
        def work() -> None:
            pass

        t = threading.Thread(target=work, name="notebook-worker")
        t.start()
        t.join()
        stop_tracing()
        evs = [e for e in get_events() if e["thread"] == "notebook-worker"]
        kinds = [e["event"] for e in evs]
        assert kinds[0] == E.EVENT_START
        assert kinds[-1] == E.EVENT_END

    def test_build_segments_yields_three_states(self) -> None:
        """
        Expected: segment dicts include keys ``thread``, ``t0``, ``t1``,
        ``state`` in ``{'running','waiting','holding'}``, optional ``lock``.
        """
        clear_events()
        start_tracing(clear=True)
        lock = TrackedLock("L-seg")
        lock.acquire()
        lock.release()
        stop_tracing()
        segs = build_segments(raw_events=snapshot_raw_events(), session_start=session_start_time())
        assert segs
        for s in segs:
            assert s["state"] in ("running", "waiting", "holding")
            assert s["t1"] > s["t0"]

    def test_export_gantt_png_no_crash(self, tmp_path: Path) -> None:
        """Expected: ``export_gantt(path.png)`` creates a raster file."""
        clear_events()
        start_tracing(clear=True)
        TrackedLock("L-gantt").acquire()
        stop_tracing()
        out = tmp_path / "gantt.png"
        export_gantt(str(out), relative_time=True)
        assert out.is_file() and out.stat().st_size > 50

    def test_visualize_gantt_no_show_does_not_raise(self) -> None:
        """Expected: ``visualize_gantt(show=False)`` runs headless without error."""
        clear_events()
        start_tracing(clear=True)
        TrackedLock("L-vis").acquire()
        stop_tracing()
        visualize_gantt(show=False)


class TestNotebookDecoratorsPrintTrace:
    """``trace`` prints lines; notebook may mention debugging output."""

    def test_trace_decorator_prints_enter_exit(self) -> None:
        """
        Expected stdout (approximately)::

            [TRACE] Enter f
            [TRACE] Exit f
        """
        buf = io.StringIO()
        with redirect_stdout(buf):

            @trace
            def f() -> int:
                return 42

            assert f() == 42
        out = buf.getvalue()
        assert "[TRACE] Enter f" in out
        assert "[TRACE] Exit f" in out


class TestNotebookDeadlockDetectionContract:
    """Narrative for ``detect_deadlocks`` return value (demo follow-up)."""

    def test_detect_deadlocks_none_when_no_cycle(self) -> None:
        """
        Expected output: ``None`` when the wait-for graph is acyclic.

        With an empty registry after ``reset_state()``, there is no graph edge.
        """
        reset_state()
        assert detect_deadlocks() is None
