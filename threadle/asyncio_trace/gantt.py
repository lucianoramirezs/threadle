"""Async task timeline segments and Gantt charts."""

from __future__ import annotations

from typing import Any, Literal

from threadle._mpl import setup_matplotlib_backend, show_figure

setup_matplotlib_backend()
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from threadle.asyncio_trace import events as AE
from threadle.asyncio_trace.recorder import async_session_start_time, snapshot_raw_async_events

AsyncStateKind = Literal["running", "awaiting", "done"]

ASYNC_STATE_COLORS: dict[AsyncStateKind, str] = {
    "running": "#2ca02c",
    "awaiting": "#ff7f0e",
    "done": "#7f7f7f",
}


def _add_async_state_legend(ax: Any) -> None:
    """Legend for semantic async Gantt colors (running / awaiting / done)."""
    handles = [
        Patch(
            facecolor=ASYNC_STATE_COLORS["running"],
            edgecolor="white",
            linewidth=0.5,
            label="running",
        ),
        Patch(
            facecolor=ASYNC_STATE_COLORS["awaiting"],
            edgecolor="white",
            linewidth=0.5,
            label="awaiting",
        ),
        Patch(
            facecolor=ASYNC_STATE_COLORS["done"],
            edgecolor="white",
            linewidth=0.5,
            label="done",
        ),
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=8, framealpha=0.9)


def build_async_segments(
    raw_events: list[dict[str, Any]] | None = None,
    *,
    session_start: float | None = None,
) -> list[dict[str, Any]]:
    """Build contiguous segments per task: ``running`` or ``awaiting`` (plus flush to trace end)."""
    if raw_events is None:
        raw_events = snapshot_raw_async_events()
    if not raw_events:
        return []

    if session_start is None:
        session_start = async_session_start_time()

    events_sorted = sorted(raw_events, key=lambda e: (e["timestamp"], e.get("_seq", 0)))
    t_max = max(e["timestamp"] for e in events_sorted)

    last_t: dict[str, float] = {}
    mode: dict[str, AsyncStateKind] = {}
    await_label: dict[str, str | None] = {}
    ended: set[str] = set()
    segments: list[dict[str, Any]] = []

    def append_segment(tid: str, t0: float, t1: float, st: AsyncStateKind, label: str | None = None) -> None:
        if t1 <= t0:
            return
        seg: dict[str, Any] = {
            "task_id": tid,
            "t0": t0,
            "t1": t1,
            "state": st,
            "awaiting": label,
        }
        if session_start is not None:
            seg["t0_rel"] = t0 - session_start
            seg["t1_rel"] = t1 - session_start
        segments.append(seg)

    for ev in events_sorted:
        tid = ev["task_id"]
        t = float(ev["timestamp"])
        kind = ev["event"]
        aw = ev.get("awaiting")

        if tid in ended:
            continue

        if tid in last_t:
            st = mode[tid]
            lab = await_label.get(tid) if st == "awaiting" else None
            append_segment(tid, last_t[tid], t, st, lab)

        if kind == AE.EVENT_START:
            mode[tid] = "running"
            await_label.pop(tid, None)
        elif kind == AE.EVENT_END:
            ended.add(tid)
            last_t.pop(tid, None)
            mode.pop(tid, None)
            await_label.pop(tid, None)
            continue
        elif kind == AE.EVENT_AWAIT:
            await_label[tid] = aw
            mode[tid] = "awaiting"
        elif kind == AE.EVENT_RESUME:
            await_label.pop(tid, None)
            mode[tid] = "running"

        last_t[tid] = t

    for tid, t0 in list(last_t.items()):
        if tid in ended:
            continue
        st = mode.get(tid, "running")
        lab = await_label.get(tid) if st == "awaiting" else None
        append_segment(tid, t0, t_max, st, lab)

    segments.sort(key=lambda s: (s["t0"], s["task_id"]))
    return segments


def visualize_async_gantt(
    *,
    events: list[dict[str, Any]] | None = None,
    relative_time: bool = True,
    show: bool = True,
    title: str | None = "threadle — asyncio tasks (Gantt)",
) -> None:
    """Plot asyncio task timeline (matplotlib). Separate color map from thread Gantt."""
    ss = async_session_start_time() if relative_time else None
    segs = build_async_segments(raw_events=events, session_start=ss)
    if not segs:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.5, 0.5, "No async timeline segments (start_async_tracing and run tasks).", ha="center", va="center")
        ax.set_axis_off()
        if show:
            show_figure(fig)
        plt.close(fig)
        return

    tasks_sorted = sorted({s["task_id"] for s in segs})
    y_index = {name: i for i, name in enumerate(tasks_sorted)}

    use_rel = relative_time and "t0_rel" in segs[0]
    t0_key = "t0_rel" if use_rel else "t0"
    t1_key = "t1_rel" if use_rel else "t1"

    fig, ax = plt.subplots(figsize=(12, max(3, 0.45 * len(tasks_sorted) + 1)))
    height = 0.35

    for s in segs:
        y = y_index[s["task_id"]]
        left = s[t0_key]
        width = s[t1_key] - s[t0_key]
        color = ASYNC_STATE_COLORS.get(s["state"], "#888888")
        ax.barh(y, width, left=left, height=height, color=color, align="center", edgecolor="white", linewidth=0.3)
        if s.get("awaiting") and s["state"] == "awaiting":
            ax.text(
                left + width / 2,
                y,
                str(s["awaiting"])[:40],
                ha="center",
                va="center",
                fontsize=6,
                color="black",
            )

    ax.set_yticks(range(len(tasks_sorted)))
    ax.set_yticklabels(tasks_sorted)
    ax.set_xlabel("Time since async trace start (s)" if use_rel else "Time (perf_counter)")
    if title:
        ax.set_title(title)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    _add_async_state_legend(ax)
    plt.tight_layout()
    if show:
        show_figure(fig)
    plt.close(fig)


def export_async_gantt(
    path: str,
    *,
    events: list[dict[str, Any]] | None = None,
    relative_time: bool = True,
    title: str | None = "threadle — asyncio tasks (Gantt)",
) -> None:
    """Save async Gantt to PNG."""
    ss = async_session_start_time() if relative_time else None
    segs = build_async_segments(raw_events=events, session_start=ss)
    if not segs:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.5, 0.5, "No async timeline segments.", ha="center", va="center")
        ax.set_axis_off()
        fig.savefig(path, bbox_inches="tight", dpi=150)
        plt.close(fig)
        return

    tasks_sorted = sorted({s["task_id"] for s in segs})
    y_index = {name: i for i, name in enumerate(tasks_sorted)}
    use_rel = relative_time and "t0_rel" in segs[0]
    t0_key = "t0_rel" if use_rel else "t0"
    t1_key = "t1_rel" if use_rel else "t1"

    fig, ax = plt.subplots(figsize=(12, max(3, 0.45 * len(tasks_sorted) + 1)))
    height = 0.35
    for s in segs:
        y = y_index[s["task_id"]]
        left = s[t0_key]
        width = s[t1_key] - s[t0_key]
        color = ASYNC_STATE_COLORS.get(s["state"], "#888888")
        ax.barh(y, width, left=left, height=height, color=color, align="center", edgecolor="white", linewidth=0.3)

    ax.set_yticks(range(len(tasks_sorted)))
    ax.set_yticklabels(tasks_sorted)
    ax.set_xlabel("Time since async trace start (s)" if use_rel else "Time (perf_counter)")
    if title:
        ax.set_title(title)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    _add_async_state_legend(ax)
    plt.tight_layout()
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
