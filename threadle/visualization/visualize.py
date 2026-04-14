"""Visualize tracked thread/lock relationships."""

from __future__ import annotations

from typing import Any

from threadle._mpl import setup_matplotlib_backend, show_figure

setup_matplotlib_backend()
import matplotlib.pyplot as plt
import networkx as nx

from threadle.analysis.graph import build_graph


def visualize(
    output_path: str | None = None,
    *,
    graph: nx.DiGraph | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 7),
    deadlock_report: Any | None = None,
) -> None:
    """Draw the wait-for :class:`~networkx.DiGraph` (directed edges with arrows).

    By default reads the live tracker via :func:`~threadle.analysis.graph.build_graph`.
    Pass ``graph=`` to render a snapshot captured earlier (e.g. before threads finish).

    Lock→thread edges use relation ``held_by`` (blue); thread→lock edges use
    ``waits_for`` (red). Other directed graphs (e.g. asyncio dependencies) are
    drawn with a single accent color and arrows.

    Parameters
    ----------
    output_path
        If set, save PNG instead of showing interactively.
    graph
        Optional pre-built graph; if ``None``, ``build_graph()`` is used.
    title
        Figure title.
    figsize
        Matplotlib figure size; larger values spread the layout visually.
    deadlock_report
        If provided and a cycle was found, those edges are drawn thicker.
    """
    g = graph if graph is not None else build_graph()
    n = max(len(g), 1)
    # Larger k spreads nodes (default 1/sqrt(n) is often too tight).
    k = max(2.5, 7.0 / (n**0.5))

    pos = nx.spring_layout(g, seed=42, k=k, iterations=80)

    fig, ax = plt.subplots(figsize=figsize)

    if len(g.nodes) == 0:
        ax.text(0.5, 0.5, "Empty graph (no locks/threads in snapshot).", ha="center", va="center", fontsize=11)
        ax.set_axis_off()
        if title:
            ax.set_title(title, fontsize=12)
        _finish_figure(fig, output_path)
        return

    # Node colors: wait-for graph uses kind; generic DiGraphs default to one hue.
    colors: list[str] = []
    for _, data in g.nodes(data=True):
        if data.get("kind") == "lock":
            colors.append("#60a5fa")
        elif data.get("kind") == "thread":
            colors.append("#f59e0b")
        else:
            colors.append("#c084fc")

    nx.draw_networkx_nodes(g, pos, node_color=colors, node_size=2600, ax=ax)
    nx.draw_networkx_labels(g, pos, font_size=9, ax=ax)

    # Split edges by relation when present (wait-for instrumented graph).
    has_relation = all("relation" in g.edges[u, v] for u, v in g.edges())
    if has_relation:
        held = [(u, v) for u, v, d in g.edges(data=True) if d.get("relation") == "held_by"]
        waits = [(u, v) for u, v, d in g.edges(data=True) if d.get("relation") == "waits_for"]
        _draw_dir_edges(g, pos, held, "#1d4ed8", ax, width=2.2)
        _draw_dir_edges(g, pos, waits, "#dc2626", ax, width=2.2)
    else:
        elist = list(g.edges())
        _draw_dir_edges(g, pos, elist, "#ea580c", ax, width=2.0)

    # Emphasize deadlock cycle if reported and edges exist in this graph.
    if deadlock_report is not None and getattr(deadlock_report, "found", False) and deadlock_report.raw_cycle:
        valid = set(g.nodes())
        cycle_edges: list[tuple[Any, Any]] = []
        for src, dst, _ in deadlock_report.raw_cycle:
            ss, dd = str(src), str(dst)
            if ss in valid and dd in valid:
                cycle_edges.append((ss, dd))
        if cycle_edges:
            _draw_dir_edges(g, pos, cycle_edges, "#7f1d1d", ax, width=3.5)

    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=12, pad=12)
    plt.tight_layout()
    _finish_figure(fig, output_path)


def _draw_dir_edges(
    g: nx.DiGraph,
    pos: dict,
    edgelist: list[tuple[Any, Any]],
    color: str,
    ax: Any,
    *,
    width: float,
) -> None:
    if not edgelist:
        return
    nx.draw_networkx_edges(
        g,
        pos,
        edgelist=edgelist,
        edge_color=color,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=22,
        width=width,
        min_source_margin=18,
        min_target_margin=20,
        connectionstyle="arc3,rad=0.08",
        ax=ax,
    )


def _finish_figure(fig: Any, output_path: str | None) -> None:
    if output_path:
        fig.savefig(output_path, bbox_inches="tight", dpi=140)
    else:
        show_figure(fig)
    plt.close(fig)
