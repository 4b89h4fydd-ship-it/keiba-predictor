"""Source-body assertions follow Stage 3 delegates without executing app/collectors.

Only for legacy tests that extract isolated function bodies. Public route/adapter
behavior is independently exercised by test_stage4_box_connections.py.
"""
import ast
from pathlib import Path


def implementation_source():
    source = Path('app.py').read_text(encoding='utf-8')
    lines = source.splitlines(keepends=True)
    removed = set()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
                   and d.func.id == '_arvexq_route_wraps' for d in node.decorator_list):
                first = min([node.lineno] + [d.lineno for d in node.decorator_list])
                removed.update(range(first - 1, node.end_lineno))
        elif isinstance(node, ast.ImportFrom):
            if any((a.asname or '').startswith(('_arvexq_box_', '_arvexq_route_wraps')) for a in node.names):
                removed.update(range(node.lineno - 1, node.end_lineno))
        elif isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                   and t.value.id.startswith('_arvexq_original_') and t.attr in ('__name__', '__qualname__')
                   for t in node.targets):
                removed.update(range(node.lineno - 1, node.end_lineno))
    result = ''.join(line for i, line in enumerate(lines) if i not in removed)
    return result.replace('def _arvexq_original_', 'def ')
