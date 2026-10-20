"""Preserve original public corner-order implementation and observed ties."""
import importlib


def test_corner_order_old_import_is_owned_implementation():
    old = importlib.import_module("arvexq.ingest.corner_order")
    owned = importlib.import_module("arvexq.components.item_075.corner_order")
    assert old is owned
    assert old.parse_corner_order("1,(2,3),4") == {1: 1, 2: 2, 3: 2, 4: 4}
