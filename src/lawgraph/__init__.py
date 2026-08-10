"""Minimal product-law graph runtime (portfolio demo)."""

from .audit import verify_audit
from .graph import Graph, GraphError, LawViolation
from .state import Channel, StateSchema

__all__ = [
    "Channel",
    "StateSchema",
    "Graph",
    "GraphError",
    "LawViolation",
    "verify_audit",
]
__version__ = "0.2.0"
