"""Global tracker for threads and locks."""

from __future__ import annotations

import threading
from typing import Any

from threadle.core.state import LockInfo, ThreadInfo

_STATE_LOCK = threading.Lock()

GLOBAL_STATE: dict[str, dict[Any, Any]] = {
    "threads": {},
    "locks": {},
}


def reset_state() -> None:
    with _STATE_LOCK:
        GLOBAL_STATE["threads"].clear()
        GLOBAL_STATE["locks"].clear()


def register_thread(thread_id: int, name: str) -> None:
    with _STATE_LOCK:
        GLOBAL_STATE["threads"].setdefault(thread_id, ThreadInfo(ident=thread_id, name=name))


def register_lock(lock_name: str) -> None:
    with _STATE_LOCK:
        GLOBAL_STATE["locks"].setdefault(lock_name, LockInfo(name=lock_name))


def set_lock_owner(lock_name: str, thread_id: int | None) -> None:
    with _STATE_LOCK:
        lock = GLOBAL_STATE["locks"].setdefault(lock_name, LockInfo(name=lock_name))
        lock.owner = thread_id


def add_waiting_thread(lock_name: str, thread_id: int) -> None:
    with _STATE_LOCK:
        lock = GLOBAL_STATE["locks"].setdefault(lock_name, LockInfo(name=lock_name))
        lock.waiting.add(thread_id)
        thread = GLOBAL_STATE["threads"].setdefault(
            thread_id,
            ThreadInfo(ident=thread_id, name=f"Thread-{thread_id}"),
        )
        thread.waiting_for = lock_name


def remove_waiting_thread(lock_name: str, thread_id: int) -> None:
    with _STATE_LOCK:
        lock = GLOBAL_STATE["locks"].get(lock_name)
        if lock is not None:
            lock.waiting.discard(thread_id)
        thread = GLOBAL_STATE["threads"].get(thread_id)
        if thread is not None and thread.waiting_for == lock_name:
            thread.waiting_for = None


def snapshot_state() -> dict[str, dict[Any, Any]]:
    with _STATE_LOCK:
        return {
            "threads": {
                thread_id: ThreadInfo(
                    ident=info.ident,
                    name=info.name,
                    waiting_for=info.waiting_for,
                )
                for thread_id, info in GLOBAL_STATE["threads"].items()
            },
            "locks": {
                lock_name: LockInfo(
                    name=info.name,
                    owner=info.owner,
                    waiting=set(info.waiting),
                )
                for lock_name, info in GLOBAL_STATE["locks"].items()
            },
        }
