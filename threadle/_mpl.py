"""Matplotlib backend and figure display (notebook-safe, headless-safe).

Must run :func:`setup_matplotlib_backend` before ``import matplotlib.pyplot`` in
callers so Jupyter is not stuck on Agg when ``DISPLAY`` is unset.
"""

from __future__ import annotations

import os
from typing import Any


def setup_matplotlib_backend() -> None:
    """Use Agg only for headless non-IPython; in Jupyter prefer ``matplotlib_inline``."""
    import matplotlib

    try:
        from IPython import get_ipython

        if get_ipython() is not None:
            try:
                matplotlib.use("module://matplotlib_inline.backend_inline")
            except Exception:
                pass
            return
    except ImportError:
        pass

    if os.environ.get("DISPLAY", "") == "":
        matplotlib.use("Agg")


def show_figure(fig: Any) -> None:
    """Embed ``fig`` in notebooks; otherwise :func:`matplotlib.pyplot.show`."""
    try:
        from IPython import get_ipython
        from IPython.display import display

        if get_ipython() is not None:
            display(fig)
            return
    except ImportError:
        pass
    import matplotlib.pyplot as plt

    plt.show()
