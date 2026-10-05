#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

PATH = Path("app.py")
source = PATH.read_text(encoding="utf-8")
lines = source.splitlines()
tree = ast.parse(source)

target_names = {
    "_winner_learning_profile",
    "_learning_metric",
    "_learning_races",
}

found = []
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in target_names:
        found.append(node)

print("legacy-learning-audit functions", [n.name for n in found])
for node in sorted(found, key=lambda n: n.lineno):
    start = max(1, node.lineno)
    end = min(len(lines), node.end_lineno or node.lineno)
    print(f"\n===== {node.name} {start}-{end} =====")
    for i in range(start, end + 1):
        print(f"{i:05d}: {lines[i-1]}")

# Also show every call site, because leakage can happen in the caller even if the helper is clean.
for name in sorted(target_names):
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            called = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            if called == name:
                sites.append(node.lineno)
    print(f"\nCALLS {name}: {sites}")
    for lineno in sites:
        a = max(1, lineno - 5)
        b = min(len(lines), lineno + 8)
        for i in range(a, b + 1):
            print(f"{i:05d}: {lines[i-1]}")
        print("---")

missing = target_names - {n.name for n in found}
if missing:
    raise SystemExit(f"missing legacy learning helpers: {sorted(missing)}")
