"""``trace_async`` and ``traced_await`` helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from threadle.asyncio_trace import events as AE
from threadle.asyncio_trace.recorder import is_async_tracing, record_async_event
from threadle.asyncio_trace.task_id import format_task_id

T = TypeVar("T")


def trace_async(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorate a coroutine function to record ``start`` / ``end`` for its task.

    Run the coroutine under an active event loop so :func:`asyncio.current_task`
    is set (e.g. ``asyncio.run``, ``await`` from another task).
    """

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        task = asyncio.current_task()
        tid = format_task_id(task)
        if is_async_tracing():
            record_async_event(AE.EVENT_START, tid, awaiting=None)
        try:
            return await fn(*args, **kwargs)
        finally:
            if is_async_tracing():
                record_async_event(AE.EVENT_END, tid, awaiting=None)

    return wrapper


async def traced_await(
    awaitable: Awaitable[T],
    *,
    awaiting: str | None = None,
) -> T:
    """
    ``await`` with timeline events: records ``await`` before suspending and
    ``resume`` after the awaitable completes (including if it raises).

    ``awaiting`` should name the logical dependency (e.g. another task id from
    :func:`format_task_id`) for dependency graphs.
    """
    task = asyncio.current_task()
    tid = format_task_id(task)
    if is_async_tracing():
        record_async_event(AE.EVENT_AWAIT, tid, awaiting=awaiting)
    try:
        return await awaitable  # type: ignore[no-any-return]
    finally:
        if is_async_tracing():
            record_async_event(AE.EVENT_RESUME, tid, awaiting=None)
