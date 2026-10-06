#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PY = ROOT / 'app.py'
INDEX = ROOT / 'arvexq' / 'ui' / 'static' / 'index.html'
APP_JS = ROOT / 'arvexq' / 'ui' / 'static' / 'app.js'
BUILD = ROOT / 'build_static.py'
OLD = 'v327'
NEW = 'v328'
OLD_MARKER = 'v327-race-open-repair-20261006'
NEW_MARKER = 'v328-safari-runtime-20261006'


def replace_required(text: str, old: str, new: str, label: str, *, all_matches: bool = False) -> str:
    if new in text and old not in text:
        return text
    if old not in text:
        raise RuntimeError(f'{label}: anchor missing: {old!r}')
    return text.replace(old, new) if all_matches else text.replace(old, new, 1)


def bump_fastapi_version(text: str) -> str:
    tree = ast.parse(text)
    for node in tree.body:
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == 'app'
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == 'FastAPI'
        ):
            continue
        for kw in node.value.keywords:
            if kw.arg == 'version' and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                value = kw.value.value
                if NEW in value:
                    return text
                if OLD not in value:
                    raise RuntimeError(f'FastAPI version is neither {OLD} nor {NEW}: {value!r}')
                segment = ast.get_source_segment(text, kw.value)
                if not segment:
                    raise RuntimeError('FastAPI version source segment missing')
                return text.replace(segment, segment.replace(OLD, NEW, 1), 1)
    raise RuntimeError('top-level app = FastAPI(...) version literal not found')


app_py = APP_PY.read_text(encoding='utf-8')
APP_PY.write_text(bump_fastapi_version(app_py), encoding='utf-8')

index = INDEX.read_text(encoding='utf-8')
index = replace_required(index, '/styles-arvexq-v327.css', '/styles-arvexq-v328.css', 'index css')
index = replace_required(index, '/app-v327.js', '/app-v328.js', 'index js')
index = replace_required(index, 'arvexq-hard-reset-v327-race-open-repair-20261006', 'arvexq-hard-reset-v328-safari-runtime-20261006', 'hard reset tag')
index = replace_required(index, 'arvexq_build","v327"', 'arvexq_build","v328"', 'hard reset build')
INDEX.write_text(index, encoding='utf-8')

js = APP_JS.read_text(encoding='utf-8')
js = replace_required(js, 'window.ARVEXQ_BUILD="v327";', 'window.ARVEXQ_BUILD="v328";', 'runtime build')
js = replace_required(js, OLD_MARKER, NEW_MARKER, 'service-worker reload marker', all_matches=True)
js = replace_required(js, '/sw-v327-reset.js', '/sw-v328-reset.js', 'service-worker registration')
if 'function courseProfile(r){\n  r=r||{};' not in js:
    raise RuntimeError('Safari courseProfile null guard missing before build bump')
if 'function courseStageFrac(r,st){\n  r=r||{};' not in js:
    raise RuntimeError('Safari courseStageFrac null guard missing before build bump')
APP_JS.write_text(js, encoding='utf-8')

build = BUILD.read_text(encoding='utf-8')
for name in ('compat_css', 'compat_app', 'compat_arvexq'):
    old = f'{name} = ("v326",'
    new = f'{name} = ("v327","v326",'
    if new not in build:
        if old not in build:
            raise RuntimeError(f'{name}: v326 anchor missing')
        build = build.replace(old, new, 1)

old_sw = 'for legacy_sw in ("v326", "v325", "v324", "v323", "v322", "v321", "v320", "v319", "v318"):'
new_sw = 'for legacy_sw in ("v327", "v326", "v325", "v324", "v323", "v322", "v321", "v320", "v319", "v318"):'
if new_sw not in build:
    if old_sw not in build:
        raise RuntimeError('legacy service-worker alias anchor missing')
    build = build.replace(old_sw, new_sw, 1)

old_header = '    "/sw-v326-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",\n'
new_header = '    "/sw-v327-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",\n' + old_header
if '    "/sw-v327-reset.js","  Cache-Control: no-store, no-cache, must-revalidate, max-age=0","  Service-Worker-Allowed: /",\n' not in build:
    if old_header not in build:
        raise RuntimeError('v326 service-worker header anchor missing')
    build = build.replace(old_header, new_header, 1)
BUILD.write_text(build, encoding='utf-8')

index = INDEX.read_text(encoding='utf-8')
js = APP_JS.read_text(encoding='utf-8')
build = BUILD.read_text(encoding='utf-8')
checks = {
    'index css v328': '/styles-arvexq-v328.css' in index,
    'index js v328': '/app-v328.js' in index,
    'fresh hard reset tag': 'arvexq-hard-reset-v328-safari-runtime-20261006' in index,
    'runtime build v328': 'window.ARVEXQ_BUILD="v328";' in js,
    'runtime sw v328': '/sw-v328-reset.js' in js,
    'runtime marker v328': NEW_MARKER in js,
    'v327 app redirect': 'compat_app = ("v327","v326",' in build,
    'v327 css redirect': 'compat_css = ("v327","v326",' in build,
    'v327 arvexq redirect': 'compat_arvexq = ("v327","v326",' in build,
    'v327 sw alias': 'for legacy_sw in ("v327", "v326",' in build,
    'v327 sw no-store': '"/sw-v327-reset.js"' in build,
    'Safari course guard': 'function courseProfile(r){\n  r=r||{};' in js,
}
missing = [k for k, ok in checks.items() if not ok]
if missing:
    raise SystemExit('v328 build/cache policy incomplete: ' + ', '.join(missing))
print('ARVEXQ v328 coherent; v327 compatibility retained; Safari/PWA hard reset renewed')
