#!/usr/bin/env python3
"""Autonomous fail-safe: never overwrite a fresher dest with a staler src.

Scenario (generic site/artifact publish — not finance-specific)
---------------------------------------------------------------
  build -> compare -> publish -> END

Product laws:

  1. After compare: src track time must be >= dest track time (no stale-over-fresh).
  2. After compare: architecture freeze bit must stay true if already frozen.
  3. After publish: published only when compare said copy_allowed; dest advances.

Illegal paths fail closed with no publish. Fully autonomous (no human node).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawgraph import Channel, Graph, GraphError, LawViolation, StateSchema
from lawgraph.state import append_list, last_value


def build_site_publish_graph(
    *,
    force_stale_src: bool = False,
    force_unfreeze: bool = False,
) -> Graph:
    schema = StateSchema(
        [
            Channel("src_track", last_value, 0),  # higher = fresher
            Channel("dest_track", last_value, 0),
            Channel("copy_allowed", last_value, False),
            Channel("freeze_locked", last_value, True),
            Channel("published", last_value, False),
            Channel("events", append_list, None),
        ]
    )
    g = Graph(schema, entry="build", terminal="END")

    def build(state):
        # Simulate built artifact track id (e.g. epoch or content generation).
        raw = state.get("src_track")
        src = 100 if raw is None else int(raw)
        if force_stale_src:
            src = 10  # older than a typical dest of 50
        return {"src_track": src, "events": ["built"]}

    def compare(state):
        src = int(state.get("src_track") or 0)
        dest = int(state.get("dest_track") or 0)
        allowed = src >= dest
        freeze = bool(state.get("freeze_locked", True))
        if force_unfreeze:
            freeze = False  # illegal: touch freeze outside an unfreeze path
        return {
            "copy_allowed": allowed,
            "freeze_locked": freeze,
            "events": ["compared_ok" if allowed else "compared_stale"],
        }

    def publish(state):
        src = int(state.get("src_track") or 0)
        return {
            "published": True,
            "dest_track": src,
            "events": ["published"],
        }

    def law_not_stale(state, node):
        src = int(state.get("src_track") or 0)
        dest = int(state.get("dest_track") or 0)
        if src < dest:
            raise LawViolation(
                "stale_over_fresh_block",
                node,
                f"src_track={src} < dest_track={dest}; refuse regress",
            )
        if not state.get("copy_allowed"):
            raise LawViolation(
                "stale_over_fresh_block",
                node,
                "copy_allowed is false",
            )

    def law_freeze_intact(state, node):
        # Demo: freeze starts true; no graph edge may clear it on this path.
        if state.get("freeze_locked") is not True:
            raise LawViolation(
                "freeze_untouched",
                node,
                "freeze_locked cleared without unfreeze path",
            )

    def law_publish_safe(state, node):
        if not state.get("copy_allowed"):
            raise LawViolation(
                "stale_over_fresh_block",
                node,
                "publish blocked: copy not allowed",
            )
        if state.get("freeze_locked") is not True:
            raise LawViolation(
                "freeze_untouched",
                node,
                "publish blocked: freeze was disturbed",
            )
        if int(state.get("dest_track") or 0) < int(state.get("src_track") or 0):
            # after publish node, dest should equal src; law runs after write
            pass
        if not state.get("published"):
            raise LawViolation(
                "publish_mark_required",
                node,
                "publish node did not set published",
            )

    g.add_node("build", build)
    g.add_node(
        "compare",
        compare,
        laws=[
            ("stale_over_fresh_block", law_not_stale),
            ("freeze_untouched", law_freeze_intact),
        ],
    )
    g.add_node("publish", publish, laws=[("publish_safe", law_publish_safe)])
    g.add_edge("build", "compare")
    g.add_edge("compare", "publish")
    g.add_edge("publish", "END")
    return g


def main() -> int:
    print("=== legal path: fresher src, freeze intact ===")
    g = build_site_publish_graph()
    final = g.run({"src_track": 100, "dest_track": 50, "freeze_locked": True})
    print("published:", final["published"], "dest_track:", final["dest_track"])
    print("events:", final["events"])
    g.verify_audit()
    print("audit verified: ok")

    print()
    print("=== illegal path: stale src over fresh dest ===")
    bad = build_site_publish_graph(force_stale_src=True)
    try:
        bad.run({"src_track": 10, "dest_track": 50, "freeze_locked": True})
        print("ERROR: expected LawViolation")
        return 1
    except LawViolation as e:
        print("caught:", e)
        print("audit tail:", bad.audit_log[-4:])
        bad.verify_audit()
        print("audit verified after fail: ok")

    print()
    print("=== illegal path: freeze cleared on autonomous path ===")
    fr = build_site_publish_graph(force_unfreeze=True)
    try:
        fr.run({"src_track": 100, "dest_track": 50, "freeze_locked": True})
        print("ERROR: expected LawViolation")
        return 1
    except LawViolation as e:
        print("caught:", e)

    print()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
