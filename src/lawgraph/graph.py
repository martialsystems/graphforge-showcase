"""Compile and run a small state graph with fail-closed laws.

This is intentionally small. Production GraphForge (private, proprietary)
adds checkpoints, interrupts, catalog/trace, license packaging, and more.
This package only shows the control-plane idea: explicit topology + typed
merges + laws that reject illegal transitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .state import StateSchema


NodeFn = Callable[[Dict[str, Any]], Optional[Mapping[str, Any]]]
LawFn = Callable[[Dict[str, Any], str], None]
CondFn = Callable[[Dict[str, Any]], str]


class GraphError(RuntimeError):
    pass


class LawViolation(GraphError):
    """Raised when a product law fails after a node (fail closed)."""

    def __init__(self, law: str, node: str, detail: str):
        self.law = law
        self.node = node
        self.detail = detail
        super().__init__(f"law {law!r} failed after node {node!r}: {detail}")


@dataclass
class _Node:
    name: str
    fn: NodeFn
    laws: List[Tuple[str, LawFn]] = field(default_factory=list)


class Graph:
    def __init__(self, schema: StateSchema, *, entry: str, terminal: str = "END"):
        self.schema = schema
        self.entry = entry
        self.terminal = terminal
        self._nodes: Dict[str, _Node] = {}
        self._edges: Dict[str, str] = {}
        self._cond: Dict[str, Tuple[CondFn, Dict[str, str]]] = {}
        self._audit: List[Dict[str, Any]] = []

    def add_node(
        self,
        name: str,
        fn: NodeFn,
        *,
        laws: Optional[list[tuple[str, LawFn]]] = None,
    ) -> None:
        if name in self._nodes or name == self.terminal:
            raise GraphError(f"node already exists: {name}")
        self._nodes[name] = _Node(name=name, fn=fn, laws=list(laws or []))

    def add_edge(self, src: str, dst: str) -> None:
        if src in self._cond:
            raise GraphError(f"{src} already has a conditional edge")
        self._edges[src] = dst

    def add_conditional_edges(
        self, src: str, cond: CondFn, mapping: Mapping[str, str]
    ) -> None:
        if src in self._edges:
            raise GraphError(f"{src} already has a fixed edge")
        self._cond[src] = (cond, dict(mapping))

    def require_law(self, node: str, law_name: str, law_fn: LawFn) -> None:
        if node not in self._nodes:
            raise GraphError(f"unknown node: {node}")
        self._nodes[node].laws.append((law_name, law_fn))

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit)

    def run(
        self,
        initial: Optional[Mapping[str, Any]] = None,
        *,
        max_steps: int = 32,
    ) -> dict[str, Any]:
        if self.entry not in self._nodes:
            raise GraphError(f"entry node missing: {self.entry}")

        state = self.schema.empty()
        if initial:
            # initial values go through reducers as first write
            state = self.schema.apply(state, dict(initial))

        node = self.entry
        steps = 0
        self._audit.clear()

        while node != self.terminal:
            if steps >= max_steps:
                raise GraphError(f"max_steps={max_steps} exceeded at {node!r}")
            if node not in self._nodes:
                raise GraphError(f"unknown node during run: {node}")

            steps += 1
            spec = self._nodes[node]
            update = spec.fn(dict(state)) or {}
            try:
                state = self.schema.apply(state, update)
            except KeyError as e:
                raise GraphError(f"node {node!r} wrote illegal channel: {e}") from e

            for law_name, law_fn in spec.laws:
                try:
                    law_fn(dict(state), node)
                    self._audit.append(
                        {
                            "event": "law_ok",
                            "node": node,
                            "law": law_name,
                        }
                    )
                except LawViolation:
                    self._audit.append(
                        {
                            "event": "law_fail",
                            "node": node,
                            "law": law_name,
                        }
                    )
                    raise
                except Exception as e:
                    # laws must raise LawViolation for expected failures
                    viol = LawViolation(law_name, node, str(e))
                    self._audit.append(
                        {
                            "event": "law_fail",
                            "node": node,
                            "law": law_name,
                            "detail": str(e),
                        }
                    )
                    raise viol from e

            self._audit.append({"event": "node_ok", "node": node, "step": steps})
            node = self._next(node, state)

        self._audit.append({"event": "terminal", "steps": steps})
        return state

    def _next(self, node: str, state: dict[str, Any]) -> str:
        if node in self._cond:
            cond, mapping = self._cond[node]
            key = cond(state)
            if key not in mapping:
                raise GraphError(
                    f"conditional from {node!r} returned {key!r}; "
                    f"expected one of {sorted(mapping)}"
                )
            return mapping[key]
        if node in self._edges:
            return self._edges[node]
        raise GraphError(f"no outgoing edge from {node!r}")
