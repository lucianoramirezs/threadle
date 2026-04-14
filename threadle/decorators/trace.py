"""Simple tracing decorator."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any


def trace(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"[TRACE] Enter {func.__name__}")
        result = func(*args, **kwargs)
        print(f"[TRACE] Exit {func.__name__}")
        return result

    return wrapper
