"""Stale-over-fresh and freeze fail-safes (autonomous)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from examples.site_publish_gate import build_site_publish_graph  # noqa: E402
from lawgraph import LawViolation  # noqa: E402


def test_legal_publish_advances_dest():
    g = build_site_publish_graph()
    final = g.run({"src_track": 100, "dest_track": 50, "freeze_locked": True})
    assert final["published"] is True
    assert final["dest_track"] == 100
    g.verify_audit()


def test_stale_src_blocked():
    g = build_site_publish_graph(force_stale_src=True)
    with pytest.raises(LawViolation) as ei:
        g.run({"src_track": 10, "dest_track": 50, "freeze_locked": True})
    assert ei.value.law == "stale_over_fresh_block"
    assert not any(
        e.get("event") == "node_ok" and e.get("node") == "publish"
        for e in g.audit_log
    )
    g.verify_audit()


def test_freeze_cleared_blocked():
    g = build_site_publish_graph(force_unfreeze=True)
    with pytest.raises(LawViolation) as ei:
        g.run({"src_track": 100, "dest_track": 50, "freeze_locked": True})
    assert ei.value.law == "freeze_untouched"


def test_zero_src_track_is_not_treated_as_missing():
    """src_track 0 is a real track; must not be rewritten to 100."""
    g = build_site_publish_graph()
    with pytest.raises(LawViolation) as ei:
        g.run({"src_track": 0, "dest_track": 50, "freeze_locked": True})
    assert ei.value.law == "stale_over_fresh_block"
    assert "src_track=0" in ei.value.detail
    assert not any(
        e.get("event") == "node_ok" and e.get("node") == "publish"
        for e in g.audit_log
    )


def test_zero_src_equals_zero_dest_is_allowed():
    g = build_site_publish_graph()
    final = g.run({"src_track": 0, "dest_track": 0, "freeze_locked": True})
    assert final["published"] is True
    assert final["dest_track"] == 0
    assert final["src_track"] == 0
    g.verify_audit()
