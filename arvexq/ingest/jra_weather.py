"""Compatibility import; implementation is owned by responsibility 004."""
import importlib as _importlib
import sys as _sys
_implementation = _importlib.import_module("arvexq.components.item_004.jra_weather")
_sys.modules[__name__] = _implementation
