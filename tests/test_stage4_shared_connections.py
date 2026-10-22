"""Shared boxes reuse one callable and perform no fan-out or duplicated work."""
import importlib
import json
from pathlib import Path
from unittest.mock import Mock
import pytest

ALIASES = json.loads((Path(__file__).resolve().parents[1] / 'docs/independence/route-connection-stage3-20261021/shared-bindings.json').read_text())['aliases']


@pytest.mark.parametrize('binding', ALIASES, ids=lambda b: f"{b['from_item']:03}->{b['to_item']:03}-{b['symbol']}")
def test_shared_object_and_single_execution(binding):
    consumer = importlib.import_module(f"arvexq.components.item_{binding['from_item']:03}.shared_routes")
    owner = importlib.import_module(binding['module'])
    actual = getattr(consumer, binding['symbol'])
    assert actual is getattr(owner, binding['symbol'])
    data = {'horses': [], 'missing': None}
    implementation = Mock(return_value=data)
    assert actual(implementation, data) is data
    implementation.assert_called_once_with(data)
