#!/usr/bin/env python3
"""Toy product law: promote a staged dataset only when quality gates pass.

Scenario
--------
A data pipeline walks a promotion graph:

  ingest -> validate -> stage -> promote -> END

Product laws (enforced after specific nodes):

  1. After validate: row_count > 0 and schema_ok is true.
  2. After stage: quality_score must meet the minimum threshold.
  3. After promote: staging digest present; promote forbidden if quality failed.

Same control-plane pattern as the agent release gate, different domain.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawgraph import Channel, Graph, LawViolation, StateSchema
from lawgraph.state import append_list, last_value

MIN_QUALITY = 0.9


def build_pipeline_graph(*, force_low_quality: bool = False) -> Graph:
    schema = StateSchema(
        [
            Channel("source", last_value, ""),
            Channel("row_count", last_value, 0),
            Channel("schema_ok", last_value, False),
            Channel("quality_score", last_value, 0.0),
            Channel("stage_digest", last_value, None),
            Channel("promoted", last_value, False),
            Channel("events", append_list, None),
        ]
    )

    g = Graph(schema, entry="ingest", terminal="END")

    def ingest(state):
        return {
            "source": state.get("source") or "s3://demo/raw/events.parquet",
            "events": ["ingested"],
        }

    def validate(state):
        # Outcome is data; real systems would run a schema checker here.
        rows = int(state.get("row_count") or 0)
        ok = bool(state.get("schema_ok", True)) and rows > 0
        return {
            "row_count": rows,
            "schema_ok": ok,
            "events": ["validated_ok" if ok else "validated_fail"],
        }

    def stage(state):
        if force_low_quality:
            score = 0.4
        else:
            raw = state.get("quality_score")
            score = MIN_QUALITY if raw is None else float(raw)
        return {
            "quality_score": score,
            "stage_digest": "sha256:stage-demo",
            "events": ["staged"],
        }

    def promote(state):
        return {
            "promoted": True,
            "events": ["promoted"],
        }

    def law_schema_valid(state, node):
        if not state.get("schema_ok"):
            raise LawViolation(
                "schema_must_validate",
                node,
                "refusing to continue with invalid or empty schema",
            )
        if int(state.get("row_count") or 0) <= 0:
            raise LawViolation(
                "schema_must_validate",
                node,
                "refusing to continue with zero rows",
            )

    def law_quality_threshold(state, node):
        score = float(state.get("quality_score") or 0.0)
        if score < MIN_QUALITY:
            raise LawViolation(
                "quality_threshold",
                node,
                f"quality_score={score}; need >= {MIN_QUALITY}",
            )

    def law_promote_safe(state, node):
        if not state.get("schema_ok"):
            raise LawViolation(
                "schema_must_validate",
                node,
                "promote blocked: schema invalid",
            )
        score = float(state.get("quality_score") or 0.0)
        if score < MIN_QUALITY:
            raise LawViolation(
                "quality_threshold",
                node,
                "promote blocked: quality below threshold",
            )
        if not state.get("stage_digest"):
            raise LawViolation(
                "stage_digest_required",
                node,
                "promote blocked: missing stage_digest",
            )

    g.add_node("ingest", ingest)
    g.add_node("validate", validate, laws=[("schema_must_validate", law_schema_valid)])
    g.add_node("stage", stage, laws=[("quality_threshold", law_quality_threshold)])
    g.add_node("promote", promote, laws=[("promote_safe", law_promote_safe)])

    g.add_edge("ingest", "validate")
    g.add_edge("validate", "stage")
    g.add_edge("stage", "promote")
    g.add_edge("promote", "END")
    return g


def main() -> int:
    print("=== legal path: schema ok, quality above threshold ===")
    g = build_pipeline_graph(force_low_quality=False)
    final = g.run({"row_count": 1000, "schema_ok": True, "quality_score": 0.95})
    print("promoted:", final["promoted"], "digest:", final["stage_digest"])
    print("events:", final["events"])
    print("audit tail:", g.audit_log[-4:])

    print()
    print("=== illegal path: quality below threshold ===")
    bad = build_pipeline_graph(force_low_quality=True)
    try:
        bad.run({"row_count": 1000, "schema_ok": True})
        print("ERROR: expected LawViolation")
        return 1
    except LawViolation as e:
        print("caught:", e)
        print("audit:", bad.audit_log[-6:])

    print()
    print("=== illegal path: empty / invalid schema ===")
    empty = build_pipeline_graph(force_low_quality=False)
    try:
        empty.run({"row_count": 0, "schema_ok": False})
        print("ERROR: expected LawViolation")
        return 1
    except LawViolation as e:
        print("caught:", e)

    print()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
