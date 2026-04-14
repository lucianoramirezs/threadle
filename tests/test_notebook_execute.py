"""Execute ``notebook/demo.ipynb`` programmatically (integration test).

Expected outcome when this test runs:

- All code cells execute without raising (we skip ``%pip`` / ``!pip`` under test).
- Artefactos bajo ``outputs/`` respecto al cwd de ejecución (``tmp_path``).

Requires dev extras: ``nbformat``, ``nbclient``, ``ipykernel``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")
nbclient = pytest.importorskip("nbclient")


def _coerce_code_sources_to_str(nb: dict) -> None:
    """nbclient expects ``cell.source`` to be a string for code cells."""
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        if isinstance(src, list):
            cell["source"] = "".join(src)


def _normalize_sources(nb: dict) -> None:
    """Make notebook sources executable in CI (skip pip)."""
    _coerce_code_sources_to_str(nb)
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        text = src if isinstance(src, str) else "".join(src)
        stripped = text.strip()
        if stripped.startswith("!pip") or stripped.startswith("%pip"):
            cell["source"] = (
                "# skipped in automated test: environment already has threadle installed\n"
                "pass\n"
            )


def test_demo_notebook_executes(tmp_path: Path, demo_notebook_path: Path) -> None:
    """
    Expected: running the demo notebook end-to-end completes without errors.

    Side effects in ``tmp_path/outputs/`` (cwd = ``tmp_path`` for nbclient).
    """
    nb = json.loads(demo_notebook_path.read_text(encoding="utf-8"))
    _normalize_sources(nb)
    notebook = nbformat.from_dict(nb)

    client = nbclient.NotebookClient(
        notebook,
        timeout=180,
        kernel_name="python3",
    )
    client.execute(cwd=str(tmp_path))

    out = tmp_path / "outputs"
    showcase = out / "showcase-run-demo.png"
    assert showcase.is_file(), "Expected outputs/showcase-run-demo.png from run_demo cell"
    assert showcase.stat().st_size > 100
