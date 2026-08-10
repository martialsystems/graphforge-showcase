"""Hash-chained audit integrity."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lawgraph import Channel, Graph, StateSchema, verify_audit
from lawgraph.audit import GENESIS, seal_event
from lawgraph.state import last_value


def _tiny_ok_graph() -> Graph:
    schema = StateSchema([Channel("x", last_value, 0)])
    g = Graph(schema, entry="n", terminal="END")

    def n(state):
        return {"x": 1}

    g.add_node("n", n)
    g.add_edge("n", "END")
    return g


def test_audit_chain_verifies_after_run():
    g = _tiny_ok_graph()
    g.run()
    g.verify_audit()
    verify_audit(g.audit_log)
    assert g.audit_log[0]["prev_hash"] == GENESIS
    assert g.audit_log[0]["event"] == "run_start"
    assert g.audit_log[-1]["event"] == "terminal"


def test_tamper_detected():
    g = _tiny_ok_graph()
    g.run()
    log = g.audit_log
    log[1] = dict(log[1])
    log[1]["event"] = "tampered"
    # re-seal wrongly or just mutate hash body
    with pytest.raises(ValueError, match="hash mismatch|prev_hash"):
        verify_audit(log)


def test_seal_links_prev():
    e0 = seal_event(GENESIS, {"event": "a"})
    e1 = seal_event(e0["hash"], {"event": "b"})
    verify_audit([e0, e1])
    assert e1["prev_hash"] == e0["hash"]
