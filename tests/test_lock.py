import threading

from threadle.core.tracker import GLOBAL_STATE, reset_state
from threadle.locks.tracked_lock import TrackedLock


def test_acquire_and_release_updates_owner() -> None:
    reset_state()
    lock = TrackedLock("db")
    lock.acquire()
    thread_id = threading.get_ident()

    assert GLOBAL_STATE["locks"]["db"].owner == thread_id
    lock.release()
    assert GLOBAL_STATE["locks"]["db"].owner is None
