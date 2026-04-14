import threading
from threadle.core.tracker import reset_state
from threadle.locks.tracked_lock import TrackedLock
from threadle.timeline import events as E
from threadle.timeline.gantt import build_segments
from threadle.timeline.recorder import clear_events, get_events, record_event, start_tracing, stop_tracing


def test_record_event_is_ordered_and_thread_safe() -> None:
    clear_events()
    start_tracing(clear=True)
    barrier = threading.Barrier(4)

    def worker(n: int) -> None:
        barrier.wait()
        for _ in range(10):
            record_event(E.EVENT_ACQUIRE_ATTEMPT, f"L{n}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    evs = get_events()
    assert len(evs) == 40
    ts = [e["timestamp"] for e in evs]
    assert ts == sorted(ts)
    stop_tracing()


def test_build_segments_running_wait_hold() -> None:
    # Synthetic event stream (same thread): start -> attempt -> blocked -> success -> release
    t0 = 100.0
    raw = [
        {"timestamp": t0, "thread": "T1", "event": E.EVENT_START, "lock": None, "_seq": 1},
        {"timestamp": t0 + 1, "thread": "T1", "event": E.EVENT_ACQUIRE_ATTEMPT, "lock": "L1", "_seq": 2},
        {"timestamp": t0 + 2, "thread": "T1", "event": E.EVENT_BLOCKED, "lock": "L1", "_seq": 3},
        {"timestamp": t0 + 5, "thread": "T1", "event": E.EVENT_ACQUIRE_SUCCESS, "lock": "L1", "_seq": 4},
        {"timestamp": t0 + 8, "thread": "T1", "event": E.EVENT_RELEASE, "lock": "L1", "_seq": 5},
        {"timestamp": t0 + 9, "thread": "T1", "event": E.EVENT_END, "lock": None, "_seq": 6},
    ]
    segs = build_segments(raw_events=raw, session_start=t0)
    states = [s["state"] for s in segs]
    assert "running" in states
    assert "waiting" in states
    assert "holding" in states


def test_tracked_lock_emits_timeline_when_tracing() -> None:
    reset_state()
    clear_events()
    start_tracing(clear=True)
    lock = TrackedLock("L-test")
    lock.acquire()
    assert any(e["event"] == E.EVENT_ACQUIRE_SUCCESS for e in get_events())
    lock.release()
    assert any(e["event"] == E.EVENT_RELEASE for e in get_events())
    stop_tracing()
