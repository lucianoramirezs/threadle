"""Scoped tracing sessions (context manager API)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from threadle.analysis.report import DeadlockReport, analyze_deadlocks
from threadle.core.tracker import reset_state
from threadle.timeline.recorder import get_events, start_tracing, stop_tracing


@dataclass
class Session:
    """
    Manage timeline tracing around a block of instrumented code.

    This does **not** auto-instrument ``threading.Lock``; use :class:`~threadle.locks.tracked_lock.TrackedLock`
    and decorators as usual. Call :meth:`analyze` at points where you want a deadlock snapshot.

    Parameters
    ----------
    trace_timeline
        If True, call :func:`~threadle.timeline.recorder.start_tracing` on enter and
        :func:`~threadle.timeline.recorder.stop_tracing` on exit.
    reset_tracker
        If True, clear global lock/thread tracker state on enter (use only in tests or
        isolated demos — **not** in production processes with live threads).
    clear_events_on_enter
        Passed to ``start_tracing(clear=...)`` when ``trace_timeline`` is True.
    """

    trace_timeline: bool = True
    reset_tracker: bool = False
    clear_events_on_enter: bool = True

    def __enter__(self) -> Session:
        if self.reset_tracker:
            reset_state()
        if self.trace_timeline:
            start_tracing(clear=self.clear_events_on_enter)
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        if self.trace_timeline:
            stop_tracing()

    def analyze(self) -> DeadlockReport:
        """Structured deadlock report for the **current** tracker snapshot."""
        return analyze_deadlocks()

    def timeline_events(self) -> list[dict[str, Any]]:
        """Events recorded since tracing started (if tracing was enabled)."""
        return cast(list[dict[str, Any]], list(get_events()))
