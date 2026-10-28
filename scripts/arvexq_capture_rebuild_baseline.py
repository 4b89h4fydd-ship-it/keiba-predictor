"""Capture exact local presentation assets and API route declarations, offline.

This is a source baseline, not a browser/screenshot or live API verification.
"""
import ast
import hashlib
import json
import subprocess
from pathlib import Path


def capture(root):
    files = sorted(set(root.glob('arvexq/ui/static/**/*.js')) |
                   set(root.glob('arvexq/ui/static/**/*.css')) |
                   {root/'dist/index.html', root/'workers/api.mjs', root/'workers/web.mjs'})
    assets = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in files if p.is_file()}
    routes = []
    for node in ast.walk(ast.parse((root/'app.py').read_text())):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr in ('get', 'post', 'put', 'delete', 'patch') and decorator.args:
                        if isinstance(decorator.args[0], ast.Constant):
                            routes.append({'method': decorator.func.attr.upper(),
                                           'path': decorator.args[0].value, 'handler': node.name})
    return {'version': 1, 'scope': 'local-source-only',
            'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
            'assets': assets, 'routes': sorted(routes, key=lambda r:(r['path'], r['method'])),
            'browser_verified': False, 'production_verified': False}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    target = root/'docs/rebuild/baseline-20261027.json'
    with target.open('x') as stream:
        json.dump(capture(root), stream, ensure_ascii=False, indent=2)
        stream.write('\n')
