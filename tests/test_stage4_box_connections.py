"""Offline Stage 4 contract tests. These do not certify live providers or predictions."""
import asyncio
import ast
import gzip
import importlib
import inspect
import json
from pathlib import Path
from unittest.mock import Mock, patch
from functools import lru_cache

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/independence/route-connection-stage3-20261021'
RECORDS = json.loads(gzip.decompress((DOC / 'connections.json.gz').read_bytes()))


@lru_cache(None)
def parsed(path):
    return ast.parse((ROOT / path).read_text())


def module(path):
    return importlib.import_module(path.removesuffix('.py').removesuffix('/__init__').replace('/', '.'))


ALIASES = [r for r in RECORDS if r['kind'] in ('python-object-alias', 'python-module-object-alias')]


@pytest.mark.parametrize('record', ALIASES, ids=lambda r: f"{r['items']}-{r['caller']['path']}-{r['caller'].get('imported', r['caller'].get('local_name'))}")
def test_original_object_and_actual_caller_binding(record):
    box = module(record['box_target'])
    original = module(record['original_source'])
    if record['kind'] == 'python-module-object-alias':
        expected = original
        actual = box.original
    else:
        expected = getattr(original, record['caller']['imported'])
        actual = getattr(box, record['caller']['imported'])
    assert actual is expected, 'alias must preserve caches, types and module state'
    # Local imports / installer aliases deleted after exec have no module-level binding.
    # Execute the actual import node separately; never run collector CLI main functions.
    path = ROOT / record['caller']['path']
    tree = parsed(record['caller']['path'])
    local = record['caller'].get('local_name', record['caller'].get('imported'))
    box_module = record['box_target'].removesuffix('.py').replace('/', '.')
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
             and n.module == box_module
             and any((a.asname or a.name) == local for a in n.names)]
    assert nodes, 'the actual caller must import this box'
    namespace = {}
    exec(compile(ast.Module(body=[nodes[0]], type_ignores=[]), str(path), 'exec'), namespace)
    assert namespace[local] is expected
    # verified_holdout has an unrelated missing retired module already on main.
    if record['caller']['path'] != 'scripts/arvexq_verified_holdout.py':
        caller = module(record['caller']['path'])
        if hasattr(caller, local):
            assert getattr(caller, local) is expected


FORWARDS = [r for r in RECORDS if r['kind'] == 'existing-callable-forward']


@pytest.mark.parametrize('record', FORWARDS, ids=lambda r: f"{r['items']}-{r['caller']['symbol']}")
def test_actual_public_entry_forwards_once_without_copying_or_swallowing(record):
    import app
    name = record['caller']['symbol']
    public = getattr(app, name)
    original = getattr(app, record['original_private_name'])
    boxfn = getattr(module(record['box_target']), name)
    assert inspect.signature(public) == inspect.signature(original)
    assert inspect.iscoroutinefunction(public) == inspect.iscoroutinefunction(original)
    assert inspect.unwrap(public) is original
    payload = {'horses': [{'circuit': '中央', 'recentRaces': []}], 'missing': None}
    result = {'data': payload}
    calls = []
    async def async_spy(*args, **kwargs):
        calls.append((args, kwargs))
        return result
    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return result
    implementation = async_spy if inspect.iscoroutinefunction(public) else spy
    with patch.dict(public.__globals__, {record['original_private_name']: implementation}):
        value = public(payload, keep=payload)
        if inspect.isawaitable(value):
            value = asyncio.run(value)
        assert value is result
    assert len(calls) == 1
    assert calls[0][0][0] is payload and calls[0][1]['keep'] is payload
    error = ValueError('stage4 missing-data sentinel')
    def fail(*args, **kwargs):
        raise error
    with pytest.raises(ValueError) as caught:
        boxfn(fail, payload)
    assert caught.value is error


@pytest.mark.parametrize('record', [r for r in RECORDS if r['kind'] == 'unchanged-asset-load'], ids=lambda r: str(r['items']))
def test_assets_read_original_bytes(record):
    tree = __import__('ast').parse((ROOT / record['box_target']).read_text())
    import ast
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            paths = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            if record['original_source'] == 'arvexq/ui/static/' + paths[0]:
                value = getattr(module(record['box_target']), node.name)()
                assert value == (ROOT / record['original_source']).read_text(encoding='utf-8')


def test_audit_forward_preserves_input_output_and_error():
    from arvexq.components.item_196.audit_route import audit
    manifest = {'requirements': []}
    output = {'ok': False, 'missing': ['sentinel']}
    fn = Mock(return_value=output)
    assert audit(fn, manifest) is output
    fn.assert_called_once_with(manifest)


def test_fastapi_registration_keeps_unwrapped_signatures():
    import app
    from fastapi.routing import APIRoute
    for route in app.app.routes:
        if isinstance(route, APIRoute) and hasattr(route.endpoint, '__wrapped__'):
            assert inspect.signature(route.endpoint) == inspect.signature(route.endpoint.__wrapped__)
            assert not {'args', 'kwargs'} & {p.name for p in route.dependant.query_params}
    assert len(app.app.openapi()['paths']) > 100
