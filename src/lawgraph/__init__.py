"""Minimal product-law graph runtime (portfolio demo)."""

from .graph import Graph, GraphError, LawViolation
from .state import Channel, StateSchema

__all__ = [
    "Channel",
    "StateSchema",
    "Graph",
    "GraphError",
    "LawViolation",
]
__version__ = "0.1.0"
