#!/usr/bin/env python3
from pathlib import Path

PATH = Path('arvexq/ui/static/app.js')
text = PATH.read_text(encoding='utf-8')


def replace_function(src: str, name: str, replacement: str) -> str:
    marker = f'function {name}('
    start = src.find(marker)
    if start < 0:
        if replacement in src:
            return src
        raise SystemExit(f'{name}: function not found')
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit(f'{name}: opening brace not found')
    depth = 0
    quote = None
    escape = False
    i = brace
    while i < len(src):
        ch = src[i]
        if quote:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                quote = None
        else:
            if ch in ('\"', "'", '`'):
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return src[:start] + replacement + src[i + 1:]
        i += 1
    raise SystemExit(f'{name}: closing brace not found')


RACE_READY = '''function raceDisplayCoreReady(d,row){
  if(!d)return false;
  var hs=(d.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}),fs=d.result&&d.result.finishers||[];
  if(!hs.length){
    return isFinal(d)&&fs.some(function(x){return x&&n(x.horseNumber)>0&&String(x.name||'').trim()})
  }
  var active=hs.filter(function(h){return !isScratchHorse(h)});
  if(!active.length)active=hs;
  var named=active.filter(function(h){return String(h.name||'').trim()}).length;
  // Rendering readiness is intentionally weaker than prediction/bet readiness.
  // Never trap the user on a loading screen while jockey, carried weight, odds,
  // bodyweight or history are still syncing. Those are guarded separately by
  // dataReadinessProfile before predictions/bets are fixed.
  return named>=Math.min(active.length,Math.max(1,Math.ceil(active.length*.50)))
}'''

text = replace_function(text, 'raceDisplayCoreReady', RACE_READY)

# Keep the visible build label tied to the actual runtime build instead of a stale literal.
old_footer = "function cinematicFooter(){return '<footer class=\"cinematic-footer\"><b>ARVEXQ</b><span>ARTIFICIAL RACING INTELLIGENCE</span><small>TACTICAL ENGINE · BUILD v326</small></footer>'}"
new_footer = "function cinematicFooter(){return '<footer class=\"cinematic-footer\"><b>ARVEXQ</b><span>ARTIFICIAL RACING INTELLIGENCE</span><small>TACTICAL ENGINE · BUILD '+esc(window.ARVEXQ_BUILD||'v327')+'</small></footer>'}"
if old_footer in text:
    text = text.replace(old_footer, new_footer, 1)
elif new_footer not in text and 'BUILD v326</small></footer>' in text:
    text = text.replace('BUILD v326</small></footer>', "BUILD '+esc(window.ARVEXQ_BUILD||'v327')+'</small></footer>", 1)

# Invariants: do not regress special-race scope or the final-input buy-plan lock.
required = [
    'function specialForecastRaceCandidates()',
    "String(r.track||'')==='高知'",
    'lockWindow=30',
    'n(rd.actualOdds,0)>=.65',
    'n(rd.bodyWeight,0)>=.70',
    'n(rd.environment,0)>=1',
    "plan.lockPolicy='v327-final-input-window-30m'",
    'window.ARVEXQ_BUILD="v327";',
    '/sw-v327-reset.js',
]
missing = [x for x in required if x not in text]
if missing:
    raise SystemExit('race-open patch invariant failure: ' + repr(missing))

# The old display gate must be gone. These fields remain prediction/bet readiness inputs,
# but must not block rendering a race page.
fn_start = text.find('function raceDisplayCoreReady(')
fn_end = text.find('\n}', fn_start) + 2
ready_block = text[fn_start:fn_end]
for forbidden in ('carriedWeight', 'jockey', 'fieldSize'):
    if forbidden in ready_block:
        raise SystemExit(f'race display still blocked by {forbidden}')

PATH.write_text(text, encoding='utf-8')
print('ARVEXQ race-open reliability patched: runner identity opens UI; strict prediction readiness preserved')
