"""Regression tests for standalone NAR corner-order parsing."""
from arvexq.ingest.corner_order import _top_level_tokens, parse_corner_order

def test_tied_corner_positions():
    assert _top_level_tokens("1,(2,7),4") == ["1", "(2,7)", "4"]
    assert parse_corner_order("1,(2,7),4") == {1: 1, 2: 2, 7: 2, 4: 4}

def test_empty_and_separators():
    assert parse_corner_order("") == {}
    assert parse_corner_order("1-2,3") == {1: 1, 2: 2, 3: 3}
