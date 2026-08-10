"""Tests for the agent release-gate example.

Illegal transitions must raise. Legal path must publish once.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from examples.agent_release_gate import build_release_graph  # noqa: E402
from lawgraph import LawViolation  # noqa: E402


def test_legal_path_publishes():
    g = build_release_graph(force_skip_review=False)
    final = g.run({"tests_passed": True})
    assert final["published"] is True
    assert final["review_status"] == "approved"
    assert final["artifact_digest"]
    assert "published" in final["events"]
    assert any(e.get("event") == "law_ok" for e in g.audit_log)
    g.verify_audit()


def test_skip_review_fails_closed():
    g = build_release_graph(force_skip_review=True)
    with pytest.raises(LawViolation) as ei:
        g.run({"tests_passed": True})
    assert ei.value.law == "review_required"
    assert ei.value.node == "review_gate"
    assert final_not_published(g)


def test_failed_tests_fail_closed():
    g = build_release_graph(force_skip_review=False)
    with pytest.raises(LawViolation) as ei:
        g.run({"tests_passed": False})
    assert ei.value.law == "tests_must_pass"
    assert ei.value.node == "test"


def test_unknown_channel_write_fails():
    from lawgraph import Channel, Graph, StateSchema
    from lawgraph.state import last_value

    schema = StateSchema([Channel("x", last_value, 0)])
    g = Graph(schema, entry="n", terminal="END")

    def bad(_state):
        return {"not_a_channel": 1}

    g.add_node("n", bad)
    g.add_edge("n", "END")
    with pytest.raises(Exception):
        g.run()


def final_not_published(g) -> bool:
    # run aborted; ensure we never recorded a successful publish law
    return not any(
        e.get("event") == "node_ok" and e.get("node") == "publish" for e in g.audit_log
    )
