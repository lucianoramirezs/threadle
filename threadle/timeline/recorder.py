"""Thread-safe global event recorder for timeline / Gantt views."""

from __future__ import annotations

import threading
import time

from threadle.timeline.events import (
    TimelineEvent,
    TimelineEventInternal,
    strip_internal_fields,
)

_lock = threading.Lock()
_events: list[TimelineEventInternal] = []
_seq: int = 0
_tracing: bool = False
_session_start: float | None = None


def start_tracing(*, clear: bool = True) -> None:
    """Begin recording timeline events (uses ``time.perf_counter()``)."""
    global _tracing, _seq, _session_start
    with _lock:
        _tracing = True
        if clear:
            _events.clear()
            _seq = 0
        _session_start = time.perf_counter()


def stop_tracing() -> None:
    """Stop recording new events (existing buffer is kept)."""
    global _tracing
    with _lock:
        _tracing = False


def is_tracing() -> bool:
    return _tracing


def clear_events() -> None:
    """Remove all recorded events and reset ordering (does not change tracing flag)."""
    global _seq, _session_start
    with _lock:
        _events.clear()
        _seq = 0
        _session_start = time.perf_counter()


def record_event(
    event: str,
    lock: str | None = None,
    *,
    thread_name: str | None = None,
) -> None:
    """Append one event if tracing is enabled. Thread-safe and low overhead when off."""
    if not _tracing:
        return
    tname = thread_name if thread_name is not None else threading.current_thread().name
    global _seq
    with _lock:
        _seq += 1
        rec: TimelineEventInternal = {
            "timestamp": time.perf_counter(),
            "thread": tname,
            "event": event,  # type: ignore[assignment]
            "lock": lock,
            "_seq": _seq,
        }
        _events.append(rec)


def get_events(*, strip_internal: bool = True) -> list[TimelineEvent] | list[TimelineEventInternal]:
    """Return a snapshot of recorded events, ordered by (timestamp, sequence)."""
    with _lock:
        snapshot = list(_events)
    snapshot.sort(key=lambda e: (e["timestamp"], e.get("_seq", 0)))
    if strip_internal:
        return [strip_internal_fields(e) for e in snapshot]  # type: ignore[return-value]
    return snapshot


def session_start_time() -> float | None:
    """Perf-counter value when :func:`start_tracing` last ran (with ``clear=True``)."""
    with _lock:
        return _session_start


def snapshot_raw_events() -> list[TimelineEventInternal]:
    """Internal: sorted events including ``_seq`` for deterministic processing."""
    with _lock:
        snapshot = list(_events)
    snapshot.sort(key=lambda e: (e["timestamp"], e.get("_seq", 0)))
    return snapshot
