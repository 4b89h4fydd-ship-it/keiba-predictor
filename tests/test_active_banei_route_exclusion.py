"""Active-route Banei exclusion: evaluate the exact existing list expressions.

No D1 reads/writes, network, or production app imports occur here. Archived
historical documents remain untouched; only current-day active paths are gated.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BANEI = "nar-2026-10-22-帯広-01"
BANEI_ALIAS = "nar-2026-10-22-帯広ば-02"
NAR = "nar-2026-10-22-大井-03"
JRA = "jra-2026-10-22-東京-04"


def _module(path: str) -> ast.Module:
    return ast.parse((ROOT / path).read_text(encoding="utf-8"), path)


def _fn(module: ast.Module, name: str) -> ast.FunctionDef:
    return next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == name)


def _eval_assignment(path: str, fn_name: str, name: str, values: dict):
    func = _fn(_module(path), fn_name)
    match = next(
        n for n in ast.walk(func)
        if isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == name
        and isinstance(n.value, (ast.ListComp, ast.DictComp))
    )
    code = compile(ast.fix_missing_locations(ast.Expression(body=match.value)), path, "eval")
    return eval(code, {"__builtins__": __builtins__, **values})


def _rows():
    return [
        {"id": BANEI, "track": "帯広", "raceNumber": 1, "date": "2026-10-22"},
        {"id": BANEI_ALIAS, "track": "帯広ば", "raceNumber": 2, "date": "2026-10-22"},
        {"id": NAR, "track": "大井", "raceNumber": 3, "date": "2026-10-22"},
        {"id": JRA, "track": "東京", "raceNumber": 4, "date": "2026-10-22"},
    ]


class ActiveBaneiExclusionTests(unittest.TestCase):
    def test_current_day_boxed_bootstrap_filters_before_presentation(self):
        node = _fn(_module("app.py"), "_arvexq_original__bootstrap_rows_local")
        node.decorator_list = []
        namespace = {"races": lambda *_: {"races": _rows()}}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                     "app.py", "exec"), namespace)
        result = namespace[node.name]("2026-10-22")
        self.assertEqual({row["id"] for row in result}, {NAR, JRA})

    def test_canonical_prefetch_collect_filters_both_summaries_and_details(self):
        bundle = {"races": _rows(), "details": _rows()}
        original = deepcopy(bundle)
        for field in ("rows", "initial"):
            actual = _eval_assignment("scripts/arvexq_prefetch.py", "prepare", field,
                                      {"bundle": bundle})
            self.assertEqual({r["id"] for r in actual}, {NAR, JRA})
        self.assertEqual(bundle, original)

    def test_analysis_only_consumes_active_prefetch_rows(self):
        day = {"races": _rows(), "details": _rows()}
        rows = _eval_assignment("scripts/arvexq_prefetch.py", "analyze_persisted",
                                "rows", {"day": day})
        details = _eval_assignment("scripts/arvexq_prefetch.py", "analyze_persisted",
                                   "details", {"day": day})
        self.assertEqual({r["id"] for r in rows}, {NAR, JRA})
        self.assertEqual(set(details), {NAR, JRA})

    def test_live_sync_excludes_inactive_venue_without_erasing_input(self):
        bundle = {"races": _rows()}
        before = deepcopy(bundle)
        rows = _eval_assignment("scripts/arvexq_live_sync.py", "main", "rows",
                                {"bundle": bundle})
        self.assertEqual({r["id"] for r in rows}, {NAR, JRA})
        self.assertEqual(bundle, before)


if __name__ == "__main__":
    unittest.main()
