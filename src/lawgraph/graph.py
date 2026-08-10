"""Compile and run a small state graph with fail-closed laws.

This is intentionally small. Production GraphForge (private, proprietary)
adds checkpoints, catalog/trace, license packaging, and more.
This package only shows the control-plane idea: explicit topology + typed
merges + laws that reject illegal transitions + hash-chained audit.

Fail-safes are mechanical and autonomous: max_steps, fail-closed laws,
sealed channels (via schema reducers), and an audit chain. There is no
human-approval step in the runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .audit import GENESIS, seal_event, verify_audit
from .state import StateSchema


NodeFn = Callable[[Dict[str, Any]], Optional[Mapping[str, Any]]]
LawFn = Callable[[Dict[str, Any], str], None]
CondFn = Callable[[Dict[str, Any]], str]


class GraphError(RuntimeError):
    """Runtime error for illegal graph structure or execution faults."""


class LawViolation(GraphError):
    """Raised when a product law fails after a node (fail closed)."""

    def __init__(self, law: str, node: str, detail: str) -> None:
        """Record which law failed, on which node, and a short detail string."""
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
    """Directed graph over a StateSchema with optional post-node laws."""

    def __init__(
        self, schema: StateSchema, *, entry: str, terminal: str = "END"
    ) -> None:
        """Create an empty graph; call ``add_node`` / ``add_edge`` before ``run``."""
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
        laws: Optional[List[Tuple[str, LawFn]]] = None,
    ) -> None:
        """Register a node and optional laws that run after a successful write."""
        if name in self._nodes or name == self.terminal:
            raise GraphError(f"node already exists: {name}")
        self._nodes[name] = _Node(name=name, fn=fn, laws=list(laws or []))

    def add_edge(self, src: str, dst: str) -> None:
        """Add a fixed edge from ``src`` to ``dst``."""
        if src in self._cond:
            raise GraphError(f"{src} already has a conditional edge")
        self._edges[src] = dst

    def add_conditional_edges(
        self, src: str, cond: CondFn, mapping: Mapping[str, str]
    ) -> None:
        """Route from ``src`` using ``cond(state)`` keys into ``mapping``."""
        if src in self._edges:
            raise GraphError(f"{src} already has a fixed edge")
        self._cond[src] = (cond, dict(mapping))

    def require_law(self, node: str, law_name: str, law_fn: LawFn) -> None:
        """Attach an additional law to an existing node."""
        if node not in self._nodes:
            raise GraphError(f"unknown node: {node}")
        self._nodes[node].laws.append((law_name, law_fn))

    @property
    def audit_log(self) -> List[Dict[str, Any]]:
        """Copy of node/law audit events from the last ``run``."""
        return list(self._audit)

    def verify_audit(self) -> None:
        """Raise ValueError if the last run's audit chain is broken."""
        verify_audit(self._audit)

    def _record(self, event: Mapping[str, Any]) -> None:
        prev = self._audit[-1]["hash"] if self._audit else GENESIS
        self._audit.append(seal_event(prev, dict(event)))

    def run(
        self,
        initial: Optional[Mapping[str, Any]] = None,
        *,
        max_steps: int = 32,
    ) -> Dict[str, Any]:
        """
        Execute from ``entry`` until ``terminal``; raise on law failure.

        Fail-safes (all autonomous):
        - ``max_steps``: runaway loops abort with GraphError
        - laws after nodes: LawViolation fails closed (no further edges)
        - illegal channel writes: GraphError; state from that write is not kept
          as a successful step (apply raises before laws/next)
        """
        if self.entry not in self._nodes:
            raise GraphError(f"entry node missing: {self.entry}")
        if max_steps < 1:
            raise GraphError("max_steps must be >= 1")

        state = self.schema.empty()
        if initial:
            state = self.schema.apply(state, dict(initial))

        node = self.entry
        steps = 0
        self._audit.clear()
        self._record({"event": "run_start", "entry": self.entry, "max_steps": max_steps})

        while node != self.terminal:
            if steps >= max_steps:
                self._record(
                    {
                        "event": "budget_fail",
                        "node": node,
                        "max_steps": max_steps,
                    }
                )
                raise GraphError(
                    f"max_steps={max_steps} exceeded at {node!r} "
                    f"(autonomous budget fail-safe)"
                )
            if node not in self._nodes:
                raise GraphError(f"unknown node during run: {node}")

            steps += 1
            spec = self._nodes[node]
            update = spec.fn(dict(state)) or {}
            try:
                state = self.schema.apply(state, update)
            except KeyError as e:
                self._record(
                    {
                        "event": "write_fail",
                        "node": node,
                        "detail": str(e),
                    }
                )
                raise GraphError(f"node {node!r} wrote illegal channel: {e}") from e
            except ValueError as e:
                # sealed / forbid_write reducers
                self._record(
                    {
                        "event": "write_fail",
                        "node": node,
                        "detail": str(e),
                    }
                )
                raise GraphError(f"node {node!r} sealed-channel write: {e}") from e

            for law_name, law_fn in spec.laws:
                try:
                    law_fn(dict(state), node)
                    self._record(
                        {
                            "event": "law_ok",
                            "node": node,
                            "law": law_name,
                        }
                    )
                except LawViolation:
                    self._record(
                        {
                            "event": "law_fail",
                            "node": node,
                            "law": law_name,
                        }
                    )
                    raise
                except Exception as e:
                    viol = LawViolation(law_name, node, str(e))
                    self._record(
                        {
                            "event": "law_fail",
                            "node": node,
                            "law": law_name,
                            "detail": str(e),
                        }
                    )
                    raise viol from e

            self._record({"event": "node_ok", "node": node, "step": steps})
            node = self._next(node, state)

        self._record({"event": "terminal", "steps": steps})
        # Self-check: chain must verify after a clean terminal
        verify_audit(self._audit)
        return state

    def _next(self, node: str, state: Dict[str, Any]) -> str:
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
