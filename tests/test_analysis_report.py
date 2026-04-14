"""Structured deadlock reports and debug snapshots."""

from __future__ import annotations

import json
import subprocess
import sys

from threadle.analysis.deadlock import detect_deadlocks
from threadle.analysis.report import analyze_deadlocks
from threadle.analysis.snapshot import export_debug_bundle_dict, export_tracker_state_dict
from threadle.core.tracker import add_waiting_thread, register_lock, register_thread, reset_state, set_lock_owner
from threadle.session import Session


def test_analyze_deadlocks_matches_detect_deadlocks_raw_cycle() -> None:
    reset_state()
    register_lock("L1")
    register_lock("L2")
    register_thread(1, "t1")
    register_thread(2, "t2")
    set_lock_owner("L1", 1)
    set_lock_owner("L2", 2)
    add_waiting_thread("L1", 2)
    add_waiting_thread("L2", 1)

    rep = analyze_deadlocks()
    raw = detect_deadlocks()
    assert rep.found is True
    assert raw == rep.raw_cycle
    assert "waits for" in rep.summary.lower()
    assert rep.edges
    data = rep.to_dict()
    assert data["found"] is True
    json.loads(rep.to_json())


def test_export_tracker_state_dict_shape() -> None:
    reset_state()
    register_lock("L1")
    register_thread(9, "worker")
    d = export_tracker_state_dict()
    assert "locks" in d and "threads" in d
    assert "L1" in d["locks"]
    assert d["threads"]["9"]["name"] == "worker"


def test_export_debug_bundle_includes_deadlock_block() -> None:
    reset_state()
    register_lock("L1")
    register_lock("L2")
    register_thread(1, "t1")
    register_thread(2, "t2")
    set_lock_owner("L1", 1)
    set_lock_owner("L2", 2)
    add_waiting_thread("L1", 2)
    add_waiting_thread("L2", 1)
    bundle = export_debug_bundle_dict()
    assert bundle["deadlock"]["found"] is True
    assert bundle["tracker"]["locks"]


def test_session_starts_and_stops_tracing() -> None:
    reset_state()
    with Session(trace_timeline=True, reset_tracker=True):
        pass  # smoke: no exception


def test_cli_detect_json() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "threadle.cli.main", "detect", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    assert "found" in out


def test_cli_snapshot() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "threadle.cli.main", "snapshot"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "tracker" in data and "deadlock" in data
