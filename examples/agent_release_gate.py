#!/usr/bin/env python3
"""Toy product law: agent cannot ship code that skipped the release gate.

Scenario
--------
An agent (or CI job) walks a release graph:

  plan -> implement -> test -> review_gate -> publish -> END

Product laws (enforced after specific nodes):

  1. After test: tests must have passed.
  2. After review_gate: a human (or designated reviewer) must approve.
  3. After publish: artifact digest must be recorded; publish is forbidden
     if review was skipped or tests failed.

Illegal paths fail closed with LawViolation. That is the point.

This example is domain-neutral on purpose. Swap "publish" for "deploy",
"promote model", or "post to site" — the pattern is the same.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawgraph import Channel, Graph, LawViolation, StateSchema
from lawgraph.state import append_list, last_value


def build_release_graph(*, force_skip_review: bool = False) -> Graph:
    schema = StateSchema(
        [
            Channel("goal", last_value, ""),
            Channel("diff_summary", last_value, ""),
            Channel("tests_passed", last_value, False),
            Channel("review_status", last_value, "pending"),  # pending|approved|rejected
            Channel("published", last_value, False),
            Channel("artifact_digest", last_value, None),
            Channel("events", append_list, None),
        ]
    )

    g = Graph(schema, entry="plan", terminal="END")

    def plan(state):
        return {
            "goal": state.get("goal") or "ship release notes helper",
            "events": ["planned"],
        }

    def implement(state):
        # Pretend the agent wrote a change.
        return {
            "diff_summary": "add scripts/release_notes.py",
            "events": ["implemented"],
        }

    def test(state):
        # In a real system this would shell out. Here the outcome is data.
        passed = bool(state.get("tests_passed", True))
        return {
            "tests_passed": passed,
            "events": ["tested_ok" if passed else "tested_fail"],
        }

    def review_gate(state):
        if force_skip_review:
            # Illegal agent behavior: jump past human review.
            return {
                "review_status": "pending",
                "events": ["review_skipped_by_agent"],
            }
        # Happy path: reviewer approves.
        return {
            "review_status": "approved",
            "events": ["review_approved"],
        }

    def publish(state):
        return {
            "published": True,
            "artifact_digest": "sha256:demo-artifact",
            "events": ["published"],
        }

    def law_tests_passed(state, node):
        if not state.get("tests_passed"):
            raise LawViolation(
                "tests_must_pass",
                node,
                "refusing to continue with failing tests",
            )

    def law_review_approved(state, node):
        if state.get("review_status") != "approved":
            raise LawViolation(
                "review_required",
                node,
                f"review_status={state.get('review_status')!r}; need approved",
            )

    def law_publish_safe(state, node):
        if not state.get("tests_passed"):
            raise LawViolation("tests_must_pass", node, "publish blocked: tests failed")
        if state.get("review_status") != "approved":
            raise LawViolation(
                "review_required",
                node,
                "publish blocked: review not approved",
            )
        if not state.get("artifact_digest"):
            raise LawViolation(
                "artifact_required",
                node,
                "publish blocked: missing artifact_digest",
            )

    g.add_node("plan", plan)
    g.add_node("implement", implement)
    g.add_node("test", test, laws=[("tests_must_pass", law_tests_passed)])
    g.add_node(
        "review_gate",
        review_gate,
        laws=[("review_required", law_review_approved)],
    )
    g.add_node("publish", publish, laws=[("publish_safe", law_publish_safe)])

    g.add_edge("plan", "implement")
    g.add_edge("implement", "test")
    g.add_edge("test", "review_gate")
    g.add_edge("review_gate", "publish")
    g.add_edge("publish", "END")
    return g


def main() -> int:
    print("=== legal path: tests pass, review approves ===")
    g = build_release_graph(force_skip_review=False)
    final = g.run({"tests_passed": True})
    print("published:", final["published"], "digest:", final["artifact_digest"])
    print("events:", final["events"])
    print("audit tail:", g.audit_log[-4:])

    print()
    print("=== illegal path: agent skips review ===")
    bad = build_release_graph(force_skip_review=True)
    try:
        bad.run({"tests_passed": True})
        print("ERROR: expected LawViolation")
        return 1
    except LawViolation as e:
        print("caught:", e)
        print("audit:", bad.audit_log[-6:])

    print()
    print("=== illegal path: tests failed ===")
    fail = build_release_graph(force_skip_review=False)
    try:
        fail.run({"tests_passed": False})
        print("ERROR: expected LawViolation")
        return 1
    except LawViolation as e:
        print("caught:", e)

    print()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
