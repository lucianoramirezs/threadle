"""Lock wrapper that reports ownership and waiters."""

from __future__ import annotations

import threading

from threadle.core.tracker import (
    add_waiting_thread,
    register_lock,
    register_thread,
    remove_waiting_thread,
    set_lock_owner,
)
from threadle.timeline import events as E
from threadle.timeline.recorder import is_tracing, record_event


class TrackedLock:
    """A thin wrapper around ``threading.Lock`` that updates global tracker state."""

    def __init__(self, name: str):
        self._lock = threading.Lock()
        self.name = name
        register_lock(name)

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        current = threading.current_thread()
        thread_id = threading.get_ident()
        register_thread(thread_id, current.name)

        if is_tracing():
            record_event(E.EVENT_ACQUIRE_ATTEMPT, self.name)

        blocking_wait = blocking and self._lock.locked()
        if self._lock.locked():
            add_waiting_thread(self.name, thread_id)

        if blocking_wait and is_tracing():
            record_event(E.EVENT_BLOCKED, self.name)

        acquired = self._lock.acquire(blocking=blocking, timeout=timeout)
        if acquired:
            remove_waiting_thread(self.name, thread_id)
            set_lock_owner(self.name, thread_id)
            if is_tracing():
                record_event(E.EVENT_ACQUIRE_SUCCESS, self.name)
        else:
            remove_waiting_thread(self.name, thread_id)
            if is_tracing() and blocking_wait:
                record_event(E.EVENT_ACQUIRE_FAILED, self.name)
        return acquired

    def release(self) -> None:
        if is_tracing():
            record_event(E.EVENT_RELEASE, self.name)
        self._lock.release()
        set_lock_owner(self.name, None)

    def locked(self) -> bool:
        return self._lock.locked()
