from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lawgraph import Channel, StateSchema
from lawgraph.state import append_list, last_value


def test_unknown_channel_raises():
    s = StateSchema([Channel("a", last_value, 0)])
    st = s.empty()
    with pytest.raises(KeyError):
        s.apply(st, {"nope": 1})


def test_append_reducer():
    s = StateSchema([Channel("log", append_list, None)])
    st = s.empty()
    st = s.apply(st, {"log": "a"})
    st = s.apply(st, {"log": ["b", "c"]})
    assert st["log"] == ["a", "b", "c"]


def test_last_value():
    s = StateSchema([Channel("flag", last_value, False)])
    st = s.apply(s.empty(), {"flag": True})
    st = s.apply(st, {"flag": False})
    assert st["flag"] is False
