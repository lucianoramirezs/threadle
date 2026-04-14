"""Build timeline segments from events and render Gantt-style charts."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Literal

GanttPalette = Literal["per_thread", "semantic"]

from threadle._mpl import setup_matplotlib_backend, show_figure

setup_matplotlib_backend()
import matplotlib.pyplot as plt

from threadle.analysis.graph import build_graph
from threadle.timeline import events as E
from threadle.timeline.recorder import session_start_time, snapshot_raw_events

StateKind = Literal["running", "waiting", "holding"]

STATE_COLORS: dict[StateKind, str] = {
    "running": "#2ca02c",
    "waiting": "#d62728",
    "holding": "#1f77b4",
}

# Distinct accent per thread row (Gantt “una fila por thread”, estilo docencia)
_TASK_ROW_COLORS: list[str] = [
    "#22d3ee",  # cyan
    "#f43f5e",  # red
    "#fb923c",  # orange
    "#a78bfa",  # violet
    "#4ade80",  # green
    "#fbbf24",  # amber
]

_CPU_BUSY_COLOR = "#22c55e"
_WAIT_HATCH = "///"
_WAIT_FACE = "#1e3a5f"
_WAIT_EDGE = "#93c5fd"


def _compute_mode(*, wait_lock: str | None, held: set[str]) -> StateKind:
    if wait_lock is not None:
        return "waiting"
    if held:
        return "holding"
    return "running"


def _segment_lock_label(mode: StateKind, wait_lock: str | None, held: set[str]) -> str | None:
    if mode == "waiting" and wait_lock is not None:
        return wait_lock
    if mode == "holding" and held:
        return ",".join(sorted(held))
    return None


def build_segments(
    raw_events: list[dict[str, Any]] | None = None,
    *,
    session_start: float | None = None,
) -> list[dict[str, Any]]:
    """
    Convert ordered timeline events into contiguous segments per thread.

    Each segment: ``thread``, ``t0``, ``t1``, ``state`` (running|waiting|holding),
    optional ``lock`` (context label), and ``t0_rel`` / ``t1_rel`` when session_start is known.
    """
    if raw_events is None:
        raw_events = snapshot_raw_events()
    if not raw_events:
        return []

    if session_start is None:
        session_start = session_start_time()

    events_sorted = sorted(raw_events, key=lambda e: (e["timestamp"], e.get("_seq", 0)))
    t_max = max(e["timestamp"] for e in events_sorted)

    held: dict[str, set[str]] = defaultdict(set)
    wait_lock: dict[str, str | None] = defaultdict(lambda: None)
    last_t: dict[str, float] = {}
    mode: dict[str, StateKind] = {}
    ended: set[str] = set()

    segments: list[dict[str, Any]] = []

    def append_segment(th: str, t0: float, t1: float, st: StateKind) -> None:
        if t1 <= t0:
            return
        lab = _segment_lock_label(st, wait_lock.get(th), held[th])
        seg: dict[str, Any] = {
            "thread": th,
            "t0": t0,
            "t1": t1,
            "state": st,
            "lock": lab,
        }
        if session_start is not None:
            seg["t0_rel"] = t0 - session_start
            seg["t1_rel"] = t1 - session_start
        segments.append(seg)

    for ev in events_sorted:
        th = ev["thread"]
        t = float(ev["timestamp"])
        kind = ev["event"]
        lock = ev.get("lock")

        if th in ended:
            continue

        if th in last_t:
            append_segment(th, last_t[th], t, mode[th])

        # State transitions
        if kind == E.EVENT_START:
            held[th].clear()
            wait_lock[th] = None
        elif kind == E.EVENT_END:
            ended.add(th)
            last_t.pop(th, None)
            mode.pop(th, None)
            continue
        elif kind == E.EVENT_ACQUIRE_ATTEMPT:
            pass
        elif kind == E.EVENT_BLOCKED:
            wait_lock[th] = lock  # type: ignore[assignment]
        elif kind == E.EVENT_ACQUIRE_SUCCESS:
            if lock and wait_lock.get(th) == lock:
                wait_lock[th] = None
            if lock:
                held[th].add(lock)
        elif kind == E.EVENT_RELEASE:
            if lock:
                held[th].discard(lock)
        elif kind == E.EVENT_ACQUIRE_FAILED:
            wait_lock[th] = None

        mode[th] = _compute_mode(wait_lock=wait_lock.get(th), held=held[th])
        last_t[th] = t

    for th, t0 in list(last_t.items()):
        if th in ended:
            continue
        append_segment(th, t0, t_max, mode[th])

    segments.sort(key=lambda s: (s["t0"], s["thread"]))
    return segments


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: x[0])
    merged: list[tuple[float, float]] = [intervals[0]]
    for a, b in intervals[1:]:
        la, lb = merged[-1]
        if a <= lb + 1e-12:
            merged[-1] = (la, max(lb, b))
        else:
            merged.append((a, b))
    return merged


def _apply_gantt_theme(fig: Any, ax: Any, *, theme: str) -> None:
    if theme == "dark":
        bg = "#0f172a"
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)
        ax.tick_params(colors="#e2e8f0")
        ax.xaxis.label.set_color("#e2e8f0")
        ax.yaxis.label.set_color("#e2e8f0")
        if ax.title.get_text():
            ax.title.set_color("#f1f5f9")
        for spine in ax.spines.values():
            spine.set_color("#475569")
    else:
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")


def _plot_thread_gantt_axes(
    ax: Any,
    segs: list[dict[str, Any]],
    *,
    t0_key: str,
    t1_key: str,
    threads_sorted: list[str],
    cpu_row: bool,
    palette: GanttPalette = "per_thread",
) -> None:
    """Draw one horizontal lane per thread; optional aggregate CPU row at the bottom."""
    n_threads = len(threads_sorted)
    y_index = {name: i for i, name in enumerate(threads_sorted)}
    row_height = 0.55
    y_cpu = n_threads

    for s in segs:
        th = s["thread"]
        if th not in y_index:
            continue
        yi = y_index[th]
        left = float(s[t0_key])
        width = float(s[t1_key]) - left
        if width <= 0:
            continue
        st = s["state"]
        if palette == "semantic":
            if st == "waiting":
                ax.barh(
                    yi,
                    width,
                    left=left,
                    height=row_height,
                    align="center",
                    facecolor=STATE_COLORS["waiting"],
                    hatch=_WAIT_HATCH,
                    edgecolor="#7f1d1d",
                    linewidth=0.85,
                    zorder=2,
                )
            elif st == "running":
                ax.barh(
                    yi,
                    width,
                    left=left,
                    height=row_height,
                    align="center",
                    color=STATE_COLORS["running"],
                    edgecolor="#166534",
                    linewidth=0.4,
                    zorder=2,
                )
            else:
                ax.barh(
                    yi,
                    width,
                    left=left,
                    height=row_height,
                    align="center",
                    color=STATE_COLORS["holding"],
                    edgecolor="#1e3a8a",
                    linewidth=0.5,
                    zorder=2,
                )
        elif st == "waiting":
            ax.barh(
                yi,
                width,
                left=left,
                height=row_height,
                align="center",
                facecolor=_WAIT_FACE,
                hatch=_WAIT_HATCH,
                edgecolor=_WAIT_EDGE,
                linewidth=0.8,
                zorder=2,
            )
        else:
            color = _TASK_ROW_COLORS[yi % len(_TASK_ROW_COLORS)]
            edge = "#f8fafc"
            lw = 0.35
            if st == "holding":
                edge = "#e2e8f0"
                lw = 0.85
            ax.barh(
                yi,
                width,
                left=left,
                height=row_height,
                align="center",
                color=color,
                edgecolor=edge,
                linewidth=lw,
                zorder=2,
            )
        if s.get("lock") and st in ("waiting", "holding"):
            lbl = str(s["lock"])
            if palette == "semantic":
                tc = "#fefce8" if st == "waiting" else "#f8fafc"
            else:
                tc = "#f8fafc" if st == "waiting" else "#0f172a"
            ax.text(
                left + width / 2,
                yi,
                lbl,
                ha="center",
                va="center",
                fontsize=6,
                color=tc,
                zorder=3,
            )

    if cpu_row:
        busy: list[tuple[float, float]] = []
        for s in segs:
            if s["state"] not in ("running", "holding"):
                continue
            t0 = float(s[t0_key])
            t1 = float(s[t1_key])
            if t1 > t0:
                busy.append((t0, t1))
        for a, b in _merge_intervals(busy):
            ax.barh(
                y_cpu,
                b - a,
                left=a,
                height=row_height,
                align="center",
                color=_CPU_BUSY_COLOR,
                edgecolor="#bbf7d0",
                linewidth=0.4,
                zorder=2,
            )

    labels = list(threads_sorted) + (["CPU"] if cpu_row else [])
    n_rows = len(labels)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_ylim(n_rows - 0.5, -0.5)
    ax.invert_yaxis()


def _gantt_figure_from_segments(
    segs: list[dict[str, Any]],
    *,
    relative_time: bool,
    title: str | None,
    inset_graph: bool,
    cpu_row: bool = True,
    theme: str = "dark",
    palette: GanttPalette = "per_thread",
) -> tuple[Any, Any]:
    """Build matplotlib figure/axes for thread Gantt (one row per thread)."""
    from matplotlib.patches import Patch

    threads_sorted = sorted({s["thread"] for s in segs})
    use_rel = relative_time and "t0_rel" in segs[0]
    t0_key = "t0_rel" if use_rel else "t0"
    t1_key = "t1_rel" if use_rel else "t1"

    n_lane = len(threads_sorted) + (1 if cpu_row else 0)
    fig_h = max(3.2, 0.55 * n_lane + 1.2)
    fig, ax = plt.subplots(figsize=(12, fig_h))

    _plot_thread_gantt_axes(
        ax,
        segs,
        t0_key=t0_key,
        t1_key=t1_key,
        threads_sorted=threads_sorted,
        cpu_row=cpu_row,
        palette=palette,
    )

    ax.set_xlabel("Time (s) since trace start" if use_rel else "Time (s, perf_counter)")
    if title:
        ax.set_title(title)
    ax.grid(True, axis="x", linestyle=":", alpha=0.4)

    if palette == "semantic":
        legend_elems = [
            Patch(facecolor=STATE_COLORS["running"], edgecolor="#166534", label="running"),
            Patch(
                facecolor=STATE_COLORS["waiting"],
                hatch=_WAIT_HATCH,
                edgecolor="#7f1d1d",
                label="waiting (lock)",
            ),
            Patch(facecolor=STATE_COLORS["holding"], edgecolor="#1e3a8a", label="holding lock"),
        ]
    else:
        legend_elems = [
            Patch(facecolor=_TASK_ROW_COLORS[0], edgecolor="white", label="running / holding"),
            Patch(facecolor=_WAIT_FACE, hatch=_WAIT_HATCH, edgecolor=_WAIT_EDGE, label="waiting (lock)"),
        ]
    if cpu_row:
        legend_elems.append(Patch(facecolor=_CPU_BUSY_COLOR, edgecolor="#bbf7d0", label="CPU busy (aggregate)"))
    ax.legend(handles=legend_elems, loc="upper right", fontsize=7, framealpha=0.9)

    _apply_gantt_theme(fig, ax, theme=theme)

    if inset_graph:
        try:
            from mpl_toolkits.axes_grid1.inset_locator import inset_axes

            import networkx as nx

            G = build_graph()
            axins = inset_axes(ax, width="28%", height="28%", loc="lower right")
            pos = nx.spring_layout(G, seed=42)
            nx.draw(G, pos, ax=axins, with_labels=True, node_size=200, font_size=6)
            axins.set_title("wait graph", fontsize=8)
        except Exception:
            pass

    plt.tight_layout()
    return fig, ax


def visualize_gantt(
    *,
    events: list[dict[str, Any]] | None = None,
    relative_time: bool = True,
    show: bool = True,
    title: str | None = "threadle — thread timeline (Gantt)",
    inset_graph: bool = False,
    cpu_row: bool = True,
    theme: str = "dark",
    palette: GanttPalette = "per_thread",
) -> None:
    """Plot a Gantt-style chart (matplotlib).

    Each **thread** gets its own horizontal row. ``waiting`` (blocked on a
    :class:`~threadle.locks.tracked_lock.TrackedLock`) is drawn **hatched**;
    with ``palette="per_thread"``, ``running`` / ``holding`` use a **distinct
    solid color per thread**. With ``palette="semantic"``, colors follow
    **state** (green / red / blue). When ``cpu_row=True``, an extra row
    **CPU** shows merged intervals where any thread is ``running`` or
    ``holding`` (aggregate “busy”).

    These are **logical** states inferred from trace timestamps, not true
    multicore CPU usage; CPython's **GIL** still limits parallel bytecode.
    """
    ss = session_start_time() if relative_time else None
    segs = build_segments(raw_events=events, session_start=ss)
    if not segs:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(
            0.5,
            0.5,
            "No timeline segments (start tracing and record events).",
            ha="center",
            va="center",
            color="#e2e8f0" if theme == "dark" else "black",
        )
        ax.set_axis_off()
        _apply_gantt_theme(fig, ax, theme=theme)
        if show:
            show_figure(fig)
        plt.close(fig)
        return

    fig, ax = _gantt_figure_from_segments(
        segs,
        relative_time=relative_time,
        title=title,
        inset_graph=inset_graph,
        cpu_row=cpu_row,
        theme=theme,
        palette=palette,
    )
    if show:
        show_figure(fig)
    plt.close(fig)


def export_gantt(
    path: str,
    *,
    events: list[dict[str, Any]] | None = None,
    relative_time: bool = True,
    interactive: bool | None = None,
    inset_graph: bool = False,
    title: str | None = "threadle — thread timeline (Gantt)",
    cpu_row: bool = True,
    theme: str = "dark",
    palette: GanttPalette = "per_thread",
) -> None:
    """Save Gantt to PNG (matplotlib) or HTML (plotly if interactive / .html)."""
    if interactive is None:
        interactive = path.lower().endswith(".html")

    if interactive:
        _export_gantt_plotly(path, events=events, relative_time=relative_time, title=title)
        return

    ss = session_start_time() if relative_time else None
    segs = build_segments(raw_events=events, session_start=ss)
    if not segs:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.5, 0.5, "No timeline segments.", ha="center", va="center", color="#e2e8f0" if theme == "dark" else "black")
        ax.set_axis_off()
        _apply_gantt_theme(fig, ax, theme=theme)
        fig.savefig(path, bbox_inches="tight", dpi=150)
        plt.close(fig)
        return

    fig, ax = _gantt_figure_from_segments(
        segs,
        relative_time=relative_time,
        title=title,
        inset_graph=inset_graph,
        cpu_row=cpu_row,
        theme=theme,
        palette=palette,
    )
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def _export_gantt_plotly(
    path: str,
    *,
    events: list[dict[str, Any]] | None,
    relative_time: bool,
    title: str | None,
) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise ImportError("Exporting HTML Gantt requires the optional 'plotly' dependency.") from exc

    ss = session_start_time() if relative_time else None
    segs = build_segments(raw_events=events, session_start=ss)
    if not segs:
        fig = go.Figure()
        fig.add_annotation(text="No timeline segments.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.write_html(path)
        return

    use_rel = relative_time and "t0_rel" in segs[0]
    t0_key = "t0_rel" if use_rel else "t0"
    t1_key = "t1_rel" if use_rel else "t1"

    data = []
    for s in segs:
        data.append(
            dict(
                Task=s["thread"],
                Start=s[t0_key],
                Finish=s[t1_key],
                State=s["state"],
                Lock=str(s.get("lock") or ""),
                Color=STATE_COLORS[s["state"]],
            )
        )

    fig = go.Figure()
    for row in data:
        hover = f"{row['State']}"
        if row["Lock"]:
            hover += f" — {row['Lock']}"
        fig.add_trace(
            go.Bar(
                name=row["State"],
                x=[row["Finish"] - row["Start"]],
                y=[row["Task"]],
                base=[row["Start"]],
                orientation="h",
                marker_color=row["Color"],
                hovertemplate=hover + "<extra></extra>",
                showlegend=False,
            )
        )

    fig.update_layout(
        title=title or "",
        xaxis_title="Time (s)" + (" since trace start" if use_rel else ""),
        height=max(400, 120 * len({d["Task"] for d in data})),
    )
    fig.write_html(path)
