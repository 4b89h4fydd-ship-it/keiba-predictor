"""Inventory every tracked file and Python dependency without importing the app."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def domain(path: str) -> str:
    if '/betting/' in path or 'ticket' in path or '/backtest/' in path:
        return '買い目' if '/backtest/' not in path else 'データ分析'
    if 'special_selection' in path or 'special_forecast' in path:
        return '特別予想'
    if '/selection/' in path or '/morning/' in path or 'morning_pick' in path:
        return '厳選レース'
    if '/ui/' in path:
        return 'アプリ画面'
    if '/prediction/' in path or '/domain/legacy_evaluation' in path or 'ability' in path or 'pace_prediction' in path:
        return '予想ロジック'
    if '/features/' in path or 'career_analysis' in path or path.startswith('backtest'):
        return 'データ分析'
    if any(x in path for x in ('/ingest/', '/databanks/', '/normalize/', '/storage/')):
        return 'データ管理'
    return 'システム基盤'


def analyze_python(text: str) -> dict:
    tree = ast.parse(text)
    # Legacy installer strings are executable dependencies too.
    legacy = []
    for node in tree.body:
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                and any(isinstance(t, ast.Name) and t.id == 'SOURCE' for t in node.targets)):
            try:
                legacy.append(ast.parse(ast.literal_eval(node.value)))
            except SyntaxError:
                pass  # Some build scripts name embedded JavaScript SOURCE too.
    trees = [tree, *legacy]
    imports = set()
    symbols = []
    for current in trees:
        for node in ast.walk(current):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add('.' * node.level + (node.module or ''))
        for node in current.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append({'name': node.name, 'lines': node.end_lineno - node.lineno + 1,
                                'line': node.lineno, 'legacy_source': current is not tree,
                                'referenced_names': sorted({n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)})})
    return {'imports': sorted(imports), 'symbols': symbols, 'legacy_installer': bool(legacy)}


def inventory() -> dict:
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    records = []
    for name in sorted(set(paths + untracked) - {''}):
        if name.startswith('docs/refactor/inventory'):
            continue
        path = ROOT / name
        if not path.is_file():
            continue
        data = path.read_bytes()
        item = {'path': name, 'domain_hint': domain(name), 'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest()}
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            text = None
        if text is not None:
            item['lines'] = len(text.splitlines())
            if path.suffix == '.py':
                item.update(analyze_python(text))
            elif path.suffix in ('.js', '.mjs'):
                item['functions'] = re.findall(r'^function\s+(\w+)\s*\(', text, re.M)
                item['required_modules'] = sorted(set(re.findall(r'require\([\'\"]([^\'\"]+)', text)))
            elif path.suffix in ('.yml', '.toml', '.html'):
                item['references'] = sorted(set(re.findall(r'(?:arvexq|scripts)/[\w./-]+', text)))
            if path.suffix in ('.py', '.js', '.mjs', '.css') and item['lines'] > 500:
                item['review_priority'] = '分離優先' if item['lines'] >= 800 else '責任範囲確認'
        records.append(item)
    return {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
            'scope': 'all tracked files plus pending new files; generated dist and local databases excluded',
            'domain_hint_note': 'path-based discovery aid; mixed files require human responsibility review',
            'files': records}


def main():
    global ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    ROOT = args.root.resolve()
    report = inventory()
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for item in sorted(report['files'], key=lambda r: r.get('lines', 0), reverse=True):
        if 'review_priority' in item:
            print(f"{item['lines']:5} {item['review_priority']} {item['path']}")
    print('FILES', len(report['files']))


if __name__ == '__main__':
    main()
