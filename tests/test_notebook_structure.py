"""Structural checks for ``notebook/demo.ipynb``.

These tests do not execute the notebook; they verify that the showcase still
contains the documented API snippets and scenario markers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _load_nb(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_demo_notebook_exists(demo_notebook_path: Path) -> None:
    assert demo_notebook_path.is_file()


def test_demo_notebook_is_valid_nbformat_v4(demo_notebook_path: Path) -> None:
    nb = _load_nb(demo_notebook_path)
    assert nb.get("nbformat") == 4
    assert "cells" in nb and isinstance(nb["cells"], list)
    assert len(nb["cells"]) >= 1


def _all_cell_text(nb: dict) -> str:
    parts: list[str] = []
    for c in nb["cells"]:
        if c.get("cell_type") not in ("code", "markdown"):
            continue
        src = c.get("source", "")
        parts.append(src if isinstance(src, str) else "".join(src))
    return "\n".join(parts)


@pytest.mark.parametrize(
    "needle",
    [
        "pip install threadle",
        "import threadle as tl",
        "from threadle.examples.deadlock_demo import run_demo",
        "run_demo(",
        "outputs/",
        "showcase-run-demo.png",
        "scenario-a-wait-graph.png",
        "scenario-b-wait-graph.png",
        "Automated validation",
        "Escenario A",
        "Escenario B",
        "Escenario C",
        "Escenario K",
        "export_debug_bundle_json",
        "Session",
        "analyze_deadlocks",
        "visualize_gantt",
        "export_gantt",
        "trace_thread",
        "demo-wait-graph.png",
        "demo-gantt.png",
        "GIL",
        "start_async_tracing",
        "visualize_async_gantt",
        "demo-async-gantt.png",
        "threadle.cli.main",
    ],
)
def test_demo_contains_documented_cells(demo_notebook_path: Path, needle: str) -> None:
    nb = _load_nb(demo_notebook_path)
    joined = _all_cell_text(nb)
    assert needle in joined
