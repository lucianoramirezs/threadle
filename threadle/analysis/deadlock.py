"""Deadlock detection helpers."""

from __future__ import annotations

from typing import Any

from threadle.analysis.report import analyze_deadlocks


def detect_deadlocks() -> list[tuple[Any, Any, Any]] | None:
    """
    Return a raw NetworkX-style cycle, or ``None`` if no cycle exists.

    Prefer :func:`~threadle.analysis.report.analyze_deadlocks` when you need a summary,
    JSON, or stable structured fields.
    """
    rep = analyze_deadlocks()
    return rep.raw_cycle if rep.found else None
