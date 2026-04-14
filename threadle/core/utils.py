"""Utility helpers for stable graph node identifiers."""


def thread_node_id(thread_ident: int) -> str:
    return f"thread:{thread_ident}"


def lock_node_id(lock_name: str) -> str:
    return f"lock:{lock_name}"
