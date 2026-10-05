from __future__ import annotations

from pathlib import Path
import re

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
original = text

# 1) Keep app.py dependent on stable service/databank boundaries, not internals.
old_imp = 'from arvexq.ability_engine import apply_ability_ranking\n'
service_imp = 'from arvexq.services import prepare_race_detail\n'
bridge_imp = 'from arvexq.databanks.legacy_bridge import register_legacy_sources\n'
if old_imp in text:
    text = text.replace(old_imp, service_imp, 1)
elif service_imp not in text:
    future = re.search(r'^(from __future__ import .*\n)', text, re.M)
    if future:
        text = text[:future.end()] + service_imp + text[future.end():]
    else:
        text = service_imp + text
if bridge_imp not in text:
    pos = text.find(service_imp)
    if pos >= 0:
        pos += len(service_imp)
        text = text[:pos] + bridge_imp + text[pos:]
    else:
        text = bridge_imp + text

# 2) Route common precompute through the staged service layer.
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

# 4) Old embedded UI fallback, kept for repositories not yet extracted.
text = text.replace("st=String(h.status||'欠場')", "st=String(h.status||(h.scratched||h.withdrawn?'出走取消':'欠場'))")
text = text.replace('/欠場|取消|除外/.test(s)', '/欠場|出走取消|取消|競走除外|除外/.test(s)')

# 5) Register current fetchers after they have been defined. This is migration glue:
#    source functions can now be extracted one-by-one without callers knowing location.
registry_marker = '# ARVEXQ_DATABANK_REGISTRY\nregister_legacy_sources(globals())\n'
if registry_marker not in text:
    anchor = '\n_start_racedb_daemon()'
    if anchor in text:
        text = text.replace(anchor, '\n' + registry_marker + anchor, 1)
    else:
        text = text.rstrip() + '\n\n' + registry_marker

if text == original:
    print('No changes needed')
else:
    APP.write_text(text, encoding='utf-8')
    print('app.py patched')
