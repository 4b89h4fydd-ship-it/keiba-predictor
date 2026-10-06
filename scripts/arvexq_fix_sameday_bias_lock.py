#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from arvexq.domain.legacy_evaluation import SOURCE

PATH = Path('arvexq/domain/legacy_evaluation.py')
src = SOURCE
old = '''        lock=d.get("preRacePrediction") if isinstance(d.get("preRacePrediction"),dict) else {}
        locked=lock.get("horses") if isinstance(lock.get("horses"),list) else []
        marked={int(x.get("horseNumber") or 0) for x in locked if isinstance(x,dict) and str(x.get("mark") or "") in valid_marks}
        if not marked:
            marked={int(h.get("horseNumber") or 0) for h in (d.get("horses") or []) if isinstance(h,dict) and str((h.get("integratedEvaluation") or {}).get("mark") or "") in valid_marks}
        comparable=bool(marked)
'''
new = '''        lock=d.get("preRacePrediction") if isinstance(d.get("preRacePrediction"),dict) else {}
        locked=lock.get("horses") if isinstance(lock.get("horses"),list) else []
        # Mark-miss learning is valid only when the earlier race has an immutable
        # pre-race lock. Historical post-race/recomputed marks must never substitute.
        marked={int(x.get("horseNumber") or 0) for x in locked if isinstance(x,dict) and str(x.get("mark") or "") in valid_marks}
        comparable=bool(marked)
'''
if old in src:
    src = src.replace(old, new, 1)
elif 'Historical post-race/recomputed marks must never substitute.' not in src:
    raise SystemExit('same-day mark fallback anchor not found')

literal_lines = '\n'.join(f'    {line!r}' for line in src.splitlines(keepends=True))
text = (
    'from __future__ import annotations\n\n'
    '# Transitional extraction of evaluation_core from app.py.\n'
    '# The block is executed in the caller namespace to preserve legacy global lookup.\n'
    'SOURCE = (\n'
    f'{literal_lines}\n'
    ')\n\n'
    'def install_evaluation_core(namespace: dict) -> None:\n'
    "    code = compile(SOURCE, '<arvexq:evaluation_core>', 'exec')\n"
    '    exec(code, namespace, namespace)\n'
)
PATH.write_text(text, encoding='utf-8')
print('same-day bias pre-race-lock guard patched')
