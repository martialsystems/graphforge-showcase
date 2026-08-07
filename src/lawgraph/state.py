"""Typed channels and reducers.

State is a fixed map of channel names. Nodes return partial updates.
Each channel has a reducer that merges the update into the previous value.
Unknown channels raise — silent drops are how illegal writes hide.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping


Reducer = Callable[[Any, Any], Any]


def last_value(_old: Any, new: Any) -> Any:
    return new


def append_list(old: Any, new: Any) -> List[Any]:
    base = list(old or [])
    if isinstance(new, list):
        base.extend(new)
    else:
        base.append(new)
    return base


def forbid_write(old: Any, new: Any) -> Any:
    raise ValueError("channel is append-only or sealed; write refused")


@dataclass(frozen=True)
class Channel:
    name: str
    reducer: Reducer = last_value
    default: Any = None


class StateSchema:
    def __init__(self, channels: List[Channel]):
        if not channels:
            raise ValueError("at least one channel required")
        names = [c.name for c in channels]
        if len(names) != len(set(names)):
            raise ValueError("duplicate channel names")
        self._channels = {c.name: c for c in channels}

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self._channels)

    def empty(self) -> Dict[str, Any]:
        return {name: ch.default for name, ch in self._channels.items()}

    def apply(self, state: Mapping[str, Any], update: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(update, Mapping):
            raise TypeError("update must be a mapping")
        out = dict(state)
        for key, value in update.items():
            if key not in self._channels:
                raise KeyError(f"unknown channel: {key!r}")
            ch = self._channels[key]
            out[key] = ch.reducer(out.get(key, ch.default), value)
        return out
