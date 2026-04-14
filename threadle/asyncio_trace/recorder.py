"""Global async event buffer (parallel to thread timeline, separate storage)."""

from __future__ import annotations

import threading
import time

from threadle.asyncio_trace.events import (
    AsyncTimelineEvent,
    AsyncTimelineEventInternal,
    strip_async_internal,
)

_lock = threading.Lock()
_events: list[AsyncTimelineEventInternal] = []
_seq: int = 0
_tracing: bool = False
_session_start: float | None = None


def start_async_tracing(*, clear: bool = True) -> None:
    """Begin recording asyncio timeline events (``time.perf_counter()``)."""
    global _tracing, _seq, _session_start
    with _lock:
        _tracing = True
        if clear:
            _events.clear()
            _seq = 0
        _session_start = time.perf_counter()


def stop_async_tracing() -> None:
    """Stop recording new async events (buffer is kept)."""
    global _tracing
    with _lock:
        _tracing = False


def is_async_tracing() -> bool:
    return _tracing


def clear_async_events() -> None:
    """Clear buffer and reset ordering."""
    global _seq, _session_start
    with _lock:
        _events.clear()
        _seq = 0
        _session_start = time.perf_counter()


def record_async_event(
    event: str,
    task_id: str,
    *,
    awaiting: str | None = None,
) -> None:
    if not _tracing:
        return
    global _seq
    with _lock:
        _seq += 1
        rec: AsyncTimelineEventInternal = {
            "timestamp": time.perf_counter(),
            "task_id": task_id,
            "event": event,  # type: ignore[assignment]
            "awaiting": awaiting,
            "_seq": _seq,
        }
        _events.append(rec)


def get_async_events(*, strip_internal: bool = True) -> list[AsyncTimelineEvent] | list[AsyncTimelineEventInternal]:
    with _lock:
        snapshot = list(_events)
    snapshot.sort(key=lambda e: (e["timestamp"], e.get("_seq", 0)))
    if strip_internal:
        return [strip_async_internal(e) for e in snapshot]  # type: ignore[return-value]
    return snapshot


def async_session_start_time() -> float | None:
    with _lock:
        return _session_start


def snapshot_raw_async_events() -> list[AsyncTimelineEventInternal]:
    with _lock:
        snapshot = list(_events)
    snapshot.sort(key=lambda e: (e["timestamp"], e.get("_seq", 0)))
    return snapshot
