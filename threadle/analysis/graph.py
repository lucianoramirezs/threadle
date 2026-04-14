"""Build a wait-for graph from tracker state."""

from __future__ import annotations

import networkx as nx

from threadle.core.tracker import snapshot_state
from threadle.core.utils import lock_node_id, thread_node_id


def build_graph() -> nx.DiGraph:
    state = snapshot_state()
    graph = nx.DiGraph()

    for lock_name, lock_info in state["locks"].items():
        lock_node = lock_node_id(lock_name)
        graph.add_node(lock_node, kind="lock", name=lock_name)

        if lock_info.owner is not None:
            owner_node = thread_node_id(lock_info.owner)
            graph.add_node(owner_node, kind="thread", ident=lock_info.owner)
            graph.add_edge(lock_node, owner_node, relation="held_by")

        for waiting_thread in lock_info.waiting:
            waiting_node = thread_node_id(waiting_thread)
            graph.add_node(waiting_node, kind="thread", ident=waiting_thread)
            graph.add_edge(waiting_node, lock_node, relation="waits_for")

    return graph
