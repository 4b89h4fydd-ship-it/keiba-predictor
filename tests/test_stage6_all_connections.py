"""Stage 6: read the actual caller, adapter, and source code for all 178 connected boxes.

This is a static contract, not certification of runtime behavior, live sources,
unbounded loops, or deferred routes. Stage 4 and Stage 5 runtime tests stay intact.
"""
import ast
import json
import re
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "arvexq" / "components"
STAGE5 = ROOT / "docs" / "independence" / "route-connection-stage5-20261021" / "summary.json"
REMAINING = set(json.loads(STAGE5.read_text(encoding="utf-8"))["remaining_unconnected"])
CONNECTED = tuple(i for i in range(1, 201) if i not in REMAINING)


@lru_cache(maxsize=None)
def source(path):
    file = ROOT / path
    assert file.is_file(), f"missing actual code: {path}"
    return file.read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def connection(item):
    path = f"arvexq/components/item_{item:03}/connection.json"
    data = json.loads(source(path))
    assert data["id"] == item
    return data


def test_exact_item_population_and_existing_links():
    assert len(CONNECTED) == 178
    assert len(REMAINING) == 22
    links = [rec for item in CONNECTED for rec in connection(item)["connections"]]
    # 98 repeated item associations share original connections; they are not
    # evidence of duplicate runtime invocations.
    assert len(links) == 723
    assert len({json.dumps(r, sort_keys=True) for r in links}) == 625


@pytest.mark.parametrize("item", CONNECTED, ids=lambda i: f"item_{i:03}")
def test_existing_caller_adapter_and_original_source_for_each_item(item):
    data = connection(item)
    assert data["connection_code_present"] is True
    assert data["circuits"] and set(data["circuits"]) <= {"JRA", "NAR"}
    assert data["connections"], f"item {item}: not connected"
    for rec in data["connections"]:
        assert item in rec["items"], f"item {item}: bad ownership"
        caller = rec["caller"]["path"]
        target = rec["box_target"]
        original = rec["original_source"].split("::", 1)[0]
        caller_src, target_src, original_src = source(caller), source(target), source(original)
        assert caller_src and target_src and original_src
        kind = rec["kind"]
        if kind in {"python-object-alias", "python-module-object-alias"}:
            # Check the actual consumer points at its existing adapter.
            module = target.removesuffix(".py").replace("/", ".")
            assert module in caller_src, (item, caller, module)
            assert target.endswith(".py")
            ast.parse(target_src, filename=target)
            if kind == "python-object-alias":
                symbol = rec["caller"]["imported"]
                assert re.search(r"\b" + re.escape(symbol) + r"\b", target_src), (item, target, symbol)
        elif kind in {"existing-callable-forward", "existing-ui-function-forward"}:
            symbol = rec["caller"]["symbol"]
            private = rec.get("original_private_name")
            assert private and private in caller_src, (item, caller, symbol)
            assert symbol in caller_src and target_src.strip(), (item, target, symbol)
        elif kind == "esm-object-reexport":
            symbol = rec["caller"]["imported"]
            assert symbol in caller_src and symbol in target_src, (item, symbol)
        elif kind in {"unchanged-asset-load", "existing-worker-fetch-forward", "existing-audit-call-forward"}:
            # The original asset/worker/audit route is still on disk; the Stage 4
            # suite separately tests forwarding and exact asset byte behavior.
            assert target_src.strip()
        else:
            pytest.fail(f"Unrecognized connected record kind for {item}: {kind}")


def test_python_box_imports_have_no_static_cycles():
    # Only static imports in Python box modules are covered; dynamic imports
    # and JS runtime dependencies remain outside this test's scope.
    boxes = {
        r["box_target"]
        for i in CONNECTED
        for r in connection(i)["connections"]
        if r["box_target"].endswith(".py")
    }
    by_module = {p.removesuffix(".py").replace("/", "."): p for p in boxes}
    edges = {p: set() for p in boxes}
    for p in sorted(boxes):
        parsed = ast.parse(source(p), filename=p)
        for n in ast.walk(parsed):
            if isinstance(n, ast.ImportFrom) and n.module:
                if n.module in by_module:
                    edges[p].add(by_module[n.module])
                for a in n.names:
                    child = n.module + "." + a.name
                    if child in by_module:
                        edges[p].add(by_module[child])
            elif isinstance(n, ast.Import):
                for a in n.names:
                    if a.name in by_module:
                        edges[p].add(by_module[a.name])
    visited, active = set(), set()
    def dfs(node):
        if node in active:
            pytest.fail(f"static Python box import cycle involving {node}")
        if node in visited:
            return
        active.add(node)
        for nxt in edges[node]:
            dfs(nxt)
        active.remove(node)
        visited.add(node)
    for p in sorted(boxes):
        dfs(p)
