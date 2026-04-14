"""Decorator to record thread execution boundaries in the timeline."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from threadle.timeline import events as E
from threadle.timeline.recorder import is_tracing, record_event

F = TypeVar("F", bound=Callable[..., Any])


def trace_thread(fn: F) -> F:
    """
    Wrap a thread *target* callable to emit ``start`` / ``end`` timeline events.

    Use with ``threading.Thread(target=trace_thread(work), ...)``.
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if is_tracing():
            record_event(E.EVENT_START, None)
        try:
            return fn(*args, **kwargs)
        finally:
            if is_tracing():
                record_event(E.EVENT_END, None)

    return wrapper  # type: ignore[return-value]
