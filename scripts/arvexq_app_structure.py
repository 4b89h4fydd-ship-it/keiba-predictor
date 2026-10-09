"""Static structural audit for modularizing the oversized app.py safely."""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app.py"


def report(path: Path = SOURCE) -> None:
    raw = path.read_text(encoding="utf-8")
    tree = ast.parse(raw, filename=str(path))
    lines = raw.splitlines(keepends=True)
    lengths = [len(s.encode("utf-8")) for s in lines]
    tops = []
    names = Counter()
    for node in tree.body:
        first = getattr(node, "lineno", 1)
        last = getattr(node, "end_lineno", first)
        size = sum(lengths[first - 1:last])
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind, name = type(node).__name__, node.name
            names[name] += 1
        elif isinstance(node, ast.Assign):
            kind = "Assign"
            name = ",".join(t.id for t in node.targets if isinstance(t, ast.Name)) or "<complex>"
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            kind = "Call"
            fn = node.value.func
            name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else "<call>"
        else:
            kind, name = type(node).__name__, "-"
        tops.append((size, first, last, kind, name))
    total = len(raw.encode("utf-8"))
    print("APP_AUDIT", "bytes="+str(total), "lines="+str(len(lines)),
          "top_level_nodes="+str(len(tree.body)), "functions="+str(sum(n[3] in ("FunctionDef", "AsyncFunctionDef") for n in tops)),
          "classes="+str(sum(n[3] == "ClassDef" for n in tops)))
    print("APP_AUDIT_DUPLICATE_DEFS", sorted((n, count) for n, count in names.items() if count > 1))
    print("APP_AUDIT_LARGEST_NODES")
    for size, first, last, kind, name in sorted(tops, reverse=True)[:70]:
        print(f"APP_NODE bytes={size:>8} lines={first:>6}-{last:<6} type={kind:<17} name={name}")
    # Identify top-level functions that can be moved without closing over app.py
    # globals, its FastAPI app, or database state. Python's symbol table rather
    # than regex is used so nested function loads are included.
    import builtins
    import symtable
    module_symbols = symtable.symtable(raw, str(path), "exec")
    pure = []
    globals_by_function = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.decorator_list:
            continue
        if node.args.defaults or any(x is not None for x in node.args.kw_defaults):
            continue
        tables = [x for x in module_symbols.get_children()
                  if x.get_name() == node.name and x.get_lineno() == node.lineno]
        if len(tables) != 1:
            continue
        pending = tables[:]
        used = set()
        while pending:
            entry = pending.pop()
            used.update(entry.get_globals())
            pending.extend(entry.get_children())
        externals = sorted(x for x in used if x not in vars(builtins))
        globals_by_function[node.name] = externals
        if not externals and node.end_lineno - node.lineno >= 4:
            pure.append((node.end_lineno-node.lineno, node.name, node.lineno))
    print("APP_PURE_EXTRACTION_CANDIDATES", sorted(pure, reverse=True)[:50])
    print("APP_PURE_REVIEW_TARGETS")
    for n in ("_parse_payouts", "_jra_parse_past_cell", "_parse_recent_cell",
              "_jra_profile_runs", "_jra_parse_race_summary",
              "_parse_nar_live_odds_html", "_jra_parse_result", "odds_refresh"):
        print("APP_DEP", n, globals_by_function.get(n))
    print("APP_AUDIT_MODULE_MARKERS")
    for size, first, last, kind, name in tops:
        if kind == "Call" and name in ("exec", "eval"):
            print("APP_EXEC", first, last, lines[first-1][:200].rstrip())
        elif kind == "Assign" and any(w in name for w in ("INDEX","JS","CSS","MANIFEST","SW","ICONS")):
            print("APP_ASSET", name, size, first, last)


if __name__ == "__main__":
    report()
