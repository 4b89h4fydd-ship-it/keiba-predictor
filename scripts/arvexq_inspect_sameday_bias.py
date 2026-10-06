#!/usr/bin/env python3
from __future__ import annotations

import ast
from arvexq.domain.legacy_evaluation import SOURCE

wanted={'_v313_same_day_mark_profile','_v313_horse_flow_adjust'}
tree=ast.parse(SOURCE)
for node in tree.body:
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in wanted:
        print(f'\n===== {node.name} =====')
        print(ast.get_source_segment(SOURCE,node) or '')
