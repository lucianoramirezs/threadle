"""Timeline tracing: events, recording, and Gantt visualization."""

from threadle.timeline.gantt import build_segments, export_gantt, visualize_gantt
from threadle.timeline.recorder import (
    clear_events,
    get_events,
    is_tracing,
    start_tracing,
    stop_tracing,
)

__all__ = [
    "build_segments",
    "clear_events",
    "export_gantt",
    "get_events",
    "is_tracing",
    "start_tracing",
    "stop_tracing",
    "visualize_gantt",
]
