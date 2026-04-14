"""Stable string ids for asyncio tasks."""

from __future__ import annotations

import asyncio
from typing import Any


def format_task_id(task: asyncio.Task[Any] | None) -> str:
    """Return a readable, unique label for a :class:`asyncio.Task`."""
    if task is None:
        return "unknown"
    try:
        name = task.get_name()
    except Exception:
        name = "Task"
    return f"{name}#{id(task)}"
