from threadle.analysis.graph import build_graph
from threadle.core.tracker import add_waiting_thread, register_lock, register_thread, reset_state, set_lock_owner
from threadle.core.utils import lock_node_id, thread_node_id


def test_build_graph_creates_wait_and_hold_edges() -> None:
    reset_state()
    register_lock("L1")
    register_thread(10, "worker-a")
    register_thread(11, "worker-b")
    set_lock_owner("L1", 10)
    add_waiting_thread("L1", 11)

    graph = build_graph()

    assert graph.has_edge(lock_node_id("L1"), thread_node_id(10))
    assert graph.has_edge(thread_node_id(11), lock_node_id("L1"))
