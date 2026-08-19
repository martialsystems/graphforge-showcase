#!/usr/bin/env python3
"""Autonomous fail-safes: schema-valid tool results + step budget.

Scenario
--------
  plan -> tool_call -> apply -> END

Product laws / budgets:

  1. After tool_call: tool payload must match a fixed schema (no partial junk).
  2. After apply: apply only if tool_ok; result channel written only then.
  3. Runaway loop hits max_steps (autonomous budget fail-safe).

No human interrupt. Illegal paths stop the run and leave no applied side effect.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawgraph import Channel, Graph, GraphError, LawViolation, StateSchema
from lawgraph.state import append_list, last_value

REQUIRED_TOOL_KEYS = frozenset({"status", "value"})


def _schema_ok(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if set(payload.keys()) != REQUIRED_TOOL_KEYS:
        return False
    if payload.get("status") not in ("ok", "error"):
        return False
    return "value" in payload


def build_tool_graph(*, force_partial: bool = False) -> Graph:
    schema = StateSchema(
        [
            Channel("goal", last_value, ""),
            Channel("tool_raw", last_value, None),
            Channel("tool_ok", last_value, False),
            Channel("applied", last_value, False),
            Channel("result", last_value, None),
            Channel("events", append_list, None),
        ]
    )
    g = Graph(schema, entry="plan", terminal="END")

    def plan(state):
        return {
            "goal": state.get("goal") or "fetch structured fact",
            "events": ["planned"],
        }

    def tool_call(state):
        if force_partial:
            # Partial / junk payload — common agent failure mode.
            raw = {"status": "ok"}  # missing value
        else:
            raw = {"status": "ok", "value": 42}
        return {
            "tool_raw": raw,
            "tool_ok": _schema_ok(raw),
            "events": ["tool_returned"],
        }

    def apply(state):
        raw = state.get("tool_raw") or {}
        return {
            "applied": True,
            "result": raw.get("value"),
            "events": ["applied"],
        }

    def law_tool_schema(state, node):
        raw = state.get("tool_raw")
        if not _schema_ok(raw):
            raise LawViolation(
                "tool_schema_valid",
                node,
                f"tool payload failed schema: {raw!r}",
            )
        if not state.get("tool_ok"):
            raise LawViolation(
                "tool_schema_valid",
                node,
                "tool_ok is false",
            )

    def law_apply_safe(state, node):
        if not state.get("tool_ok"):
            raise LawViolation(
                "apply_safe",
                node,
                "apply blocked: tool not ok",
            )
        if not state.get("applied"):
            raise LawViolation(
                "apply_mark_required",
                node,
                "apply node did not set applied",
            )

    g.add_node("plan", plan)
    g.add_node("tool_call", tool_call, laws=[("tool_schema_valid", law_tool_schema)])
    g.add_node("apply", apply, laws=[("apply_safe", law_apply_safe)])
    g.add_edge("plan", "tool_call")
    g.add_edge("tool_call", "apply")
    g.add_edge("apply", "END")
    return g


def build_runaway_graph() -> Graph:
    """Agent loop with no terminal exit except max_steps budget."""
    schema = StateSchema(
        [
            Channel("n", last_value, 0),
            Channel("events", append_list, None),
        ]
    )
    g = Graph(schema, entry="tick", terminal="END")

    def tick(state):
        n = int(state.get("n") or 0) + 1
        return {"n": n, "events": [f"tick_{n}"]}

    def always_loop(_state):
        return "again"

    g.add_node("tick", tick)
    g.add_conditional_edges("tick", always_loop, {"again": "tick"})
    return g


def main() -> int:
    print("=== legal path: schema-valid tool result, apply ===")
    g = build_tool_graph(force_partial=False)
    final = g.run()
    print("applied:", final["applied"], "result:", final["result"])
    g.verify_audit()
    print("audit verified: ok")

    print()
    print("=== illegal path: partial tool JSON ===")
    bad = build_tool_graph(force_partial=True)
    try:
        bad.run()
        print("ERROR: expected LawViolation")
        return 1
    except LawViolation as e:
        print("caught:", e)
        assert not any(
            e.get("event") == "node_ok" and e.get("node") == "apply"
            for e in bad.audit_log
        )
        bad.verify_audit()
        print("no apply node_ok; audit verified")

    print()
    print("=== illegal path: runaway loop hits max_steps ===")
    loop = build_runaway_graph()
    try:
        loop.run(max_steps=5)
        print("ERROR: expected GraphError budget")
        return 1
    except GraphError as e:
        print("caught:", e)
        assert any(ev.get("event") == "budget_fail" for ev in loop.audit_log)
        loop.verify_audit()
        print("budget_fail audited; chain ok")

    print()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
