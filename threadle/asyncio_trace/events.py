"""Event types for asyncio task timeline tracing."""

from __future__ import annotations

from typing import Literal, TypedDict

EVENT_START = "start"
EVENT_AWAIT = "await"
EVENT_RESUME = "resume"
EVENT_END = "end"

AsyncEventName = Literal["start", "await", "resume", "end"]


class AsyncTimelineEvent(TypedDict, total=False):
    """Public async timeline record."""

    timestamp: float
    task_id: str
    event: AsyncEventName
    awaiting: str | None


class AsyncTimelineEventInternal(AsyncTimelineEvent, total=False):
    _seq: int


def strip_async_internal(event: AsyncTimelineEventInternal) -> AsyncTimelineEvent:
    return {
        "timestamp": event["timestamp"],
        "task_id": event["task_id"],
        "event": event["event"],
        "awaiting": event.get("awaiting"),
    }
