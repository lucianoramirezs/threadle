from threadle.analysis.deadlock import detect_deadlocks
from threadle.core.tracker import add_waiting_thread, register_lock, register_thread, reset_state, set_lock_owner


def test_deadlock_detection_finds_cycle() -> None:
    reset_state()
    register_lock("L1")
    register_lock("L2")
    register_thread(1, "t1")
    register_thread(2, "t2")

    set_lock_owner("L1", 1)
    set_lock_owner("L2", 2)
    add_waiting_thread("L1", 2)
    add_waiting_thread("L2", 1)

    cycle = detect_deadlocks()
    assert cycle is not None
    assert len(cycle) >= 2
