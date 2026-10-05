from __future__ import annotations

from pathlib import Path
import re

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
original = text

# 1) Keep app.py dependent on a stable service boundary, not prediction internals.
old_imp = 'from arvexq.ability_engine import apply_ability_ranking\n'
new_imp = 'from arvexq.services import prepare_race_detail\n'
if old_imp in text:
    text = text.replace(old_imp, new_imp, 1)
elif new_imp not in text:
    future = re.search(r'^(from __future__ import .*\n)', text, re.M)
    if future:
        text = text[:future.end()] + new_imp + text[future.end():]
    else:
        text = new_imp + text

# 2) Route common precompute through the service layer.
text = text.replace('    detail = apply_ability_ranking(detail)\n', '    detail = prepare_race_detail(detail)\n', 1)
if 'prepare_race_detail(detail)' not in text:
    pat = re.compile(r'(def _precompute_detail_metrics\(detail(?::\s*dict)?\s*\)(?:\s*->\s*[^:]+)?\s*:\s*\n)')
    m = pat.search(text)
    if not m:
        raise SystemExit('PATCH_ABORT: _precompute_detail_metrics(detail) not found')
    inject = m.group(1) + '    detail = prepare_race_detail(detail)\n'
    text = text[:m.start()] + inject + text[m.end():]

# 3) Normalize explicit scratch labels. Keep different statuses separate.
sm = re.search(r'def _scratch_status\(value:\s*str\)\s*->\s*str:\s*\n(?P<body>(?:    .*\n)+?)(?=\n\ndef |\nclass |\Z)', text)
if sm:
    body = sm.group('body')
    body2 = body.replace('if "出走取消" in s or "取消" in s:return "取消"', 'if "出走取消" in s or "取消" in s:return "出走取消"')
    if body2 != body:
        text = text[:sm.start('body')] + body2 + text[sm.end('body'):]

# 4) Front-end fallback: a scratched runner with no status must not appear as generic 欠場.
text = text.replace("st=String(h.status||'欠場')", "st=String(h.status||(h.scratched||h.withdrawn?'出走取消':'欠場'))")

# 5) Treat full cancellation wording as scratch everywhere the embedded UI checks it.
text = text.replace('/欠場|取消|除外/.test(s)', '/欠場|出走取消|取消|競走除外|除外/.test(s)')

if text == original:
    print('No changes needed')
else:
    APP.write_text(text, encoding='utf-8')
    print('app.py patched')
