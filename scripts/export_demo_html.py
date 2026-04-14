#!/usr/bin/env python3
"""Clear notebook outputs and export `notebook/demo.ipynb` to HTML via nbconvert.

Usage (from repo root):

    python scripts/export_demo_html.py

Requires dev extras: ``nbformat``, ``nbconvert``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebook" / "demo.ipynb"
HTML_OUT = ROOT / "demo.html"


def clear_outputs(path: Path) -> None:
    nb = json.loads(path.read_text(encoding="utf-8"))
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        cell["outputs"] = []
        cell["execution_count"] = None
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    if not NOTEBOOK.is_file():
        print(f"Missing {NOTEBOOK}", file=sys.stderr)
        return 1
    clear_outputs(NOTEBOOK)
    cmd = [
        sys.executable,
        "-m",
        "nbconvert",
        str(NOTEBOOK),
        "--to",
        "html",
        "--output",
        HTML_OUT.name,
        "--output-dir",
        str(HTML_OUT.parent),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Wrote {HTML_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
