"""Compatibility import; implementation is owned by responsibility 060."""
import importlib as _importlib
import sys as _sys
_implementation = _importlib.import_module("arvexq.components.item_060.place_odds")
_sys.modules[__name__] = _implementation
