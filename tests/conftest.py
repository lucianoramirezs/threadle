"""Shared pytest fixtures for threadle tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root (contains ``notebook/demo.ipynb``)."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def demo_notebook_path(repo_root: Path) -> Path:
    p = repo_root / "notebook" / "demo.ipynb"
    if not p.is_file():
        pytest.skip(
            "notebook/demo.ipynb ausente; genera: python scripts/generate_notebook_demo.py"
        )
    return p
