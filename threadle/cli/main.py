"""threadle command line interface."""

from __future__ import annotations

import argparse

from threadle.analysis.deadlock import detect_deadlocks
from threadle.analysis.report import analyze_deadlocks
from threadle.analysis.snapshot import export_debug_bundle_json
from threadle.examples.deadlock_demo import run_demo


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="threadle",
        description=(
            "threadle inspects *instrumented* lock/thread state in the current process. "
            "Use TrackedLock and tracing APIs in your code; this CLI reads snapshots."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser("detect", help="Print deadlock analysis for current tracker state")
    detect_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON (from analyze_deadlocks) instead of raw tuples",
    )

    subparsers.add_parser(
        "snapshot",
        help="Dump tracker state + deadlock analysis as JSON (for CI / bug reports)",
    )

    demo_parser = subparsers.add_parser("demo", help="Run deadlock demo")
    demo_parser.add_argument("--visualize", action="store_true", help="Render graph to PNG")
    demo_parser.add_argument(
        "--output",
        default="threadle-demo.png",
        help="Output path for graph when --visualize is enabled",
    )

    args = parser.parse_args()

    if args.command == "detect":
        if args.json:
            print(analyze_deadlocks().to_json())
        else:
            print(detect_deadlocks())
        return

    if args.command == "snapshot":
        print(export_debug_bundle_json())
        return

    if args.command == "demo":
        cycle = run_demo(visualize_graph=args.visualize, output_path=args.output)
        print(cycle)


if __name__ == "__main__":
    main()
