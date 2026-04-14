"""Serialize tracker state for logs, CI artifacts, and bug reports."""

from __future__ import annotations

import json
from typing import Any

from threadle.analysis.report import DeadlockReport, analyze_deadlocks
from threadle.core.tracker import snapshot_state


def _lock_info_to_dict(name: str, info: Any) -> dict[str, Any]:
    return {
        "name": name,
        "owner": info.owner,
        "waiting": sorted(info.waiting) if info.waiting else [],
    }


def _thread_info_to_dict(ident: int, info: Any) -> dict[str, Any]:
    return {
        "ident": ident,
        "name": info.name,
        "waiting_for": info.waiting_for,
    }


def export_tracker_state_dict() -> dict[str, Any]:
    """Return the current lock/thread tracker state as JSON-friendly dicts."""
    state = snapshot_state()
    return {
        "locks": {
            name: _lock_info_to_dict(name, li) for name, li in state["locks"].items()
        },
        "threads": {
            str(ident): _thread_info_to_dict(ident, ti)
            for ident, ti in state["threads"].items()
        },
    }


def export_debug_bundle_dict(*, include_deadlock: bool = True) -> dict[str, Any]:
    """
    Single payload for operators: tracker state plus structured deadlock analysis.

    Suitable for writing to a CI artifact or attaching to an issue.
    """
    bundle: dict[str, Any] = {"tracker": export_tracker_state_dict()}
    if include_deadlock:
        rep: DeadlockReport = analyze_deadlocks()
        bundle["deadlock"] = rep.to_dict()
    return bundle


def export_debug_bundle_json(*, indent: int | None = 2, include_deadlock: bool = True) -> str:
    return json.dumps(
        export_debug_bundle_dict(include_deadlock=include_deadlock),
        indent=indent,
    )
