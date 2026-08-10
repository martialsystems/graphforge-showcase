"""Tool schema + max_steps autonomous fail-safes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from examples.agent_tool_gate import (  # noqa: E402
    build_runaway_graph,
    build_tool_graph,
)
from lawgraph import GraphError, LawViolation  # noqa: E402


def test_legal_tool_apply():
    g = build_tool_graph(force_partial=False)
    final = g.run()
    assert final["applied"] is True
    assert final["result"] == 42
    g.verify_audit()


def test_partial_tool_fails_closed():
    g = build_tool_graph(force_partial=True)
    with pytest.raises(LawViolation) as ei:
        g.run()
    assert ei.value.law == "tool_schema_valid"
    assert not any(
        e.get("event") == "node_ok" and e.get("node") == "apply" for e in g.audit_log
    )
    g.verify_audit()


def test_max_steps_budget():
    g = build_runaway_graph()
    with pytest.raises(GraphError, match="max_steps"):
        g.run(max_steps=5)
    assert any(e.get("event") == "budget_fail" for e in g.audit_log)
    g.verify_audit()
