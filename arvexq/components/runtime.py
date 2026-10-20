"""Install fixed, checked-in component definitions in the existing app context.

This transitional composition bridge preserves shared locks, stores, decorated
routes, function signatures and app-global patches while moving source ownership
out of app.py. It accepts neither user source text nor arbitrary module paths.
Importing a box alone never starts services or opens a database.
"""
from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def component_path(item_id: int) -> Path:
    if type(item_id) is not int or not 1 <= item_id <= 200:
        raise ValueError('component ID must be an integer from 1 to 200')
    return ROOT / f'item_{item_id:03d}'


@lru_cache(maxsize=200)
def _definitions(item_id):
    path = component_path(item_id) / 'implementation.py'
    source = path.read_text(encoding='utf-8')
    definitions = {}
    for node in ast.parse(source, filename=str(path)).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions[node.name] = node
    return str(path), source, definitions


def install_component(item_id: int, name: str, namespace: dict) -> None:
    """Install one owned definition exactly at its former composition point."""
    filename, _, definitions = _definitions(item_id)
    if name not in definitions:
        raise ValueError(f'{item_id:03d} does not own {name!r}')
    code = compile(ast.Module(body=[definitions[name]], type_ignores=[]),
                   filename, 'exec', dont_inherit=True)
    exec(code, namespace)


def composed_app_source(path=None):
    """Read the real assembled source for static contracts without importing app."""
    path = Path(path) if path is not None else ROOT.parents[1] / 'app.py'
    source = path.read_text(encoding='utf-8')
    lines = source.splitlines(keepends=True)
    replacements = []
    for node in ast.parse(source).body:
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == 'install_component'):
            continue
        item_id, name = (ast.literal_eval(a) for a in node.value.args[:2])
        _, owned_source, definitions = _definitions(item_id)
        definition = definitions[name]
        start = min([definition.lineno] + [d.lineno for d in definition.decorator_list])
        text = ''.join(owned_source.splitlines(keepends=True)[start - 1:definition.end_lineno])
        replacements.append((node.lineno - 1, node.end_lineno, text))
    for start, end, text in reversed(replacements):
        lines[start:end] = [text]
    return ''.join(lines)
