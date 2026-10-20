"""Compatibility import; implementation is owned by responsibility 063."""
import importlib as _importlib
import sys as _sys
_implementation = _importlib.import_module("arvexq.components.item_063.netkeiba_odds_parser")
_sys.modules[__name__] = _implementation
