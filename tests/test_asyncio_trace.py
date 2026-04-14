"""Tests for asyncio timeline tracing."""

from __future__ import annotations

import asyncio

from threadle.asyncio_trace import events as AE
from threadle.asyncio_trace.decorators import trace_async, traced_await
from threadle.asyncio_trace.gantt import build_async_segments
from threadle.asyncio_trace.recorder import clear_async_events, get_async_events, start_async_tracing, stop_async_tracing
from threadle.asyncio_trace.task_id import format_task_id


def test_trace_async_emits_start_end() -> None:
    clear_async_events()
    start_async_tracing(clear=True)

    @trace_async
    async def f() -> int:
        return 7

    assert asyncio.run(f()) == 7
    stop_async_tracing()
    kinds = [e["event"] for e in get_async_events()]
    assert kinds[0] == AE.EVENT_START
    assert kinds[-1] == AE.EVENT_END


def test_traced_await_emits_await_resume() -> None:
    clear_async_events()
    start_async_tracing(clear=True)

    @trace_async
    async def inner() -> str:
        await asyncio.sleep(0)
        return "ok"

    @trace_async
    async def outer() -> str:
        return await traced_await(inner(), awaiting="inner")

    assert asyncio.run(outer()) == "ok"
    stop_async_tracing()
    kinds = [e["event"] for e in get_async_events()]
    assert AE.EVENT_AWAIT in kinds
    assert AE.EVENT_RESUME in kinds


def test_build_async_segments_running_and_awaiting() -> None:
    t0 = 1000.0
    raw = [
        {"timestamp": t0, "task_id": "T1", "event": AE.EVENT_START, "awaiting": None, "_seq": 1},
        {"timestamp": t0 + 0.1, "task_id": "T1", "event": AE.EVENT_AWAIT, "awaiting": "dep", "_seq": 2},
        {"timestamp": t0 + 0.2, "task_id": "T1", "event": AE.EVENT_RESUME, "awaiting": None, "_seq": 3},
        {"timestamp": t0 + 0.3, "task_id": "T1", "event": AE.EVENT_END, "awaiting": None, "_seq": 4},
    ]
    segs = build_async_segments(raw_events=raw, session_start=t0)
    states = [s["state"] for s in segs]
    assert "running" in states
    assert "awaiting" in states


def test_format_task_id_is_string() -> None:
    async def run() -> None:
        t = asyncio.current_task()
        assert isinstance(format_task_id(t), str)
        assert "#" in format_task_id(t)

    asyncio.run(run())
