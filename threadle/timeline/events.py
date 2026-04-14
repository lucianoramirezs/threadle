"""Event type constants and helpers for timeline tracing."""

from __future__ import annotations

from typing import Literal, TypedDict

# Core lifecycle (threads)
EVENT_START = "start"
EVENT_END = "end"

# Lock lifecycle
EVENT_ACQUIRE_ATTEMPT = "acquire_attempt"
EVENT_ACQUIRE_SUCCESS = "acquire_success"
EVENT_RELEASE = "release"
EVENT_BLOCKED = "blocked"
# Emitted when a blocking wait ends without acquiring (timeout, non-blocking false, etc.)
EVENT_ACQUIRE_FAILED = "acquire_failed"

EventName = Literal[
    "start",
    "end",
    "acquire_attempt",
    "acquire_success",
    "release",
    "blocked",
    "acquire_failed",
]


class TimelineEvent(TypedDict, total=False):
    """Single timeline record (public fields)."""

    timestamp: float
    thread: str
    event: EventName
    lock: str | None


class TimelineEventInternal(TimelineEvent, total=False):
    """Event as stored internally (includes monotonic ordering key)."""

    _seq: int


def strip_internal_fields(event: TimelineEventInternal) -> TimelineEvent:
    """Return a copy suitable for external consumers (no ``_seq``)."""
    return {
        "timestamp": event["timestamp"],
        "thread": event["thread"],
        "event": event["event"],
        "lock": event.get("lock"),
    }
