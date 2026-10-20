"""Compatibility import; implementation is owned by responsibility 013."""
import importlib as _importlib
import sys as _sys
_implementation = _importlib.import_module("arvexq.components.item_013.grade_class")
_sys.modules[__name__] = _implementation
