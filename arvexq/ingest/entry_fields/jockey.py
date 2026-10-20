"""Compatibility import; implementation is owned by responsibility 031."""
import importlib as _importlib
import sys as _sys
_implementation = _importlib.import_module("arvexq.components.item_031.jockey")
_sys.modules[__name__] = _implementation
