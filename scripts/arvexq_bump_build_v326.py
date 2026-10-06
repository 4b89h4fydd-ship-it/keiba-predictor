#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PY = ROOT / "app.py"
INDEX = ROOT / "arvexq" / "ui" / "static" / "index.html"
APP_JS = ROOT / "arvexq" / "ui" / "static" / "app.js"
BUILD = ROOT / "build_static.py"
OLD = "v325"
NEW = "v326"


def replace_once_or_done(text: str, old: str, new: str, label: str) -> str:
    if new in text and old not in text:
        return text
    count = text.count(old)
    if count == 1:
        return text.replace(old, new, 1)
    if new in text and count == 0:
        return text
    raise RuntimeError(f"{label}: expected one old anchor, got {count}")


def replace_all_or_done(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count == expected:
        return text.replace(old, new)
    if count == 0 and text.count(new) >= expected:
        return text
    raise RuntimeError(f"{label}: expected {expected} old anchors, got {count}")


def bump_fastapi_version(text: str) -> str:
    tree = ast.parse(text)
    for node in tree.body:
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "app"
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "FastAPI"
        ):
            continue
        for kw in node.value.keywords:
            if kw.arg != "version" or not isinstance(kw.value, ast.Constant) or not isinstance(kw.value.value, str):
                continue
            value = kw.value.value
            if NEW in value:
                return text
            if OLD not in value:
                raise RuntimeError(f"FastAPI version is neither {OLD} nor {NEW}: {value!r}")
            segment = ast.get_source_segment(text, kw.value)
            if not segment:
                raise RuntimeError("FastAPI version source segment missing")
            replacement = segment.replace(OLD, NEW, 1)
            if text.count(segment) < 1:
                raise RuntimeError("FastAPI version literal not found in source")
            return text.replace(segment, replacement, 1)
    raise RuntimeError("top-level app = FastAPI(...) version literal not found")


# 1) Server/build source of truth.
app_py = APP_PY.read_text(encoding="utf-8")
app_py = bump_fastapi_version(app_py)
APP_PY.write_text(app_py, encoding="utf-8")

# 2) HTML must request the same generation it advertises in the hard reset.
index = INDEX.read_text(encoding="utf-8")
index = replace_once_or_done(index, "/styles-arvexq-v325.css", "/styles-arvexq-v326.css", "index css generation")
index = replace_once_or_done(index, "/app-v325.js", "/app-v326.js", "index js generation")
if 'arvexq_build","v326"' not in index and 'arvexq_build","v325"' in index:
    index = index.replace('arvexq_build","v325"', 'arvexq_build","v326"', 1)
INDEX.write_text(index, encoding="utf-8")

# 3) JS cache namespace + service worker must move in lockstep.
js = APP_JS.read_text(encoding="utf-8")
js = replace_once_or_done(js, 'window.ARVEXQ_BUILD="v325";', 'window.ARVEXQ_BUILD="v326";', "runtime build")
js = replace_all_or_done(js, '"v325-home-race-boxes-20261006"', '"v326-special-races-20261006"', 2, "sw reload marker")
js = replace_once_or_done(js, '/sw-v325-reset.js', '/sw-v326-reset.js', "sw registration")
js = js.replace('BUILD v324', 'BUILD v326')
APP_JS.write_text(js, encoding="utf-8")

# 4) Preserve immediately previous asset URLs and installed SW generations.
build = BUILD.read_text(encoding="utf-8")
for name in ("compat_css", "compat_app", "compat_arvexq"):
    old = f'{name} = ("v324",'
    new = f'{name} = ("v325","v324",'
    if new not in build:
        if old not in build:
            raise RuntimeError(f"{name}: v324 anchor not found")
        build = build.replace(old, new, 1)

old_sw = 'for legacy_sw in ("v321", "v320", "v319", "v318"):'
new_sw = 'for legacy_sw in ("v325", "v324", "v323", "v322", "v321", "v320", "v319", "v318"):'
if new_sw not in build:
    if old_sw not in build:
        raise RuntimeError("legacy service-worker alias anchor not found")
    build = build.replace(old_sw, new_sw, 1)

# ARVEXQ is patched frequently between formal build-number bumps. A one-year immutable
# policy can therefore pin an iPhone/PWA to stale JS/CSS even after main is fixed.
# Keep browser caching, but force revalidation so same-generation hotfixes are visible.
immutable = '  Cache-Control: public, max-age=31536000, immutable'
revalidate = '  Cache-Control: no-cache, must-revalidate'
count = build.count(immutable)
if count:
    if count != 3:
        raise RuntimeError(f"current JS/CSS immutable header count changed: {count}")
    build = build.replace(immutable, revalidate)
elif build.count(revalidate) < 3:
    raise RuntimeError("current JS/CSS revalidation policy missing")

BUILD.write_text(build, encoding="utf-8")

# Final invariants.
index = INDEX.read_text(encoding="utf-8")
js = APP_JS.read_text(encoding="utf-8")
build = BUILD.read_text(encoding="utf-8")
checks = {
    "index css": "/styles-arvexq-v326.css" in index,
    "index js": "/app-v326.js" in index,
    "runtime build": 'window.ARVEXQ_BUILD="v326";' in js,
    "runtime sw": "/sw-v326-reset.js" in js,
    "runtime sw marker": js.count('"v326-special-races-20261006"') >= 2,
    "prior app redirect": 'compat_app = ("v325","v324",' in build,
    "prior css redirect": 'compat_css = ("v325","v324",' in build,
    "prior sw alias": 'for legacy_sw in ("v325", "v324",' in build,
    "no current immutable assets": 'max-age=31536000, immutable' not in build,
    "current assets revalidate": build.count('Cache-Control: no-cache, must-revalidate') >= 4,
}
missing = [k for k, ok in checks.items() if not ok]
if missing:
    raise SystemExit("v326 build/cache policy incomplete: " + ", ".join(missing))
print("ARVEXQ v326 coherent; v325 compatibility retained; current JS/CSS revalidate on load")
