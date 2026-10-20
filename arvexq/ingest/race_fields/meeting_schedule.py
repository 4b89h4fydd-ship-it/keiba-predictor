"""Compatibility import; implementation is owned by responsibility 010."""
import importlib as _importlib
import sys as _sys
_implementation = _importlib.import_module("arvexq.components.item_010.meeting_schedule")
_sys.modules[__name__] = _implementation
