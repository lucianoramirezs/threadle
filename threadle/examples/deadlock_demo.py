"""Deadlock demo logic reusable by CLI and scripts."""

from __future__ import annotations

import threading
from threading import Event

from threadle.analysis.deadlock import detect_deadlocks
from threadle.core.tracker import reset_state
from threadle.locks.tracked_lock import TrackedLock
from threadle.visualization.visualize import visualize


def run_demo(visualize_graph: bool = False, output_path: str = "threadle-demo.png"):
    reset_state()
    lock_one = TrackedLock("L1")
    lock_two = TrackedLock("L2")
    first_has_lock = Event()
    second_has_lock = Event()
    release_all = Event()

    def safe_release(lock: TrackedLock) -> None:
        try:
            lock.release()
        except RuntimeError:
            # Demo threads can interleave differently; ignore duplicate releases.
            pass

    def worker_one() -> None:
        lock_one.acquire()
        acquired_lock_two = False
        first_has_lock.set()
        second_has_lock.wait()
        acquired_lock_two = lock_two.acquire(timeout=0.2)
        release_all.wait(timeout=0.2)
        if acquired_lock_two:
            safe_release(lock_two)
        safe_release(lock_one)

    def worker_two() -> None:
        lock_two.acquire()
        acquired_lock_one = False
        second_has_lock.set()
        first_has_lock.wait()
        acquired_lock_one = lock_one.acquire(timeout=0.2)
        release_all.wait(timeout=0.2)
        if acquired_lock_one:
            safe_release(lock_one)
        safe_release(lock_two)

    thread_one = threading.Thread(target=worker_one, name="demo-1")
    thread_two = threading.Thread(target=worker_two, name="demo-2")
    thread_one.start()
    thread_two.start()

    first_has_lock.wait(timeout=1.0)
    second_has_lock.wait(timeout=1.0)
    cycle = detect_deadlocks()
    if visualize_graph:
        visualize(output_path=output_path)

    release_all.set()
    thread_one.join(timeout=1.0)
    thread_two.join(timeout=1.0)
    return cycle
