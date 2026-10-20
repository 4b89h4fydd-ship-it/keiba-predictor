"""Compatibility import; implementation is owned by responsibility 050."""
import importlib as _importlib
import sys as _sys
_implementation = _importlib.import_module("arvexq.components.item_050.corners")
_sys.modules[__name__] = _implementation
