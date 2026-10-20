"""Read the fixed component catalog without initializing application services."""
from __future__ import annotations
import json
from functools import lru_cache
from .runtime import component_path, ROOT


@lru_cache(maxsize=200)
def _spec(item_id):
    return json.loads((component_path(item_id) / 'component.json').read_text(encoding='utf-8'))


def describe(item_id):
    # Callers cannot mutate the cached ownership map.
    import copy
    return copy.deepcopy(_spec(item_id))


def all_components():
    return [describe(item_id) for item_id in range(1, 201)]


def assemble_ui():
    """Compose canonical UI fragments in original order, preserving every byte."""
    import hashlib
    manifest = json.loads((ROOT / 'ui-assembly.json').read_text(encoding='utf-8'))
    repository = ROOT.parents[1]
    chunks = []
    for part in manifest['parts']:
        path = (repository / part['path']).resolve()
        if ROOT.resolve() not in path.parents:
            raise ValueError('UI fragment must remain inside the component tree')
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != part['sha256']:
            raise ValueError(f'UI source receipt mismatch: {part["path"]}')
        chunks.append(content)
    combined = b''.join(chunks)
    if hashlib.sha256(combined).hexdigest() != manifest['sha256']:
        raise ValueError('UI assembly changed unexpectedly')
    return combined.decode('utf-8')
