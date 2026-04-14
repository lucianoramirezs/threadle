"""State containers used by the tracker."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ThreadInfo:
    """Information tracked per thread."""

    ident: int
    name: str
    waiting_for: str | None = None


@dataclass
class LockInfo:
    """Information tracked per lock."""

    name: str
    owner: int | None = None
    waiting: set[int] = field(default_factory=set)
