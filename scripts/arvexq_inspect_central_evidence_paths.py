#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

src=Path('app.py').read_text(encoding='utf-8')
lines=src.splitlines()
tree=ast.parse(src)

TOKENS=(
    'sameDayMarkAdjustment',
    'sameDayBias',
    'biasScore',
    'trackBiasScore',
    'recentRaces',
    '_jra_merge_runs',
)

hits=[]
for node in ast.walk(tree):
    if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
    start=node.lineno; end=node.end_lineno or start
    text='\n'.join(lines[start-1:end])
    matched=[t for t in TOKENS if t in text]
    if not matched:continue
    # Ignore pure display/helper readers unless they also assign/merge evidence.
    if not any(s in text for s in ('sameDayMarkAdjustment','_jra_merge_runs','recentRaces"]=',"recentRaces'] =",'recentRaces =','recentRaces":')):
        continue
    hits.append((start,end,node.name,matched,text))

for start,end,name,matched,text in sorted(hits):
    print(f'\n===== {name} {start}-{end} tokens={matched} =====')
    print(text)
print(f'\nARVEXQ_CENTRAL_EVIDENCE_PATH_BLOCKS={len(hits)}')
