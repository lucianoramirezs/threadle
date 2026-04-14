"""threadle public API.

Asyncio-related symbols are loaded on first access (``__getattr__``) so
``import threadle`` stays robust and attributes like ``clear_async_events``
resolve whenever ``threadle.asyncio_trace`` is present on disk.
"""

from __future__ import annotations

import importlib
from typing import Any

from threadle.analysis.deadlock import detect_deadlocks
from threadle.analysis.report import DeadlockReport, analyze_deadlocks
from threadle.analysis.snapshot import (
    export_debug_bundle_dict,
    export_debug_bundle_json,
    export_tracker_state_dict,
)
from threadle.decorators.trace import trace
from threadle.decorators.trace_thread import trace_thread
from threadle.locks.tracked_lock import TrackedLock
from threadle.session import Session
from threadle.timeline.gantt import export_gantt, visualize_gantt
from threadle.timeline.recorder import clear_events, get_events, is_tracing, start_tracing, stop_tracing
from threadle.visualization.visualize import visualize

# (module path, attribute name) for lazy asyncio exports
_LAZY_ASYNC: dict[str, tuple[str, str]] = {
    "build_async_dependency_graph": ("threadle.asyncio_trace.graph", "build_async_dependency_graph"),
    "build_async_segments": ("threadle.asyncio_trace.gantt", "build_async_segments"),
    "clear_async_events": ("threadle.asyncio_trace.recorder", "clear_async_events"),
    "detect_async_wait_cycle": ("threadle.asyncio_trace.deadlock_async", "detect_async_wait_cycle"),
    "export_async_gantt": ("threadle.asyncio_trace.gantt", "export_async_gantt"),
    "format_task_id": ("threadle.asyncio_trace.task_id", "format_task_id"),
    "get_async_events": ("threadle.asyncio_trace.recorder", "get_async_events"),
    "is_async_tracing": ("threadle.asyncio_trace.recorder", "is_async_tracing"),
    "start_async_tracing": ("threadle.asyncio_trace.recorder", "start_async_tracing"),
    "stop_async_tracing": ("threadle.asyncio_trace.recorder", "stop_async_tracing"),
    "trace_async": ("threadle.asyncio_trace.decorators", "trace_async"),
    "traced_await": ("threadle.asyncio_trace.decorators", "traced_await"),
    "visualize_async_gantt": ("threadle.asyncio_trace.gantt", "visualize_async_gantt"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_ASYNC:
        mod_path, attr = _LAZY_ASYNC[name]
        mod = importlib.import_module(mod_path)
        obj = getattr(mod, attr)
        globals()[name] = obj
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = [
    "DeadlockReport",
    "Session",
    "TrackedLock",
    "analyze_deadlocks",
    "build_async_dependency_graph",
    "build_async_segments",
    "clear_async_events",
    "clear_events",
    "detect_async_wait_cycle",
    "detect_deadlocks",
    "export_async_gantt",
    "export_debug_bundle_dict",
    "export_debug_bundle_json",
    "export_tracker_state_dict",
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
]
