#!/usr/bin/env python3
from __future__ import annotations
import ast
from pathlib import Path

src=Path('app.py').read_text(encoding='utf-8')
lines=src.splitlines()
tree=ast.parse(src)
want=('jra','central_run','profile_run','parse_result','result_detail')
blocks=[]
for node in tree.body:
    if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
    name=node.name.lower()
    if not any(k in name for k in want):continue
    if not any(k in name for k in ('jra','central','profile')):continue
    start=node.lineno;end=node.end_lineno or start
    text='\n'.join(lines[start-1:end])
    if any(token in text for token in ('finishers','cornerPositions','timeSeconds','racePrize1','推定','上り','recentRaces')):
        blocks.append((start,end,node.name,text))
for start,end,name,text in blocks:
    print(f'\n===== {name} {start}-{end} =====')
    print(text)
print(f'\nARVEXQ_JRA_PARSER_BLOCK_COUNT={len(blocks)}')
