"""Compatibility import; implementation is owned by responsibility 017."""
import importlib as _importlib
import sys as _sys
_implementation = _importlib.import_module("arvexq.components.item_017.course")
_sys.modules[__name__] = _implementation
