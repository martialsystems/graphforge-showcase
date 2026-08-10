"""Hash-chained audit helpers (demo).

Each event carries prev_hash and hash so a post-run verify can detect
tampering. Commercial GraphForge uses a richer store; this is the teachable
shape.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping, MutableMapping, Optional


GENESIS = "0" * 64


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def hash_event(prev_hash: str, event: Mapping[str, Any]) -> str:
    """Hash one audit event body chained to ``prev_hash``."""
    body = {k: v for k, v in event.items() if k not in ("hash", "prev_hash")}
    material = {"prev_hash": prev_hash, "body": body}
    return hashlib.sha256(_canonical(material).encode("utf-8")).hexdigest()


def seal_event(
    prev_hash: str, event: MutableMapping[str, Any]
) -> Dict[str, Any]:
    """Return a copy of ``event`` with prev_hash and hash filled in."""
    out = dict(event)
    out.pop("hash", None)
    out["prev_hash"] = prev_hash
    out["hash"] = hash_event(prev_hash, out)
    return out


def verify_audit(log: List[Mapping[str, Any]]) -> None:
    """
    Raise ValueError if the chain is broken, incomplete, or reordered.

    Empty log is valid (no run yet).
    """
    prev = GENESIS
    for i, raw in enumerate(log):
        if "hash" not in raw or "prev_hash" not in raw:
            raise ValueError(f"audit[{i}] missing hash fields")
        if raw["prev_hash"] != prev:
            raise ValueError(
                f"audit[{i}] prev_hash mismatch: "
                f"expected {prev[:12]}… got {str(raw['prev_hash'])[:12]}…"
            )
        expected = hash_event(prev, raw)
        if raw["hash"] != expected:
            raise ValueError(f"audit[{i}] hash mismatch (tamper or corrupt entry)")
        prev = raw["hash"]


def last_hash(log: List[Mapping[str, Any]]) -> Optional[str]:
    """Return the tip hash, or None if empty."""
    if not log:
        return None
    return str(log[-1].get("hash") or "") or None
