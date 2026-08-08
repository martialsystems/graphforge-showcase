"""Tests for the data-pipeline promotion-gate example.

Illegal promotions must raise. Legal path must promote once.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from examples.data_pipeline_gate import build_pipeline_graph  # noqa: E402
from lawgraph import LawViolation  # noqa: E402


def test_legal_path_promotes():
    g = build_pipeline_graph(force_low_quality=False)
    final = g.run({"row_count": 500, "schema_ok": True, "quality_score": 0.95})
    assert final["promoted"] is True
    assert final["stage_digest"]
    assert "promoted" in final["events"]
    assert any(e.get("event") == "law_ok" for e in g.audit_log)


def test_low_quality_fails_closed():
    g = build_pipeline_graph(force_low_quality=True)
    with pytest.raises(LawViolation) as ei:
        g.run({"row_count": 500, "schema_ok": True})
    assert ei.value.law == "quality_threshold"
    assert ei.value.node == "stage"
    assert not any(
        e.get("event") == "node_ok" and e.get("node") == "promote" for e in g.audit_log
    )


def test_invalid_schema_fails_closed():
    g = build_pipeline_graph(force_low_quality=False)
    with pytest.raises(LawViolation) as ei:
        g.run({"row_count": 0, "schema_ok": False})
    assert ei.value.law == "schema_must_validate"
    assert ei.value.node == "validate"
