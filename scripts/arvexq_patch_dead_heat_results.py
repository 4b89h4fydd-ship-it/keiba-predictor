#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

APP = Path("app.py")


def main() -> None:
    src = APP.read_text(encoding="utf-8")
    tree = ast.parse(src)
    target = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_nar_official_result_fast":
            target = node
            break
    if target is None:
        raise SystemExit("PATCH_ABORT: _nar_official_result_fast not found")

    lines = src.splitlines(keepends=True)
    start = target.lineno - 1
    end = target.end_lineno or target.lineno
    block = "".join(lines[start:end])

    old = '        ranks={int(x.get("finish") or 0) for x in finishers}\n        if not all(i in ranks for i in (1,2,3)):continue\n'
    new = '        classified=[int(x.get("finish") or 0) for x in finishers if int(x.get("finish") or 0)>0]\n        if 1 not in classified or sum(1 for finish in classified if finish<=3)<3:continue\n'

    if new in block:
        print("NAR dead-heat podium parser already patched")
        return
    if old not in block:
        raise SystemExit("PATCH_ABORT: legacy literal-rank podium guard not found in _nar_official_result_fast")

    block = block.replace(old, new, 1)
    lines[start:end] = [block]
    out = "".join(lines)
    ast.parse(out)
    APP.write_text(out, encoding="utf-8")
    print("Patched NAR podium acceptance: normal 1-2-3 and dead heats such as 1-1-3 now pass")


if __name__ == "__main__":
    main()
