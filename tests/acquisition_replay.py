"""Offline replay of original PR #13 acquisition functions (test code only)."""
import ast
import copy
import gzip
import io
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RECORDS = json.loads((ROOT / 'docs/refactor/stage4-functions.json').read_text())
BASELINE = gzip.decompress((ROOT / 'tests/fixtures/acquisition-95f2595.py.gz').read_bytes()).decode()
BASELINE_TREE = ast.parse(BASELINE)
FIXED_TIME = 1791673200.0


def original_namespace(app):
    namespace = dict(vars(app))
    # Only original function definitions are compiled. No original app startup,
    # store construction, network requests or worker initialization are replayed.
    exec(compile(BASELINE, '<acquisition-95f2595>', 'exec'), namespace)
    return namespace


def caches(app):
    names = {k for r in RECORDS for k in r.get('owned_state', []) if 'cache' in k or 'lookup' in k}
    return [getattr(app, name) for name in sorted(names) if isinstance(getattr(app, name), dict)]


def compare(app, name, args=(), *, responses=(), overrides=None, env=None, expected_error=None, setup=None, capture=None):
    """Compare return data, input mutations, cache state and exact HTTP requests."""
    outcomes = []
    cache_objects = caches(app)
    saved = [copy.deepcopy(c) for c in cache_objects]
    try:
        for original in (True, False):
            if setup:
                setup()
            for cache in cache_objects:
                cache.clear()
            namespace = original_namespace(app) if original else vars(app)
            values = copy.deepcopy(args)
            pending = iter(responses)
            calls = []

            def get(request, timeout):
                calls.append((request.full_url, request.data, sorted(request.header_items()), timeout))
                item = next(pending)  # Unexpected/repeated requests fail the test.
                if isinstance(item, Exception):
                    raise item
                return io.BytesIO(item.encode() if isinstance(item, str) else item)

            with patch.dict(namespace, overrides or {}), patch.dict('os.environ', env or {}), \
                    patch('urllib.request.urlopen', get), patch('time.time', return_value=FIXED_TIME):
                try:
                    result = namespace[name](*values)
                    error = None
                except Exception as exc:
                    result = None
                    error = (type(exc).__name__, str(exc))
            outcomes.append((result, values, calls, [copy.deepcopy(c) for c in cache_objects],
                             copy.deepcopy(capture()) if capture else None, error))
        assert outcomes[0] == outcomes[1], f'{name}: acquisition output/request/cache mismatch'
        if expected_error:
            assert outcomes[1][-1][0] == expected_error
        else:
            assert outcomes[1][-1] is None, f'{name}: unexpected error {outcomes[1][-1]}'
        return outcomes[1][0], outcomes[1][2]
    finally:
        for cache, old in zip(cache_objects, saved):
            cache.clear()
            cache.update(old)
